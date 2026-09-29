"""
資料を追加で検索する読み取り専用ツール。Claude API は呼ばない（埋め込みモデルは使う）。
"""

from pydantic import BaseModel, ConfigDict, Field

from ..retrieval.models import Chunk
from ..retrieval.search import search


class SearchFilingInput(BaseModel):
    """
    追加検索ツールの入力。
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(min_length=1, max_length=200)
    top_k: int = Field(default=3, ge=1, le=5)


class SearchHit(BaseModel):
    """
    追加検索で見つかったチャンク 1 つと類似度。
    """

    chunk: Chunk
    score: float


class SearchFilingResult(BaseModel):
    """
    追加検索の結果。見つかったチャンクは出典として使っていい。
    """

    hits: list[SearchHit]


def search_filing(tool_input: SearchFilingInput) -> SearchFilingResult:
    """
    Claude が指定した検索語で資料を検索し、上位のチャンクを返す。
    """

    results = search(
        tool_input.query,
        top_k=tool_input.top_k,
    )

    return SearchFilingResult(
        hits=[SearchHit(chunk=chunk, score=score) for chunk, score in results]
    )
