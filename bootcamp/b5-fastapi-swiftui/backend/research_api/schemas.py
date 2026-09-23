from pydantic import BaseModel, Field, field_validator


class ResearchQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)

    # ge = greater than or equal
    # le = less than or equal
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def validate_question(
        cls,
        value: str,
    ) -> str:
        """
        " "のような空白だけの質問を防ぐ。

        min_length=1だけでは空白1文字も有効になるため、
        strip()後にもチェックする。
        """

        value = value.strip()

        if not value:
            raise ValueError("Question must not be empty.")

        return value


class ResearchSource(BaseModel):
    chunk_id: str
    company: str
    document_name: str
    page: int
    score: float
    source_url: str


class ResearchQueryResponse(BaseModel):
    answer: str
    is_answerable: bool
    sources: list[ResearchSource]
