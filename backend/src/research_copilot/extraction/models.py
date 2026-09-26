"""
構造化抽出の結果の型。Claude の構造化出力の型としても使う。
"""

from pydantic import BaseModel


class FinancialMetric(BaseModel):
    """
    抽出した財務指標 1 つ。資料に値がなければ value は None。
    """

    name: str
    value: float | None
    unit: str | None
    period: str | None
    source_page: int | None


class Guidance(BaseModel):
    """
    会社の業績予想。実績とは分けて持つ。
    """

    revenue: float | None
    operating_income: float | None
    net_income: float | None
    unit: str | None
    period: str | None
    source_page: int | None


class FilingExtraction(BaseModel):
    """
    決算資料 1 件から抽出した結果。Claude の構造化出力の型として使う。
    """

    company: str
    revenue: FinancialMetric
    operating_income: FinancialMetric
    net_income: FinancialMetric
    guidance: Guidance | None
