import json
import logging
import os
from collections.abc import Iterator
from time import perf_counter

import anthropic

from ..rag.pipeline import build_context, create_client
from ..retrieval.search import search

logger = logging.getLogger(__name__)


def json_line(payload: dict[str, object]) -> str:
    """
    Python dictを1行JSONへ変換する。

    NDJSON:
    1 line = 1 JSON
    """

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
        )
        + "\n"
    )


def stream_research_query(
    question: str,
    top_k: int,
    request_id: str,
) -> Iterator[str]:
    """
    Research QueryをNDJSONでStreamingする。

    Event:
        metadata → Retrieval情報
        text_delta → Claudeの回答破片
        done → 完了情報
        error → Streaming途中のError
    """

    started_at = perf_counter()

    try:
        # ====================================
        # Retrieval
        # ====================================

        retrieval_started = perf_counter()

        results = search(
            question,
            top_k=top_k,
        )

        retrieval_ms = (perf_counter() - retrieval_started) * 1000

        context = build_context(results)

        # 先にRetrieval結果を返す。
        retrieved_sources = [
            {
                "chunk_id": chunk.chunk_id,
                "company": chunk.company,
                "document_name": chunk.document_name,
                "page": chunk.page,
                "score": score,
                "source_url": chunk.source_url,
            }
            for chunk, score in results
        ]

        yield json_line(
            {
                "type": "metadata",
                "request_id": request_id,
                "retrieval_ms": round(retrieval_ms, 2),
                "retrieved_sources": retrieved_sources,
            }
        )

        # ====================================
        # Claude Streaming
        # ====================================

        model = os.getenv("ANTHROPIC_MODEL")

        if not model:
            raise RuntimeError("ANTHROPIC_MODEL is not set.")

        client = create_client()

        system_prompt = (
            "You are an investment research assistant. "
            "Use ONLY the supplied CONTEXT. "
            "Do not guess missing information. "
            "If the answer cannnot be confirmed "
            "from the context, clearly say so. "
            "Preserve numerical values and units. "
            "Do not provide investment advice "
            "or definitive stock-price predictions."
        )

        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"),
                }
            ],
        ) as stream:
            # Claudeからtextが届くたびにSwiftUIへそのまま流す。
            for text in stream.text_stream:
                yield json_line(
                    {
                        "type": "text_delta",
                        "text": text,
                    }
                )

            # Stream全体が終了した後の完成Messageを取得する。
            final_message = stream.get_final_message()

        latency_ms = (perf_counter() - started_at) * 1000

        # Anthropic APIのToken Usage。
        usage = final_message.usage

        logger.info(
            "research stream completed",
            extra={
                "event": "research_stream_completed",
                "request_id": request_id,
                "latency_ms": round(latency_ms, 2),
                "retrieval_ms": round(retrieval_ms, 2),
                "top_k": top_k,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        )

        yield json_line(
            {
                "type": "done",
                "request_id": request_id,
                "latency_ms": round(latency_ms, 2),
            }
        )

    except anthropic.APITimeoutError:
        logger.exception(
            "Claude stream timed out",
            extra={
                "event": "stream_failed",
                "request_id": request_id,
            },
        )

        yield json_line(
            {
                "type": "error",
                "message": "The AI service timed out.",
            }
        )

    except Exception:
        logger.exception(
            "Research stream failed",
            extra={
                "event": "stream_failed",
                "request_id": request_id,
            },
        )

        yield json_line(
            {
                "type": "error",
                "message": "The research request failed.",
            }
        )
