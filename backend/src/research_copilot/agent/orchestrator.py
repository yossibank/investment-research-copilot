"""
Copilot の中心の処理（検索 → Claude → ツール実行 → 出典の検証）。Claude API を呼ぶ。
"""

import json
import logging
from pathlib import Path
from time import perf_counter
from typing import NoReturn, cast

from anthropic.types import MessageParam, ToolResultBlockParam, ToolUseBlock
from pydantic import BaseModel

from ..llm import create_client, get_model
from ..retrieval.models import Chunk
from ..retrieval.search import search
from ..tools.registry import TOOLS, run_tool
from ..tools.search_tool import SearchFilingResult, SearchHit
from .models import (
    AgentLimits,
    AgentStopped,
    CopilotAnswer,
    CopilotRun,
    ResearchSource,
    StopReason,
    ToolCall,
)
from .prompts import SUBMIT_ANSWER_TOOL, SYSTEM_PROMPT, build_user_message
from .state import ConversationState, ResearchTaskState, TaskMetrics, TaskSnapshot

logger = logging.getLogger(__name__)


DEFAULT_LIMITS = AgentLimits()


def execute_copilot(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    limits: AgentLimits = DEFAULT_LIMITS,
    snapshot_path: Path | None = None,
) -> CopilotRun:
    """
    質問に対して、検索 → Claude（必要ならツール実行）→ 出典の検証までを行う。

    流れ:
        1. 質問に近いチャンクを検索する
        2. 検索結果を CONTEXT として Claude に渡す
        3. Claude が tool_use を返したら Python でツールを実行し、結果を渡してもう一度呼ぶ
        4. Claude が submit_answer ツールで返した回答（CopilotAnswer）を受け取る
        5. 回答が挙げた出典を、実際の検索結果と照合する

    API と評価の両方から呼ばれるため、HTTP のことは扱わない。
    戻り値の CopilotRun には、評価で使うレイテンシやトークン数も含まれる。
    snapshot_path を渡すと、1 step ごとに途中の状態を JSON に保存する。
    """

    snapshot = start_task(question, top_k)

    return run_task(
        snapshot,
        request_id,
        limits,
        snapshot_path,
    )


def resume_copilot(
    snapshot_path: Path,
    request_id: str | None = None,
    limits: AgentLimits = DEFAULT_LIMITS,
) -> CopilotRun:
    """
    保存した途中の状態を読み戻し、残りの step を続ける。
    """

    snapshot = TaskSnapshot.load(snapshot_path)

    if snapshot.task.status != "running":
        raise ValueError(f"Task is already {snapshot.task.status}.")

    return run_task(
        snapshot,
        request_id,
        limits,
        snapshot_path,
    )


def start_task(question: str, top_k: int) -> TaskSnapshot:
    """
    質問に近いチャンクを検索し、Claude に送る最初のメッセージまでを作る。
    """

    if not question.strip():
        raise ValueError("Question must not be empty.")

    started = perf_counter()

    results = search(question, top_k=top_k)

    retrieval_ms = (perf_counter() - started) * 1000

    hits = [SearchHit(chunk=chunk, score=score) for chunk, score in results]

    task = ResearchTaskState(
        question=question,
        top_k=top_k,
        results=hits,
        evidence=list(hits),
        metrics=TaskMetrics(
            retrieval_ms=retrieval_ms,
            elapsed_ms=retrieval_ms,
        ),
    )

    conversation = ConversationState(
        messages=[
            {
                "role": "user",
                "content": build_user_message(question, results),
            }
        ]
    )

    return TaskSnapshot(task=task, conversation=conversation)


def run_task(
    snapshot: TaskSnapshot,
    request_id: str | None,
    limits: AgentLimits,
    snapshot_path: Path | None = None,
) -> CopilotRun:
    """
    Claude とツールのやりとりを、submit_answer で答えるか上限に届くまで続ける。

    状態はすべて snapshot に書き込むので、途中で止まっても保存したところから再開できる。
    """

    task = snapshot.task
    conversation = snapshot.conversation
    metrics = task.metrics

    model = get_model()
    client = create_client()

    while metrics.steps < limits.max_steps:
        if metrics.elapsed_ms >= limits.timeout_s * 1000:
            _stop("timeout", snapshot, snapshot_path, request_id)

        if metrics.input_tokens + metrics.output_tokens >= limits.max_total_tokens:
            _stop("token_budget", snapshot, snapshot_path, request_id)

        step_started = perf_counter()

        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=[*TOOLS, SUBMIT_ANSWER_TOOL],
            tool_choice={
                "type": "auto",
                "disable_parallel_tool_use": True,
            },
            # 保存できるように辞書で持っているが、中身は Claude に送れる形のまま。
            messages=cast(list[MessageParam], conversation.messages),
        )

        metrics.steps += 1
        metrics.input_tokens += response.usage.input_tokens
        metrics.output_tokens += response.usage.output_tokens

        if response.stop_reason != "tool_use":
            raise RuntimeError("Claude finished without calling submit_answer.")

        submitted = next(
            (
                block
                for block in response.content
                if block.type == "tool_use" and block.name == SUBMIT_ANSWER_TOOL["name"]
            ),
            None,
        )

        if submitted is not None:
            answer = CopilotAnswer.model_validate(submitted.input)

            task.answer = answer
            task.status = "answered"
            metrics.elapsed_ms += (perf_counter() - step_started) * 1000
            _save(snapshot, snapshot_path)

            return _to_run(task, answer)

        conversation.messages.append(
            {
                "role": "assistant",
                "content": [
                    block.model_dump(exclude_none=True) for block in response.content
                ],
            }
        )

        tool_results: list[ToolResultBlockParam] = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            if _is_repeated_call(block, task.tool_history):
                _stop("repeated_call", snapshot, snapshot_path, request_id)

            tool_result, output = _run_tool(block, request_id)

            tool_results.append(tool_result)

            content = tool_result.get("content")

            task.tool_history.append(
                ToolCall(
                    name=block.name,
                    input=dict(block.input),
                    succeeded=output is not None,
                    result=content if isinstance(content, str) else None,
                )
            )

            if output is None:
                continue

            if block.name not in task.tools_used:
                task.tools_used.append(block.name)

            if isinstance(output, SearchFilingResult):
                task.evidence.extend(output.hits)

        conversation.messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

        metrics.elapsed_ms += (perf_counter() - step_started) * 1000

        # 1 step ごとに保存する。ここで落ちても、次はこの step の続きから始められる。
        _save(snapshot, snapshot_path)

    _stop("max_steps", snapshot, snapshot_path, request_id)


