"""
execute_copilot のテスト。検索と Claude API を偽物に差し替える。
"""

from types import SimpleNamespace

from research_copilot.agent import orchestrator
from research_copilot.agent.models import CopilotAnswer
from research_copilot.agent.orchestrator import execute_copilot, validate_sources
from research_copilot.retrieval.models import Chunk


def make_chunk(
    chunk_id: str,
    page: int,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text="売上高 2,018,914 百万円",
        company="Example Holdings",
        period="2027年3月期 第一四半期",
        document_name="決算短信",
        page=page,
        source_url="https://example.com",
    )


RESULTS = [
    (make_chunk("ex-p7-c0", 7), 0.9),
    (make_chunk("ex-p1-c0", 1), 0.8),
]


class FakeMessages:
    """
    Claude API の代わり。決めておいた応答を順番に返す。
    """

    def __init__(self, responses: list) -> None:
        self.responses = responses
        self.calls = 0

    def parse(self, **kwargs):
        response = self.responses[self.calls]
        self.calls += 1
        return response


def final_response(
    answer: CopilotAnswer, input_tokens: int = 100, output_tokens: int = 20
):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[],
        parsed_output=answer,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def tool_use_response():
    block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="calculate_financial_metrics",
        input={
            "previous_revenue": 100,
            "current_revenue": 110,
        },
    )

    return SimpleNamespace(
        stop_reason="tool_use",
        content=[block],
        parsed_output=None,
        usage=SimpleNamespace(
            input_tokens=80,
            output_tokens=10,
        ),
    )


def setup_fakes(monkeypatch, responses: list) -> FakeMessages:
    fake_messages = FakeMessages(responses)

    monkeypatch.setenv(
        "ANTHROPIC_MODEL",
        "test-model",
    )
    monkeypatch.setattr(
        orchestrator,
        "search",
        lambda question, top_k: RESULTS,
    )
    monkeypatch.setattr(
        orchestrator,
        "create_client",
        lambda: SimpleNamespace(messages=fake_messages),
    )

    return fake_messages


def test_validate_sources_drops_unknown_ids() -> None:
    """
    検索結果にない ID と重複 ID は sources に入らない。
    """

    answer = CopilotAnswer(
        answer="売上高は2,018,914百万円です。",
        is_answerable=True,
        source_chunk_ids=["ex-p7-c0", "made-up-id", "ex-p7-c0"],
    )

    sources = validate_sources(answer, RESULTS)

    assert [source.chunk_id for source in sources] == ["ex-p7-c0"]


def test_execute_copilot_without_tool(monkeypatch) -> None:
    answer = CopilotAnswer(
        answer="売上高は2,018,914百万円です。",
        is_answerable=True,
        source_chunk_ids=["ex-p7-c0"],
    )

    setup_fakes(
        monkeypatch,
        [final_response(answer)],
    )

    run = execute_copilot("売上高は？")

    assert run.tools_used == []
    assert [source.chunk_id for source in run.sources] == ["ex-p7-c0"]
    assert run.input_tokens == 100
    assert run.output_tokens == 20
    assert run.total_ms >= run.retrieval_ms


def test_execute_copilot_with_tool_sums_tokens(monkeypatch) -> None:
    answer = CopilotAnswer(
        answer="売上高成長率は10.0%です。",
        is_answerable=True,
        source_chunk_ids=["ex-p7-c0"],
    )

    fake = setup_fakes(
        monkeypatch,
        [tool_use_response(), final_response(answer)],
    )

    run = execute_copilot("売上高成長率は？")

    assert fake.calls == 2
    assert run.tools_used == ["calculate_financial_metrics"]
    assert run.input_tokens == 180
    assert run.output_tokens == 30


def test_execute_copilot_tool_failure(monkeypatch) -> None:
    """
    ツールの実行に失敗しても例外を外に出さず、Claude に失敗を伝えて続ける。
    失敗したツールは tools_used に入れない。
    """

    bad_block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="calculate_financial_metrics",
        input={"previous_revenue": "invalid"},  # 数値でないので入力の検証で失敗する
    )

    tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[bad_block],
        parsed_output=None,
        usage=SimpleNamespace(input_tokens=80, output_tokens=10),
    )

    answer = CopilotAnswer(
        answer="計算に必要な値を確認できませんでした。",
        is_answerable=False,
    )

    fake = setup_fakes(
        monkeypatch,
        [tool_use, final_response(answer)],
    )

    run = execute_copilot("売上高成長率は？")

    assert fake.calls == 2  # 失敗を伝えたあと、もう一度 Claude を呼んでいる
    assert run.tools_used == []
