import logging
from dataclasses import dataclass
from time import perf_counter

from pydantic import BaseModel, Field

from ..llm import create_client, get_model
from ..rag.pipeline import build_context
from ..retrieval.models import Chunk
from ..retrieval.search import search
from ..tools.registry import TOOLS, execute_tool
from .schemas import CopilotQueryResponse, ResearchSource

logger = logging.getLogger(__name__)


class CopilotAnswer(BaseModel):
    answer: str
    is_answerable: bool
    source_chunk_ids: list[str] = Field(default_factory=list)


@dataclass
class CopilotRun:
    """
    Copilotを一回実行した結果(評価用の詳しい形)。

    APIはこの中から answer / sources / tools_used だけを返し、
    評価は検索結果・レイテンシ・トークン数までを使う。
    """

    answer: CopilotAnswer
    results: list[tuple[Chunk, float]]
    sources: list[ResearchSource]
    tools_used: list[str]
    retrieval_ms: float
    total_ms: float
    input_tokens: int
    output_tokens: int


SYSTEM_PROMPT = """
You are an investment research copilot.

You answer questions using company filing evidence
provided in CONTEXT.

Rules:

1. Use ONLY facts explicitly present in CONTEXT
   or values explicitly provided by the user.

2. Never invent missing financial values.

3. When exact financial arithmetic is required,
   use an available financial calculation tool
   instead of calculating it yourself.

4. Tool arguments must come only from explicit
   values in CONTEXT or the user's question.

5. Do not call a financial tool if required
   inputs are missing.

6. If the available evidence is insufficient,
   set is_answerable to false.

7. If is_answerable is false,
   source_chunk_ids must be empty unless the
   sources directly explain why the question
   cannot be answered.

8. source_chunk_ids must contain only CHUNK_IDs
   supplied in CONTEXT.

9. Preserve financial periods, values, and units.

10. Distinguish actual results from company guidance.

11. Do not provide investment advice,
    trade recommendations, or definitive
    stock-price predictions.
"""


def execute_copilot(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    max_tool_rounds: int = 3,
) -> CopilotRun:
    """
    Research CopilotのMain Orchestrator。

    Flow:
        Question
            ↓
        Vector Search
            ↓
        Context
            ↓
        Claude
            ↓
        Tool Use?
            ↓
        Python Tool
            ↓
        Claude
            ↓
        Structured Answer
            ↓
        Source Validation
            ↓
        API Response
    """

    if not question.strip():
        raise ValueError("Question must not be empty.")

    model = get_model()

    # ==================================
    # 1. Retrieval
    # ==================================

    started = perf_counter()

    retrieval_started = perf_counter()

    results = search(question, top_k=top_k)

    retrieval_ms = (perf_counter() - retrieval_started) * 1000

    context = build_context(results)

    # ==================================
    # 2. Conversation
    # ==================================

    messages: list[dict] = [
        {
            "role": "user",
            "content": (f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"),
        }
    ]

    client = create_client()

    tools_used: list[str] = []

    input_tokens = 0
    output_tokens = 0

    # ==================================
    # 3. Tool Loop
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
        # Tool Request
        # ==============================

        if response.stop_reason == "tool_use":
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            tool_results: list[dict] = []

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
        # Final Structured Answer
        # ==============================

        answer = response.parsed_output

        if answer is None:
            raise RuntimeError("Claude returned no parse CopilotAnswer.")

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


def to_api_response(run: CopilotRun) -> CopilotQueryResponse:
    """
    評価用のCopilotRunを、APIで返す形へ変換する。
    """

    return CopilotQueryResponse(
        answer=run.answer.answer,
        is_answerable=run.answer.is_answerable,
        sources=run.sources,
        tools_used=run.tools_used,
    )


def run_copilot_query(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    max_tool_rounds: int = 3,
) -> CopilotQueryResponse:
    """
    API用の入口。実行はexecute_copilotに任せ、API用の形へ変換するだけ。
    """

    run = execute_copilot(
        question=question,
        top_k=top_k,
        request_id=request_id,
        max_tool_rounds=max_tool_rounds,
    )

    return to_api_response(run)


def validate_sources(
    answer: CopilotAnswer,
    results: list[tuple[Chunk, float]],
) -> list[ResearchSource]:
    """
    Claudeのsource_chunk_idsを本物のRetrieval Resultと照合する。
    Claudeが存在しないIDを返してもAPI Responseには採用しない。
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

        sources.append(
            ResearchSource(
                chunk_id=chunk.chunk_id,
                company=chunk.company,
                document_name=chunk.document_name,
                page=chunk.page,
                score=score,
                source_url=chunk.source_url,
            )
        )

        seen_ids.add(chunk_id)

    return sources
