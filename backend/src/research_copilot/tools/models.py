"""
財務計算ツールの入力と結果の型。
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class FinancialMetricsInput(BaseModel):
    """
    財務計算ツールの入力。Claude が資料から読み取った数値が入り、ない値は None。
    """

    # 定義にない項目が返ってきたら、黙って捨てずにエラーにする。
    model_config = ConfigDict(extra="forbid")

    previous_revenue: float | None = None
    current_revenue: float | None = None
    previous_operating_income: float | None = None
    current_operating_income: float | None = None

    @model_validator(mode="after")
    def require_computable_pair(self) -> Self:
        """
        指標を 1 つも計算できない入力（空の入力など）をエラーにする。
        """

        pairs = [
            (self.previous_revenue, self.current_revenue),
            (self.previous_operating_income, self.current_operating_income),
            (self.previous_revenue, self.previous_operating_income),
            (self.current_revenue, self.current_operating_income),
        ]

        if not any(a is not None and b is not None for a, b in pairs):
            raise ValueError("No metric can be calculated from the given values.")

        return self


class FinancialMetricsResult(BaseModel):
    """
    財務計算ツールの結果。計算できなかった指標は None。
    """

    revenue_growth_percent: float | None
    operating_income_growth_percent: float | None
    previous_operating_margin_percent: float | None
    current_operating_margin_percent: float | None
