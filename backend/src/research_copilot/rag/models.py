from pydantic import BaseModel, Field


class RagAnswer(BaseModel):
    answer: str
    is_answerable: bool
    # Field(default_factory=list)で値がなければ新しい空リストを作成する。
    source_chunk_ids: list[str] = Field(default_factory=list)
    source_pages: list[str] = Field(default_factory=list)

