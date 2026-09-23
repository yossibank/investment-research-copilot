from pydantic import BaseModel, Field


class RagAnswer(BaseModel):
    answer: str
    is_answerable: bool
    # Field(default_factory=list)で値がなければ新しい空リストを作成する。
    source_chunk_ids: list[str] = Field(default_factory=list)
    source_pages: list[str] = Field(default_factory=list)


class GoldenCase(BaseModel):
    id: str
    question: str
    expected_answer: str
    expected_answerable: bool
    evidence_id: str | None
    evidence_page: int | None
    required_terms: list[str]


class EvalResult(BaseModel):
    id: str
    question: str
    expected_answerable: bool
    actual_answerable: bool
    retrieval_hit: bool | None
    page_hit: bool | None
    answer_correct: bool
    source_hit: bool
    answer: str
    retrieved_chunk_ids: list[str]
    expected_evidence_id: str | None
