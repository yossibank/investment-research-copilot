"""
API のリクエストとレスポンスの型。iOS の ResearchModels.swift と対応する。
"""

from pydantic import BaseModel, Field, field_validator

from ..agent.models import ResearchSource


class ResearchQueryRequest(BaseModel):
    """
    iOS から受け取る質問。
    """

    question: str = Field(min_length=1, max_length=1000)

    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def validate_question(
        cls,
        value: str,
    ) -> str:
        """
        空白だけの質問を弾き、前後の空白を取り除いた質問を返す。

        min_length=1 だけでは空白 1 文字も通ってしまうため。
        """

        value = value.strip()

        if not value:
            raise ValueError("Question must not be empty.")

        return value


class CopilotQueryResponse(BaseModel):
    """
    iOS に返す回答。ResearchModels.swift の CopilotQueryResponse と対応する。
    """

    answer: str
    is_answerable: bool
    sources: list[ResearchSource] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
