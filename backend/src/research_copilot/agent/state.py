"""
Copilot が 1 問を調べている途中の状態。JSON に保存して、途中から再開するために使う。
"""

from pathlib import Path
from typing import Any, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, Field

from ..tools.search_tool import SearchHit
from .models import CopilotAnswer, StopReason, ToolCall


class ConversationState(BaseModel):
    """
    Claude とのやりとり。Claude に送る messages をそのまま持つ。
    """

    messages: list[dict[str, Any]] = Field(default_factory=list)


class TaskMetrics(BaseModel):
    """
    使った step・トークン・時間。再開した後も足し続ける。
    """

    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retrieval_ms: float = 0
    # 検索と各 step にかかった時間の合計。プロセスをまたいでも意味が変わらないように、時刻ではなく時間を持つ。
    elapsed_ms: float = 0


class ResearchTaskState(BaseModel):
    """
    調査の進み具合。何を調べ、何を見つけ、どこまで進んだか。
    """

    task_id: str = Field(default_factory=lambda: uuid4().hex)
    question: str
    top_k: int
    status: Literal["running", "answered", "stopped"] = "running"
    # 最初の検索結果。評価の recall はこれで測る。
    results: list[SearchHit]
    # 出典として認めるチャンク。results に search_filing の結果を足していく。
    evidence: list[SearchHit]
    tool_history: list[ToolCall] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    metrics: TaskMetrics = Field(default_factory=TaskMetrics)
    answer: CopilotAnswer | None = None
    stop_reason: StopReason | None = None


class TaskSnapshot(BaseModel):
    """
    保存と再開の単位。2 つの状態をまとめて 1 つの JSON にする。
    """

    task: ResearchTaskState
    conversation: ConversationState

    def save(self, path: Path) -> None:
        """
        JSON ファイルに書き出す。
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Self:
        """
        JSON ファイルから読み戻す。
        """

        return cls.model_validate_json(path.read_text(encoding="utf-8"))
