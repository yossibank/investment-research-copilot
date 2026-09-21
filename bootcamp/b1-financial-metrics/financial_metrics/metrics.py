def growth_rate(
    previous: float | None,
    current: float | None,
) -> float | None:
    """
    売上高・営業利益・EPSなどの前年同期比成長率を計算する。

    例:
        前年売上高(previous) = 100
        今年売上高(current) = 120

        (120 - 100) / 100 * 100 = 20%
    """

    if previous is None or current is None:
        return None

    if previous == 0:
        return None

    return (current - previous) / previous * 100


def operating_margin(
    revenue: float | None,
    operating_income: float | None,
) -> float | None:
    """
    営業利益率を計算する。

    営業利益率 = 営業利益 / 売上高 * 100

    例:
        売上高(revenue) = 1000
        営業利益(operating_income) = 100

        100 / 1000 * 100 = 10%
    """

    if revenue is None or operating_income is None:
        return None

    if revenue == 0:
        return None

    return operating_income / revenue * 100
