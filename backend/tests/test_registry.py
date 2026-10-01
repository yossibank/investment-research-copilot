"""
ツールの許可リストと、入力の検証のテスト。
"""

import json

import pytest
from research_copilot.tools.registry import TOOL_HANDLERS, TOOLS, execute_tool


def test_every_tool_definition_has_handler() -> None:
    """
    Claude に見せるツールと実行できるツール（許可リスト）が一致している。
    """

    assert {tool["name"] for tool in TOOLS} == set(TOOL_HANDLERS)


def test_unexpected_tool_input_field_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool",
    ):
        execute_tool(
            name="calculate_growth_rate",
            tool_input={
                "item": "revenue",
                "previous": 1066123,
                "current": 1179799,
                "note": "inventory",
            },
        )


def test_growth_rate_is_calculated_by_code() -> None:
    result = json.loads(
        execute_tool(
            name="calculate_growth_rate",
            tool_input={"item": "revenue", "previous": 208922, "current": 301921},
        )
    )

    assert result["growth_percent"] == pytest.approx(44.5137, abs=1e-4)


def test_operating_margin_is_calculated_by_code() -> None:
    result = json.loads(
        execute_tool(
            name="calculate_operating_margin",
            tool_input={"revenue": 1100, "operating_income": 132},
        )
    )

    assert result["operating_margin_percent"] == pytest.approx(12.0)


def test_invalid_tool_input() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool: calculate_growth_rate",
    ):
        execute_tool(
            name="calculate_growth_rate",
            tool_input={"item": "revenue", "previous": "invalid", "current": 100},
        )


def test_empty_tool_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid input for tool"):
        execute_tool(
            name="calculate_growth_rate",
            tool_input={},
        )


def test_single_value_tool_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid input for tool"):
        execute_tool(
            name="calculate_growth_rate",
            tool_input={"current": 201894},
        )


def test_growth_rate_rejects_other_items() -> None:
    """
    売上高と営業利益以外（売上総利益など）の成長率は計算しない。
    """

    with pytest.raises(ValueError, match="Invalid input for tool"):
        execute_tool(
            name="calculate_growth_rate",
            tool_input={"item": "gross_profit", "previous": 603751, "current": 665899},
        )


def test_unknown_tool() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown tool: delete_database",
    ):
        execute_tool(
            name="delete_database",
            tool_input={},
        )


def test_search_filing_returns_chunks(monkeypatch) -> None:
    from research_copilot.retrieval.models import Chunk
    from research_copilot.tools import search_tool

    chunk = Chunk(
        chunk_id="ex-p6-c1",
        text="資本合計 5,574,729",
        company="Example",
        period="2027年3月期 第一四半期",
        document_name="決算短信",
        page=6,
        source_url="https://exmaple.com",
    )

    monkeypatch.setattr(
        search_tool,
        "search",
        lambda query, top_k: [(chunk, 0.8)],
    )

    result = json.loads(
        execute_tool(
            name="search_filing",
            tool_input={"query": "資本合計"},
        )
    )

    assert result["hits"][0]["chunk"]["chunk_id"] == "ex-p6-c1"


def test_search_filing_rejects_blank_query() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool: search_filing",
    ):
        execute_tool(
            name="search_filing",
            tool_input={"query": "   "},
        )


def test_list_available_filings() -> None:
    result = json.loads(
        execute_tool(
            name="list_available_filings",
            tool_input={},
        ),
    )

    assert len(result["filings"]) == 1
    assert result["filings"][0]["company"]


def test_list_available_filings_takes_no_arguments() -> None:
    with pytest.raises(ValueError, match="Invalid input for tool"):
        execute_tool(
            name="list_available_filings",
            tool_input={"company": "ソニーグループ"},
        )
