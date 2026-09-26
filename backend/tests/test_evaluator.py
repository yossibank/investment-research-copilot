"""
Copilot の実行結果の採点と集計のテスト。Claude API は呼ばない。
"""

from research_copilot.agent.models import CopilotAnswer, CopilotRun, ResearchSource
from research_copilot.evaluation.metrics import percentile, summarize
from research_copilot.evaluation.models import GoldenCase
from research_copilot.evaluation.scoring import score_case
from research_copilot.retrieval.models import Chunk


def make_run(
    answer: str,
    is_answerable: bool,
    source_ids: list[str],
    tools_used: list[str] | None = None,
) -> CopilotRun:
    chunk = Chunk(
        chunk_id="ex-p7-c0",
        text="",
        company="Example",
        period="",
        document_name="決算短信",
        page=7,
        source_url="https://example.com",
    )

    sources = [
        ResearchSource(
            chunk_id=source_id,
            company="Example",
            document_name="決算短信",
            page=7,
            score=0.9,
            source_url="https://example.com",
        )
        for source_id in source_ids
    ]

    return CopilotRun(
        answer=CopilotAnswer(
            answer=answer,
            is_answerable=is_answerable,
            source_chunk_ids=source_ids,
        ),
        results=[(chunk, 0.9)],
        sources=sources,
        tools_used=tools_used or [],
        retrieval_ms=10.0,
        total_ms=1000.0,
        input_tokens=100,
        output_tokens=20,
    )


def test_score_answerable_case() -> None:
    case = GoldenCase(
        id="t1",
        question="売上高は？",
        expected_answer="2,018,914百万円",
        expected_answerable=True,
        evidence_id="ex-p7-c0",
        evidence_page=7,
        required_terms=["2,018,914", "百万円"],
    )

    result = score_case(
        case, make_run("売上高は2,018,914百万円です。", True, ["ex-p7-c0"])
    )

    assert result.retrieval_hit is True
    assert result.answer_correct is True
    assert result.source_hit is True
    assert result.tool_correct is True  # expected_tool=None で、ツールも使っていない


def test_score_unanswerable_case_with_source_is_wrong() -> None:
    case = GoldenCase(
        id="t2",
        question="来月の株価は？",
        expected_answer="答えられない",
        expected_answerable=False,
        evidence_id=None,
        evidence_page=None,
        required_terms=[],
        category="unanswerable",
    )

    result = score_case(case, make_run("確認できません。", False, ["ex-p7-c0"]))

    assert result.retrieval_hit is None
    assert result.answer_correct is True
    assert result.source_hit is False  # 答えないのに出典を付けている


def test_score_missing_expected_tool() -> None:
    case = GoldenCase(
        id="t3",
        question="成長率は？",
        expected_answer="44.5%",
        expected_answerable=True,
        evidence_id="ex-p7-c0",
        evidence_page=7,
        required_terms=["44.5"],
        category="calculation",
        expected_tool="calculate_financial_metrics",
    )

    result = score_case(case, make_run("約44.5%です。", True, ["ex-p7-c0"]))

    assert result.answer_correct is True
    assert result.tool_correct is False  # 計算ツールを使っていない


def test_percentile() -> None:
    values = [float(v) for v in range(1, 21)]  # 1〜20

    assert percentile(values, 50) == 10.0
    assert percentile(values, 95) == 19.0
    assert percentile([], 50) is None


def test_summarize_counts_source_attribution_only_for_answered() -> None:
    case = GoldenCase(
        id="t4",
        question="q",
        expected_answer="a",
        expected_answerable=False,
        evidence_id=None,
        evidence_page=None,
        required_terms=[],
    )

    results = [
        score_case(case, make_run("確認できません。", False, [])),
        score_case(case, make_run("答えます。", True, [])),
    ]

    summary = summarize(results)

    assert summary["source_attribution_rate"] == 0.0  # 答えた 1 件に出典がない
    assert summary["answer_accuracy"] == 0.5
    assert summary["latency_ms_p50"] == 1000.0
