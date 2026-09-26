"""
Copilot の回答と実行結果の型。API と評価の両方から使う。
"""

from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel, Field

from ..retrieval.models import Chunk


class ResearchSource(BaseModel):
    """
    検索結果と照合済みの出典。API と iOS にもこの形で返す。
    """

    chunk_id: str
    company: str
    document_name: str
    page: int
    score: float
    source_url: str

    @classmethod
    def from_chunk(cls, chunk: Chunk, score: float) -> Self:
        """
        検索結果の(Chunk, score)から出典を作る。
        """

        return cls(
            chunk_id=chunk.chunk_id,
            company=chunk.company,
            document_name=chunk.document_name,
            page=chunk.page,
            score=score,
            source_url=chunk.source_url,
        )


class CopilotAnswer(BaseModel):
    """
    Claude に返させる構造化出力。
    """

    answer: str
    is_answerable: bool
    source_chunk_ids: list[str] = Field(default_factory=list)


@dataclass
class CopilotRun:
    """
    Copilot を一回実行した結果（評価用の詳しい形）。

    API はこの中から answer/sources/tools_used だけを返し、
    評価は検索結果・レイテンシ・トークン数までを使う。
    """

    answer: CopilotAnswer
    results: list[tuple[Chunk, float]]
    sources: list[ResearchSource]
    tools_used: list[str]
    retrieval_ms: float
    total_ms: float
    input_tokens: int
    output_tokens: int
