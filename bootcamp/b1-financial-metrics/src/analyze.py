from pathlib import Path

import pandas as pd

from .metrics import growth_rate, operating_margin

BASE_DIR = Path(__file__).resolve().parents[1]

FINANCIALS_PATH = BASE_DIR / "data" / "financials.csv"
PRICES_PATH = BASE_DIR / "data" / "prices.csv"


def format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value:.1f}%"


def main() -> None:
    financials = pd.read_csv(FINANCIALS_PATH)
    prices = pd.read_csv(PRICES_PATH, parse_dates=["date"])

    print("=== Financial Data Check ===")

    print("\nMissing values:")
    print(financials.isna().sum())

    print("\nDuplicates:")
    print(financials.duplicated().sum())

    print("\nData types:")
    print(financials.dtypes)

    previous = financials.iloc[-2]
    current = financials.iloc[-1]

    revenue_growth = growth_rate(
        previous["revenue_million_jpy"],
        current["revenue_million_jpy"],
    )

    operating_income_growth = growth_rate(
        previous["operating_income_million_jpy"],
        current["operating_income_million_jpy"],
    )

    previous_margin = operating_margin(
        previous["revenue_million_jpy"],
        previous["operating_income_million_jpy"],
    )

    current_margin = operating_margin(
        current["revenue_million_jpy"],
        current["operating_income_million_jpy"],
    )

    eps_growth = growth_rate(
        previous["eps_jpy"],
        current["eps_jpy"],
    )

    print("\n=== Financial Metrics ===")

    print(f"Company: {current['company']}")
    print(f"Period: {current['period']}")

    print(
        "Revenue YoY:",
        format_percentage(revenue_growth),
    )

    print(
        "Operating Income YoY:",
        format_percentage(operating_income_growth),
    )

    print(
        "Previous Operating Margin:",
        format_percentage(previous_margin),
    )

    print(
        "Operating Margin:",
        format_percentage(current_margin),
    )

    print(
        "EPS YoY:",
        format_percentage(eps_growth),
    )

    # pandas練習
    prices["daily_return_pct"] = prices["close_jpy"].pct_change() * 100

    prices["ma3"] = prices["close_jpy"].rolling(3).mean()

    print("\n=== Price Data ===")
    print(prices)


if __name__ == "__main__":
    main()
