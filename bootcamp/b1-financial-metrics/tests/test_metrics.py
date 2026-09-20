import pytest
from financial_metrics.metrics import growth_rate, operating_margin


def test_growth_rate() -> None:
    result = growth_rate(
        previous=100,
        current=110,
    )

    assert result == pytest.approx(10.0)


def test_growth_rate_decrease() -> None:
    result = growth_rate(
        previous=100,
        current=80,
    )

    assert result == pytest.approx(-20.0)


def test_growth_rate_previous_zero() -> None:
    result = growth_rate(
        previous=0,
        current=100,
    )

    assert result is None


def test_operating_margin() -> None:
    result = operating_margin(
        revenue=1000,
        operating_income=100,
    )

    assert result == pytest.approx(10.0)


def test_operating_margin_zero_revenue() -> None:
    result = operating_margin(
        revenue=0,
        operating_income=100,
    )

    assert result is None
