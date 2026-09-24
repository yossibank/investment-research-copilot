from pydantic import BaseModel


class FinancialMetricsInput(BaseModel):
    previous_revenue: float
    current_revenue: float
    previous_operating_income: float
    current_operating_income: float


class FinancialMetricsResult(BaseModel):
    revenue_growth_percent: float | None
    operating_income_growth_percent: float | None
    previous_operating_margin_percent: float | None
    current_operating_margin_percent: float | None
