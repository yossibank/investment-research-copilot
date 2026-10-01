"""
財務計算ツールの入力と結果の型。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class GrowthRateInput(BaseModel):
    """
    成長率ツールの入力。売上高または営業利益の、前期と当期の値。
    """

    # 定義にない項目が返ってきたら、黙って捨てずにエラーにする。
    model_config = ConfigDict(extra="forbid")

    item: Literal["revenue", "operating_income"]
    previous: float
    current: float


class GrowthRateResult(BaseModel):
    """
    成長率ツールの結果。前期が 0 で計算できない時は None。
    """

    growth_percent: float | None


class OperatingMarginInput(BaseModel):
    """
    営業利益率ツールの入力。同じ期間の売上高と営業利益。
    """

    model_config = ConfigDict(extra="forbid")

    revenue: float
    operating_income: float


class OperatingMarginResult(BaseModel):
    """
    営業利益ツールの結果。売上高が 0 で計算できない時は None。
    """

    operating_margin_percent: float | None
