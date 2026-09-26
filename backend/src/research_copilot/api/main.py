"""
FastAPI のアプリ本体。エンドポイントと、全リクエスト共通のログを定義する。

起動: fastapi dev backend/src/research_copilot/api/main.py
"""

import logging
from time import perf_counter
from uuid import uuid4

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from .copilot import run_copilot_query
from .logging_config import configure_logging
from .schemas import CopilotQueryResponse, ResearchQueryRequest
from .streaming_service import stream_research_query

configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Investment Research Copilot API",
    version="0.1.0",
)


@app.middleware("http")
async def request_logging(
    request: Request,
    call_next,
):
    """
    すべてのリクエストにリクエスト ID を付け、開始・完了・失敗と処理時間をログに残す。
    """

    # クライアントからリクエスト ID が来ていればそれを使い、なければここで作る。
    request_id = request.headers.get("X-Request-ID") or str(uuid4())

    # エンドポイント側から参照できるように、request.state に保存する。
    request.state.request_id = request_id

    started_at = perf_counter()

    logger.info(
        "request started",
        extra={
            "event": "request_started",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    try:
        response = await call_next(request)

    except Exception:
        latency_ms = (perf_counter() - started_at) * 1000

        logger.exception(
            "request failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "latency_ms": round(latency_ms, 2),
            },
        )

        raise

    latency_ms = (perf_counter() - started_at) * 1000

    # iOS 側でもリクエスト ID を確認できるように、レスポンスヘッダーに付ける。
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request completed",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
        },
    )

    return response


@app.get("/health")
def health() -> dict[str, str]:
    """
    サーバーが起動しているかだけを返す。Claude は呼ばない。
    """

    return {"status": "ok"}


@app.post(
    "/research/stream",
    response_class=StreamingResponse,
)
def research_stream(
    request_body: ResearchQueryRequest,
    request: Request,
) -> StreamingResponse:
    """
    Claude の回答を NDJSON（1 行 1 JSON）で少しずつ返す。ツールは使わない。
    """

    request_id = request.state.request_id

    stream = stream_research_query(
        question=request_body.question, top_k=request_body.top_k, request_id=request_id
    )

    return StreamingResponse(
        stream,
        media_type="application/x-ndjson",
    )


@app.post(
    "/research/copilot",
    response_model=CopilotQueryResponse,
)
def research_copilot(
    request_body: ResearchQueryRequest,
    request: Request,
) -> CopilotQueryResponse:
    """
    検索・ツール実行・出典の検証までを行った回答を返す。iOS アプリが使うエンドポイント。
    """

    request_id = request.state.request_id

    try:
        return run_copilot_query(
            question=request_body.question,
            top_k=request_body.top_k,
            request_id=request_id,
        )

    except anthropic.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The AI service timed out.",
        )

    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily busy.",
        )

    except anthropic.APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is unavailable.",
        )

    except anthropic.APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="The upstream AI service returned an error.",
        )

    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="The research service could not complete the request.",
        )
