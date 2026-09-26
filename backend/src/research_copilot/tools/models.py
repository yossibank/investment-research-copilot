"""
財務計算ツールの入力と結果の型。
"""

from pydantic import BaseModel


class FinancialMetricsInput(BaseModel):
    """
    財務計算ツールの入力。Claude が資料から読み取った数値が入り、ない値は None。
    """

    previous_revenue: float | None = None
    current_revenue: float | None = None
    previous_operating_income: float | None = None
    current_operating_income: float | None = None


class FinancialMetricsResult(BaseModel):
    """
    財務計算ツールの結果。計算できなかった指標は None。
    """

    revenue_growth_percent: float | None
    operating_income_growth_percent: float | None
    previous_operating_margin_percent: float | None
    current_operating_margin_percent: float | None
