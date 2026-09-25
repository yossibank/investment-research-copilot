from pydantic import BaseModel


class FinancialMetricsInput(BaseModel):
    previous_revenue: float | None = None
    current_revenue: float | None = None
    previous_operating_income: float | None = None
    current_operating_income: float | None = None


class FinancialMetricsResult(BaseModel):
    revenue_growth_percent: float | None
    operating_income_growth_percent: float | None
    previous_operating_margin_percent: float | None
    current_operating_margin_percent: float | None
