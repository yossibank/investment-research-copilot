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
            name="calculate_financial_metrics",
            tool_input={
                "previous_inventory": 1066123,
                "current_inventory": 1179799,
            },
        )


def test_growth_rate_is_calculated_by_code() -> None:
    result_json = execute_tool(
        name="calculate_financial_metrics",
        tool_input={
            "previous_revenue": 208922,
            "current_revenue": 301921,
        },
    )

    result = json.loads(result_json)

    assert result["revenue_growth_percent"] == pytest.approx(44.5137, abs=1e-4)
    assert result["current_operating_margin_percent"] is None


def test_execute_financial_tool() -> None:
    result_json = execute_tool(
        name="calculate_financial_metrics",
        tool_input={
            "previous_revenue": 1000,
            "current_revenue": 1100,
            "previous_operating_income": 110,
            "current_operating_income": 132,
        },
    )

    result = json.loads(result_json)

    assert result["revenue_growth_percent"] == pytest.approx(10.0)
    assert result["current_operating_margin_percent"] == pytest.approx(12.0)


def test_unknown_tool() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown tool: delete_database",
    ):
        execute_tool(
            name="delete_database",
            tool_input={},
        )


def test_invalid_tool_input() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool: calculate_financial_metrics",
    ):
        execute_tool(
            name="calculate_financial_metrics",
            tool_input={
                "previous_revenue": "invalid",
            },
        )


def test_empty_tool_input_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool",
    ):
        execute_tool(
            name="calculate_financial_metrics",
            tool_input={},
        )


def test_signle_value_tool_input_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid input for tool",
    ):
        execute_tool(
            name="calculate_financial_metrics",
            tool_input={
                "current_revenue": 201894,
            },
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
    with pytest.raises(ValueError, match="Invalid input for tool: search_filing"):
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
