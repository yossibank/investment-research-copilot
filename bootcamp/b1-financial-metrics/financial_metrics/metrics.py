def growth_rate(
    previous: float | None,
    current: float | None,
) -> float | None:
    """
    前期比を%で返す。

    例:
    previous = 100
    current = 110

    -> 10.0
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
    営業利益率を%で返す。

    例:
    revenue = 1000
    operating_income = 100

    -> 10.0
    """

    if revenue is None or operating_income is None:
        return None

    if revenue == 0:
        return None

    return operating_income / revenue * 100
