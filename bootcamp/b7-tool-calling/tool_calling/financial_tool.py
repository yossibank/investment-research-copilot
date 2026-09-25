from .models import FinancialMetricsInput, FinancialMetricsResult


def growth_rate(
    previous: float,
    current: float,
) -> float | None:
    """
    成長率を計算する。

    Formula:

    (current - previous)
    -------------------- × 100
          previous
    """

    if previous == 0:
        return None

    return (current - previous) / previous * 100


def operating_margin(
    revenue: float,
    operating_income: float,
) -> float | None:
    """
    営業利益率を計算する。

    Formula:

    operating_income
    ---------------- × 100
        revenue
    """

    if revenue == 0:
        return None

    return operating_income / revenue * 100


def calculate_financial_metrics(
    tool_input: FinancialMetricsInput,
) -> FinancialMetricsResult:
    """
    Claudeから渡された数値を使って財務指標を決定論的に計算する。

    重要:
        計算自体はLLMにさせない。
    """

    revenue_growth = None

    if (
        tool_input.previous_revenue is not None
        and tool_input.current_revenue is not None
    ):
        revenue_growth = growth_rate(
            tool_input.previous_revenue,
            tool_input.current_revenue,
        )

    operating_income_growth = None

    if (
        tool_input.previous_operating_income is not None
        and tool_input.current_operating_income is not None
    ):
        operating_income_growth = growth_rate(
            tool_input.previous_operating_income,
            tool_input.current_operating_income,
        )

    previous_margin = None

    if (
        tool_input.previous_revenue is not None
        and tool_input.previous_operating_income is not None
    ):
        previous_margin = operating_margin(
            tool_input.previous_revenue,
            tool_input.previous_operating_income,
        )

    current_margin = None

    if (
        tool_input.current_revenue is not None
        and tool_input.current_operating_income is not None
    ):
        current_margin = operating_margin(
            tool_input.current_revenue,
            tool_input.current_operating_income,
        )

    return FinancialMetricsResult(
        revenue_growth_percent=revenue_growth,
        operating_income_growth_percent=operating_income_growth,
        previous_operating_margin_percent=previous_margin,
        current_operating_margin_percent=current_margin,
    )
