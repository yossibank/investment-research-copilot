import anthropic
from fastapi import FastAPI, HTTPException

from .schemas import ResearchQueryRequest, ResearchQueryResponse
from .service import run_research_query

app = FastAPI(
    title="Investment Research Copilot API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """
    Server自体が起動しているか確認するEndpoint。

    Claude APIは呼ばない。

    MonitoringやDebugでも使いやすい。
    """

    return {"status": "ok"}


@app.post("/research/query", response_model=ResearchQueryResponse)
def research_query(request: ResearchQueryRequest) -> ResearchQueryResponse:
    """
    Research CopilotのメインEndpoint。

    SwiftUI
        ↓
    POST /research/query
        ↓
    B4 RAG
        ↓
    Claude
        ↓
    JSON Response
    """

    try:
        return run_research_query(
            question=request.question,
            top_k=request.top_k,
        )

    except anthropic.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The AI service timed out",
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
            detail="The research service is not configured.",
        )