def _is_repeated_call(
    block: ToolUseBlock,
    tool_calls: list[ToolCall],
) -> bool:
    """
    直前と同じツールを、同じ引数で呼んでいるかを返す。
    """

    if not tool_calls:
        return False

    last = tool_calls[-1]

    return last.name == block.name and last.input == dict(block.input)


def _save(
    snapshot: TaskSnapshot,
    snapshot_path: Path | None = None,
) -> None:
    """
    保存先が指定されていれば、今の状態を JSON に書き出す。
    """

    if snapshot_path is not None:
        snapshot.save(snapshot_path)


def _stop(
    reason: StopReason,
    snapshot: TaskSnapshot,
    snapshot_path: Path | None,
    request_id: str | None,
) -> NoReturn:
    """
    上限に届いたことをログに残し、AgentStopped を投げる。
    """

    task = snapshot.task
    task.status = "stopped"
    task.stop_reason = reason
    _save(snapshot, snapshot_path)

    logger.warning(
        "copilot agent stopped",
        extra={
            "event": "agent_stopped",
            "request_id": request_id,
            "stop_reason": reason,
            "tool_calls": len(task.tool_history),
        },
    )

    raise AgentStopped(reason, task.tool_history)


def _to_run(
    task: ResearchTaskState,
    answer: CopilotAnswer,
) -> CopilotRun:
    """
    答えの出た task を、API と評価が使う CopilotRun に変換する。
    """

    results = [(hit.chunk, hit.score) for hit in task.results]
    evidence = [(hit.chunk, hit.score) for hit in task.evidence]

    return CopilotRun(
        answer=answer,
        results=results,
        sources=validate_sources(answer, evidence),
        tools_used=task.tools_used,
        tool_calls=task.tool_history,
        retrieval_ms=task.metrics.retrieval_ms,
        total_ms=task.metrics.elapsed_ms,
        input_tokens=task.metrics.input_tokens,
        output_tokens=task.metrics.output_tokens,
    )


def _run_tool(
    block: ToolUseBlock,
    request_id: str | None,
) -> tuple[ToolResultBlockParam, BaseModel | None]:
    """
    Claude が要求したツールを 1 つ実行し、Claude に返す tool_result を作る。

    ツールが失敗しても例外は外に出さず、is_error 付きの tool_result にして
    Claude に失敗を伝える。戻り値の 2 つ目はツールの結果で、失敗した時は None。
    """

    tool_started = perf_counter()

    try:
        output = run_tool(
            name=block.name,
            tool_input=block.input,
        )

    except Exception:
        tool_ms = (perf_counter() - tool_started) * 1000

        logger.exception(
            "copilot tool failed",
            extra={
                "event": "tool_failed",
                "request_id": request_id,
                "tool_name": block.name,
                "tool_input": block.input,
                "tool_success": False,
                "tool_latency_ms": round(tool_ms, 2),
            },
        )

        return (
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": "Tool execution failed.",
                "is_error": True,
            },
            None,
        )

    result = json.dumps(
        output.model_dump(),
        ensure_ascii=False,
    )

    tool_ms = (perf_counter() - tool_started) * 1000

    logger.info(
        "copilot tool completed",
        extra={
            "event": "tool_completed",
            "request_id": request_id,
            "tool_input": block.input,
            "tool_output": result,
            "tool_name": block.name,
            "tool_success": True,
            "tool_latency_ms": round(tool_ms, 2),
        },
    )

    return (
        {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        },
        output,
    )


def validate_sources(
    answer: CopilotAnswer,
    results: list[tuple[Chunk, float]],
) -> list[ResearchSource]:
    """
    Claude が挙げた出典の ID を、実際の検索結果と照合する。

    検索結果にない ID（Claude が作り出した ID）と重複は捨てる。
    """

    retrieved_by_id = {chunk.chunk_id: (chunk, score) for chunk, score in results}

    sources: list[ResearchSource] = []

    seen_ids: set[str] = set()

    for chunk_id in answer.source_chunk_ids:
        if chunk_id in seen_ids:
            continue

        item = retrieved_by_id.get(chunk_id)

        if item is None:
            logger.warning(
                "Claude returned unknown source chunk",
                extra={"event": "invalid_source_id"},
            )

            continue

        chunk, score = item

        sources.append(ResearchSource.from_chunk(chunk, score))

        seen_ids.add(chunk_id)

    return sources
