from pydantic import BaseModel, Field


class GoldenCase(BaseModel):
    id: str
    question: str
    expected_answer: str
    expected_answerable: bool
    evidence_id: str | None
    evidence_page: int | None
    required_terms: list[str]
    category: str = "numeric"
    expected_tool: str | None = None


class EvalResult(BaseModel):
    id: str
    question: str
    category: str
    expected_answerable: bool
    actual_answerable: bool
    retrieval_hit: bool | None
    page_hit: bool | None
    answer_correct: bool
    source_hit: bool
    tool_correct: bool
    answer: str
    expected_tool: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    expected_evidence_id: str | None
    latency_ms: float | None = None
    retrieval_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
