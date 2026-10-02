"""
Copilot の中心の処理（検索 → Claude → ツール実行 → 出典の検証）。Claude API を呼ぶ。
"""

import json
import logging
from time import perf_counter
from typing import NoReturn

from anthropic.types import MessageParam, ToolResultBlockParam, ToolUseBlock
from pydantic import BaseModel

from ..llm import create_client, get_model
from ..retrieval.models import Chunk
from ..retrieval.search import search
from ..tools.registry import TOOLS, run_tool
from ..tools.search_tool import SearchFilingResult
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

logger = logging.getLogger(__name__)


DEFAULT_LIMITS = AgentLimits()


def execute_copilot(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    limits: AgentLimits = DEFAULT_LIMITS,
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
    """

    if not question.strip():
        raise ValueError("Question must not be empty.")

    model = get_model()

    # ==================================
    # 1. 検索
    # ==================================

    started = perf_counter()

    results = search(question, top_k=top_k)

    retrieval_ms = (perf_counter() - started) * 1000

    # ==================================
    # 2. Claude に渡すメッセージ
    # ==================================

    messages: list[MessageParam] = [
        {
            "role": "user",
            "content": build_user_message(question, results),
        }
    ]

    client = create_client()

    tools_used: list[str] = []

    tool_calls: list[ToolCall] = []

    # 出典として認めるチャンク。最初の検索結果に、追加検索で見つけたものを足していく。
    evidence: list[tuple[Chunk, float]] = list(results)

    input_tokens = 0
    output_tokens = 0

    # ==================================
    # 3. ツール呼び出しのループ
    # ==================================

    for _ in range(limits.max_steps):
        if perf_counter() - started > limits.timeout_s:
            _stop("timeout", tool_calls, request_id)

        if input_tokens + output_tokens > limits.max_total_tokens:
            _stop("token_budget", tool_calls, request_id)

        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=[*TOOLS, SUBMIT_ANSWER_TOOL],
            tool_choice={
                "type": "auto",
                "disable_parallel_tool_use": True,
            },
            messages=messages,
        )

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        # ==============================
        # Claude がツールを要求した場合
        # ==============================

        if response.stop_reason == "tool_use":
            # disable_parallel_tool_use なので、submit_answer が来たらそれが最後の応答になる。
            submitted = next(
                (
                    block
                    for block in response.content
                    if block.type == "tool_use"
                    and block.name == SUBMIT_ANSWER_TOOL["name"]
                ),
                None,
            )

            if submitted is not None:
                answer = CopilotAnswer.model_validate(submitted.input)

                return CopilotRun(
                    answer=answer,
                    results=results,
                    sources=validate_sources(answer, evidence),
                    tools_used=tools_used,
                    tool_calls=tool_calls,
                    retrieval_ms=retrieval_ms,
                    total_ms=(perf_counter() - started) * 1000,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            tool_results: list[ToolResultBlockParam] = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                if _is_repeated_call(block, tool_calls):
                    _stop("repeated_call", tool_calls, request_id)

                tool_result, output = _run_tool(block, request_id)

                tool_results.append(tool_result)

                content = tool_result.get("content")

                tool_calls.append(
                    ToolCall(
                        name=block.name,
                        input=dict(block.input),
                        succeeded=output is not None,
                        result=content if isinstance(content, str) else None,
                    )
                )

                if output is None:
                    continue

                if block.name not in tools_used:
                    tools_used.append(block.name)

                if isinstance(output, SearchFilingResult):
                    evidence.extend((hit.chunk, hit.score) for hit in output.hits)

            messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )

            continue

        # ==============================
        # submit_answer を呼ばずに終わった場合
        # ==============================

        raise RuntimeError("Claude finished without calling submit_answer.")

    raise _stop("max_steps", tool_calls, request_id)


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


def _stop(
    reason: StopReason,
    tool_calls: list[ToolCall],
    request_id: str | None = None,
) -> NoReturn:
    """
    上限に届いたことをログに残し、AgentStopped を投げる。
    """

    logger.warning(
        "copilot agent stopped",
        extra={
            "event": "agent_stopped",
            "request_id": request_id,
            "stop_reason": reason,
            "tool_calls": len(tool_calls),
        },
    )

    raise AgentStopped(reason, tool_calls)


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
