"""
Copilot の回答と実行結果の型。API と評価の両方から使う。
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Self

from pydantic import BaseModel, Field

from ..retrieval.models import Chunk


class ToolCall(BaseModel):
    """
    Claude が要求したツール呼び出し 1 回分。
    失敗した呼び出しも残す。
    """

    name: str
    input: dict[str, Any]
    succeeded: bool
    # Claude に返した内容（結果の JSON か、失敗のメッセージ）。
    result: str | None = None


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
    Claude の回答。submit_answer ツールの入力をこの型で検証する。
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
    # 成功・失敗を問わず、要求された順のツール呼び出し
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True)
class AgentLimits:
    """
    エージェントのループの上限。どれかに届いたら止める。
    """

    # Claude を呼ぶ回数。submit_answer で答える呼び出しも 1 回に数える。
    max_steps: int = 5

    # 検索を含む全体の時間。全 30 問の平均は約 10 秒。
    timeout_s: float = 60.0

    # 入力と出力のトークンの合計。これまでの 1問 の最大は約 2.5 万。
    max_total_tokens: int = 40000


StopReason = Literal["max_steps", "repeated_call", "timeout", "token_budget"]


class AgentStopped(RuntimeError):
    """
    上限に届いて止まったときの例外。

    RuntimeError を継承するので、API は今まで通り 503 を返す。
    """

    def __init__(self, reason: StopReason, tool_calls: list[ToolCall]) -> None:
        super().__init__(f"Agent stopped: {reason}")
        self.reason = reason
        self.tool_calls = tool_calls
