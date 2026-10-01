"""
財務指標の計算のテスト。
"""

import pytest
from research_copilot.tools.financial_tool import (
    calculate_growth_rate,
    calculate_operating_margin,
)
from research_copilot.tools.models import GrowthRateInput, OperatingMarginInput


def test_calculate_growth_rate() -> None:
    result = calculate_growth_rate(
        GrowthRateInput(
            previous=1000,
            current=1100,
        )
    )

    assert result.growth_percent == pytest.approx(10.0)


def test_growth_rate_with_zero_previous_is_none() -> None:
    result = calculate_growth_rate(
        GrowthRateInput(
            previous=0,
            current=100,
        )
    )

    assert result.growth_percent is None


def test_calculate_operating_margin() -> None:
    result = calculate_operating_margin(
        OperatingMarginInput(
            revenue=1100,
            operating_income=132,
        )
    )

    assert result.operating_margin_percent == pytest.approx(12.0)


def test_operating_margin_with_zero_revenue_is_none() -> None:
    result = calculate_operating_margin(
        OperatingMarginInput(
            revenue=0,
            operating_income=10,
        )
    )

    assert result.operating_margin_percent is None
