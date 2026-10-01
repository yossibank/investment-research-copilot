"""
execute_copilot のテスト。検索と Claude API を偽物に差し替える。
"""

from types import SimpleNamespace

import pytest
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
        self.last_messages: list = []

    def create(self, **kwargs):
        self.last_messages = kwargs["messages"]
        response = self.responses[self.calls]
        self.calls += 1
        return response


def final_response(
    answer: CopilotAnswer, input_tokens: int = 100, output_tokens: int = 20
):
    block = SimpleNamespace(
        type="tool_use",
        id="toolu_answer",
        name="submit_answer",
        input=answer.model_dump(),
    )

    return SimpleNamespace(
        stop_reason="tool_use",
        content=[block],
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def tool_use_response():
    block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="calculate_growth_rate",
        input={
            "item": "revenue",
            "previous": 100,
            "current": 110,
        },
    )

    return SimpleNamespace(
        stop_reason="tool_use",
        content=[block],
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
    assert run.tools_used == ["calculate_growth_rate"]
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
        name="calculate_growth_rate",
        input={"item": "revenue", "previous": "invalid", "current": 100},  # 数値でないので入力の検証で失敗する
    )

    tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[bad_block],
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


def test_execute_copilot_rejects_tool_outside_allowlist(monkeypatch) -> None:
    """
    許可リストにないツールは実行せず、is_error の tool_result を Claude に返す。
    """

    unknown_block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="delete_database",
        input={},
    )

    tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[unknown_block],
        usage=SimpleNamespace(input_tokens=80, output_tokens=10),
    )

    answer = CopilotAnswer(
        answer="その操作はできません。",
        is_answerable=False,
    )

    fake = setup_fakes(
        monkeypatch,
        [tool_use, final_response(answer)],
    )

    run = execute_copilot("データベースを消して")

    tool_result = fake.last_messages[-1]["content"][0]

    assert tool_result["tool_use_id"] == "toolu_1"
    assert tool_result["is_error"] is True
    assert run.tools_used == []


def test_execute_copilot_records_failed_tool_call(monkeypatch) -> None:
    """
    失敗した呼び出しも、入力と一緒に tool_calls に残る（tools_used には入らない）。
    """

    empty_block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="calculate_growth_rate",
        input={},
    )

    tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[empty_block],
        usage=SimpleNamespace(input_tokens=80, output_tokens=10),
    )

    answer = CopilotAnswer(
        answer="棚卸資産は1,179,799百万円です。",
        is_answerable=True,
        source_chunk_ids=["ex-p7-c0"],
    )

    setup_fakes(
        monkeypatch,
        [tool_use, final_response(answer)],
    )

    run = execute_copilot("棚卸資産は？")

    assert run.tools_used == []

    assert [(call.name, call.input, call.succeeded) for call in run.tool_calls] == [
        ("calculate_growth_rate", {}, False)
    ]


def test_execute_copilot_accepts_source_from_search_tool(monkeypatch) -> None:
    """
    追加検索で見つけたチャンクは出典として認める。
    """

    from research_copilot.tools import search_tool

    extra_chunk = make_chunk("ex-p6-c1", 6)

    monkeypatch.setattr(
        search_tool,
        "search",
        lambda query, top_k: [(extra_chunk, 0.7)],
    )

    search_block = SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="search_filing",
        input={"query": "資本合計"},
    )

    tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[search_block],
        usage=SimpleNamespace(input_tokens=80, output_tokens=10),
    )

    answer = CopilotAnswer(
        answer="資本合計は5,574,729百万円です。",
        is_answerable=True,
        source_chunk_ids=["ex-p6-c1"],
    )

    setup_fakes(monkeypatch, [tool_use, final_response(answer)])

    run = execute_copilot("資本合計は？")

    assert [source.chunk_id for source in run.sources] == ["ex-p6-c1"]
    assert "ex-p6-c1" not in [chunk.chunk_id for chunk, _ in run.results]


def test_execute_copilot_fails_without_submit_answer(monkeypatch) -> None:
    """
    Claude が submit_answer を呼ばずに文章だけで終えたら、エラーにする。
    """

    text_only = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text="負債合計は4,852,951百万円です。")],
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )

    setup_fakes(monkeypatch, [text_only])

    with pytest.raises(RuntimeError, match="submit_answer"):
        execute_copilot("負債合計は？")
