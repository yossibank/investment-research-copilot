from .models import FinancialMetricsInput, FinancialMetricsResult


def growth_rate(
    previous: float,
    current: float,
) -> float | None:
    """
    成長率（%）を計算する。前期が 0 なら計算できないので None を返す。

    計算式:

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
    営業利益率（%）を計算する。売上高が 0 なら計算できないので None を返す。

    計算式:

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
    Claude から渡された数値で、成長率と営業利益率を計算する。

    LLM は計算を間違えることがあるため、計算は Python で行う。
    入力がそろわない指標は None のままにする。
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
