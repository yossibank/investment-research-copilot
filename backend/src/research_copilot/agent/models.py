from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..retrieval.models import Chunk


class ResearchSource(BaseModel):
    """
    検索結果と照合済みの出典。APIとiOSにもこの形で返す。
    """

    chunk_id: str
    company: str
    document_name: str
    page: int
    score: float
    source_url: str


class CopilotAnswer(BaseModel):
    """
    Claudeに変えさせる構造化出力。
    """

    answer: str
    is_answerable: bool
    source_chunk_ids: list[str] = Field(default_factory=list)


@dataclass
class CopilotRun:
    """
    Copilotを一回実行した結果(評価用の詳しい形)。

    APIはこの中からanswer/sources/tools_usedだけを返し、
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
