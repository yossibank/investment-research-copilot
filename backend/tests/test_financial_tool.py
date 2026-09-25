import pytest
from research_copilot.tools.financial_tool import calculate_financial_metrics
from research_copilot.tools.models import FinancialMetricsInput


def test_calculate_financial_metrics() -> None:
    tool_input = FinancialMetricsInput(
        previous_revenue=1000,
        current_revenue=1100,
        previous_operating_income=110,
        current_operating_income=132,
    )

    result = calculate_financial_metrics(tool_input)

    assert result.revenue_growth_percent == pytest.approx(10.0)
    assert result.operating_income_growth_percent == pytest.approx(20.0)
    assert result.previous_operating_margin_percent == pytest.approx(11.0)
    assert result.current_operating_margin_percent == pytest.approx(12.0)


def test_zero_previous_revenue() -> None:
    tool_input = FinancialMetricsInput(
        previous_revenue=0,
        current_revenue=100,
        previous_operating_income=0,
        current_operating_income=10,
    )

    result = calculate_financial_metrics(tool_input)

    assert result.revenue_growth_percent is None
    assert result.previous_operating_margin_percent is None


def test_current_margin_only() -> None:
    tool_input = FinancialMetricsInput(
        current_revenue=1100,
        current_operating_income=132,
    )

    result = calculate_financial_metrics(tool_input)

    assert result.current_operating_margin_percent == pytest.approx(12.0)
    assert result.revenue_growth_percent is None
    assert result.previous_operating_margin_percent is None
