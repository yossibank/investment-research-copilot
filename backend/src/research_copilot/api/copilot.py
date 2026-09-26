"""
Copilot の実行結果を、API のレスポンスの形に変換する。
"""

from ..agent.models import CopilotRun
from ..agent.orchestrator import execute_copilot
from .schemas import CopilotQueryResponse


def to_api_response(run: CopilotRun) -> CopilotQueryResponse:
    """
    評価用の CopilotRun を、API で返す形へ変換する。
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
    API 用の入口。実行は execute_copilot に任せ、API 用の形へ変換するだけ。
    """

    run = execute_copilot(
        question=question,
        top_k=top_k,
        request_id=request_id,
        max_tool_rounds=max_tool_rounds,
    )

    return to_api_response(run)
