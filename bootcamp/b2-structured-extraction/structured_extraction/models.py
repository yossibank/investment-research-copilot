from pydantic import BaseModel


class FinancialMetric(BaseModel):
    name: str
    value: float | None
    unit: str | None
    period: str | None
    source_page: int | None


class Guidance(BaseModel):
    revenue: float | None
    operating_income: float | None
    net_income: float | None
    unit: str | None
    period: str | None
    source_page: int | None


class FilingExtraction(BaseModel):
    company: str
    revenue: FinancialMetric
    operating_income: FinancialMetric
    net_income: FinancialMetric
    guidance: Guidance | None
