from pydantic import BaseModel


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
