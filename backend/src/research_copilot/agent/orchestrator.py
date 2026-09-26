import logging
from time import perf_counter

from anthropic.types import MessageParam, ToolResultBlockParam

from ..llm import create_client, get_model
from ..retrieval.models import Chunk
from ..retrieval.search import search
from ..tools.registry import TOOLS, execute_tool
from .models import CopilotAnswer, CopilotRun, ResearchSource
from .prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)


def execute_copilot(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    max_tool_rounds: int = 3,
) -> CopilotRun:
    """
    質問に対して、検索 → Claude（必要ならツール実行）→ 出典の検証までを行う。

    流れ:
        1. 質問に近いチャンクを検索する
        2. 検索結果を CONTEXT として Claude に渡す
        3. Claude が tool_use を返したら Python でツールを実行し、結果を渡してもう一度呼ぶ
        4. Claude の構造化された回答（CopilotAnswer）を受け取る
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

    retrieval_started = perf_counter()

    results = search(question, top_k=top_k)

    retrieval_ms = (perf_counter() - retrieval_started) * 1000

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

    input_tokens = 0
    output_tokens = 0

    # ==================================
    # 3. ツール呼び出しのループ
    # ==================================

    for _ in range(max_tool_rounds + 1):
        response = client.messages.parse(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_choice={
                "type": "auto",
                "disable_parallel_tool_use": True,
            },
            messages=messages,
            output_format=CopilotAnswer,
        )

        usage = getattr(response, "usage", None)

        if usage is not None:
            input_tokens += usage.input_tokens
            output_tokens += usage.output_tokens

        # ==============================
        # Claude がツールを要求した場合
        # ==============================

        if response.stop_reason == "tool_use":
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

                tool_started = perf_counter()

                try:
                    result = execute_tool(
                        name=block.name,
                        tool_input=block.input,
                    )

                    tool_ms = (perf_counter() - tool_started) * 1000

                    logger.info(
                        "copilot tool completed",
                        extra={
                            "event": "tool_completed",
                            "request_id": request_id,
                            "tool_output": result,
                            "tool_name": block.name,
                            "tool_success": True,
                            "tool_latency_ms": round(tool_ms, 2),
                        },
                    )

                    if block.name not in tools_used:
                        tools_used.append(block.name)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

                except Exception:
                    tool_ms = (perf_counter() - tool_started) * 1000

                    logger.exception(
                        "copilot tool failed",
                        extra={
                            "event": "tool_failed",
                            "request_id": request_id,
                            "tool_name": block.name,
                            "tool_success": False,
                            "tool_latency_ms": round(tool_ms, 2),
                        },
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Tool execution failed.",
                            "is_error": True,
                        }
                    )

            messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )

            continue

        # ==============================
        # 最終回答（構造化出力）
        # ==============================

        answer = response.parsed_output

        if answer is None:
            raise RuntimeError("Claude returned no parsed CopilotAnswer.")

        return CopilotRun(
            answer=answer,
            results=results,
            sources=validate_sources(answer, results),
            tools_used=tools_used,
            retrieval_ms=retrieval_ms,
            total_ms=(perf_counter() - started) * 1000,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    raise RuntimeError("Maximum tool rounds exceeded.")


def validate_sources(
    answer: CopilotAnswer,
    results: list[tuple[Chunk, float]],
) -> list[ResearchSource]:
    """
    Claude が挙げた出典の ID を、実際の検索結果と照合する。

    検索結果にない ID（Claude が作り出した ID）と重複は捨てる。
    """

    retrieved_by_id = {
        chunk.chunk_id: (
            chunk,
            score,
        )
        for chunk, score in results
    }

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
