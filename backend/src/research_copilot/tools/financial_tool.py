"""
財務指標（成長率・営業利益率）の計算。Claude が要求したときにツールとして実行される。
"""

from .models import (
    GrowthRateInput,
    GrowthRateResult,
    OperatingMarginInput,
    OperatingMarginResult,
)


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


def calculate_growth_rate(
    tool_input: GrowthRateInput,
) -> GrowthRateResult:
    """
    Claude から渡された前期と当期の値で、成長率を計算する。

    LLM は計算を間違えることがあるため、計算は Python で行う。
    """

    return GrowthRateResult(
        growth_percent=growth_rate(
            tool_input.previous,
            tool_input.current,
        )
    )


def calculate_operating_margin(
    tool_input: OperatingMarginInput,
) -> OperatingMarginResult:
    """
    Claude から渡された売上高と営業利益で、営業利益率を計算する。
    """

    return OperatingMarginResult(
        operating_margin_percent=operating_margin(
            tool_input.revenue,
            tool_input.operating_income,
        )
    )
