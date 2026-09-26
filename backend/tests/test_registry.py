"""
ツールの許可リストと、入力の検証のテスト。
"""

import json

import pytest
from research_copilot.tools.registry import execute_tool


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
        match="Unknown tool",
    ):
        execute_tool(
            name="delete_database",
            tool_input={},
        )


def test_invalid_tool_input() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid financial tool input",
    ):
        execute_tool(
            name="calculate_financial_metrics",
            tool_input={
                "previous_revenue": "invalid",
            },
        )
