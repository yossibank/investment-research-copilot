from pathlib import Path

import pandas as pd

from .metrics import growth_rate, operating_margin

# __file__
# -> 現在のPythonファイル自身のパス
#
# Path(__file__)
# -> 文字列ではなくPathオブジェクトとして扱う
# -> (.../b1-financial-metrics/financial_metrics/analyze.py)
#
# resolve()
# -> 絶対パスへ変換
# -> (/Users/Home/.../investment-research-copilot/bootcamp/b1-financial-metrics/financial_metrics/analyze.py)
#
# parents[1]
# -> 2階層上のディレクトリを取得
# -> (/Users/Home/.../investment-research-copilot/bootcamp/b1-financial-metrics)
#
# プロジェクト内のファイルを参照しやすくする
BASE_DIR = Path(__file__).resolve().parents[1]

FINANCIALS_PATH = BASE_DIR / "data" / "financials.csv"
PRICES_PATH = BASE_DIR / "data" / "prices.csv"


def format_percentage(value: float | None) -> str:
    """
    floatの数値を、%表記へ変換する。

    例:
        10.123 -> "10.1%"
        None -> "N/A"
    """

    if value is None:
        return "N/A"

    return f"{value:.1f}%"


def main() -> None:
    # ======================================================
    # 1. CSVファイルを読み込む
    # ======================================================

    # pd.read_csv()
    #
    # CSVをpandasのDataFrameへ変換する。
    #
    # DataFrameとはExcelの表のような「行と列」を持つデータ構造
    financials = pd.read_csv(FINANCIALS_PATH)

    # CSVをpandasのDataFrameへ変換する。
    #
    # parse_dates=["date"]を指定すると、日付型(datetime)として読み込まれる。
    prices = pd.read_csv(PRICES_PATH, parse_dates=["date"])

    # ======================================================
    # 2. 財務データの品質を確認する
    # ======================================================

    print("=== Financial Data Check ===")

    # ------------------------------------------------------
    # 欠損値の確認
    # ------------------------------------------------------

    print("\nMissing values:")

    # .isna()
    #
    # 各セルが欠損値ならTrue、値が存在すればFalseを返す。
    #
    # .sum()
    #
    # Trueを1、Falseを0として合計値を返す。
    print(financials.isna().sum())

    # ------------------------------------------------------
    # 重複行の確認
    # ------------------------------------------------------

    print("\nDuplicates:")

    # .duplicated()
    #
    # すでに同じ内容の行が存在する場合にTrueを返す。
    print(financials.duplicated().sum())

    # ------------------------------------------------------
    # データ型の確認
    # ------------------------------------------------------

    print("\nData types:")

    # dtypes
    #
    # 各列がint,float,objectなどのどの型として読み込まれたかを確認する。
    print(financials.dtypes)

    # ======================================================
    # 3. 比較する2期間を取得する
    # ======================================================

    # iloc
    # 「行番号」でDataFrameからデータを取り出す。(負のindex)
    #
    # -1 -> 最後の行
    # -2 -> 最後から2番目の行

    previous = financials.iloc[-2]
    current = financials.iloc[-1]

    # ======================================================
    # 4. 売上高成長率を計算
    # ======================================================

    # previous["revenue_million_jpy"], current["revenue_million_jpy"]
    #
    # previous行の
    # revenue_million_jpy列の値を取得する。
    revenue_growth = growth_rate(
        previous["revenue_million_jpy"],
        current["revenue_million_jpy"],
    )

    # ======================================================
    # 5. 営業利益の前年比成長率
    # ======================================================

    operating_income_growth = growth_rate(
        previous["operating_income_million_jpy"],
        current["operating_income_million_jpy"],
    )

    # ======================================================
    # 6. 前年の営業利益率
    # ======================================================

    previous_margin = operating_margin(
        previous["revenue_million_jpy"],
        previous["operating_income_million_jpy"],
    )

    # ======================================================
    # 7. 今年の営業利益率
    # ======================================================

    current_margin = operating_margin(
        current["revenue_million_jpy"],
        current["operating_income_million_jpy"],
    )

    # ======================================================
    # 8. EPS成長率
    # ======================================================

    eps_growth = growth_rate(
        previous["eps_jpy"],
        current["eps_jpy"],
    )

    # ======================================================
    # 9. 計算結果を表示
    # ======================================================

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

    # ======================================================
    # 10. pandas練習: 日次リターンを計算
    # ======================================================

    # pct_change()
    #
    # 前の行から何%変化したかを計算する。

    prices["daily_return_pct"] = prices["close_jpy"].pct_change() * 100

    # ======================================================
    # 11. pandas練習: 3日移動平均
    # ======================================================

    # rolling(3)
    #
    # 3行ずつの窓を作る。
    #
    # mean()
    #
    # 3行の平均値を計算する。

    prices["ma3"] = prices["close_jpy"].rolling(3).mean()

    print("\n=== Price Data ===")

    # 加工後のDataFrame全体を表示する。
    print(prices)


if __name__ == "__main__":
    main()
