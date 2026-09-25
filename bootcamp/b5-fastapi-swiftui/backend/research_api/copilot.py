from email import message
import logging
import os
from time import perf_counter

from pydantic import BaseModel, Field
from rag_evaluation.rag import build_context, create_client
from tool_calling.registry import TOOLS, execute_tool
from vector_search.search import search

from .schemas import CopilotQueryResponse, ResearchSource

logger = logging.getLogger(__name__)


class CopilotAnswer(BaseModel):
    answer: str
    is_answerable: bool
    source_chunk_ids: list[str] = Field(default_factory=list)


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


def run_copilot_query(
    question: str,
    top_k: int = 5,
    request_id: str | None = None,
    max_tool_rounds: int = 3,
) -> CopilotQueryResponse:
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

    model = os.getenv("ANTHROPIC_MODEL")

    if not model:
        raise RuntimeError("ANTHROPIC_MODEL is not set.")

    # ==================================
    # 1. Retrieval
    # ==================================

    retrueval_started = perf_counter()

    results = search(question, top_k=top_k)

    retrieval_ms = (perf_counter() - retrueval_started) * 1000

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
                            "content": result,
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

                except Exception as error:
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

        return build_copilot_response(
            answer=answer,
            results=results,
            tools_used=tools_used,
        )

    raise RuntimeError("Maximum tool rounds exceeded.")


def build_copilot_response(
    answer: CopilotAnswer,
    results,
    tools_used: list[str],
) -> CopilotQueryResponse:
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

    return CopilotQueryResponse(
        answer=answer.answer,
        is_answerable=answer.is_answerable,
        sources=sources,
        tools_used=tools_used,
    )
