"""
/research/stream の処理。検索結果と Claude の回答を NDJSON で少しずつ返す。Claude API を呼ぶ。
"""

import json
import logging
from collections.abc import Iterator
from time import perf_counter

import anthropic

from ..agent.models import ResearchSource
from ..agent.prompts import STREAMING_SYSTEM_PROMPT, build_user_message
from ..llm import create_client, get_model
from ..retrieval.search import search

logger = logging.getLogger(__name__)


def json_line(payload: dict[str, object]) -> str:
    """
    dict を 1 行の JSON 文字列（末尾に改行付き）にする。
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
    検索結果を先に返し、続けて Claude の回答を少しずつ返す。

    Event:
        metadata → 検索結果
        text_delta → Claude の回答の断片
        done → 完了
        error → ストリーミング中のエラー
    """

    started_at = perf_counter()

    try:
        # ====================================
        # 検索
        # ====================================

        retrieval_started = perf_counter()

        results = search(
            question,
            top_k=top_k,
        )

        retrieval_ms = (perf_counter() - retrieval_started) * 1000

        # Claude の回答より先に、検索結果を返しておく。
        retrieved_sources = [
            ResearchSource.from_chunk(chunk, score).model_dump()
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
        # Claude の回答をストリーミング
        # ====================================

        model = get_model()

        client = create_client()

        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=STREAMING_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": build_user_message(question, results),
                }
            ],
        ) as stream:
            # Claude から文字列が届くたびに、そのまま iOS へ流す。
            for text in stream.text_stream:
                yield json_line(
                    {
                        "type": "text_delta",
                        "text": text,
                    }
                )

            # トークン数を記録するため、完了後にメッセージ全体を取得する。
            final_message = stream.get_final_message()

        latency_ms = (perf_counter() - started_at) * 1000

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
