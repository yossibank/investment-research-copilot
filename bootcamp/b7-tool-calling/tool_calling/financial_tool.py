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

    return FinancialMetricsResult(
        revenue_growth_percent=growth_rate(
            tool_input.previous_revenue,
            tool_input.current_revenue,
        ),
        operating_income_growth_percent=growth_rate(
            tool_input.previous_operating_income,
            tool_input.current_operating_income,
        ),
        previous_operating_margin_percent=operating_margin(
            tool_input.previous_revenue,
            tool_input.previous_operating_income,
        ),
        current_operating_margin_percent=operating_margin(
            tool_input.current_revenue,
            tool_input.current_operating_income,
        ),
    )
