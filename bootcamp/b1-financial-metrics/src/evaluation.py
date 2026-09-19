def recall_at_k(
    retrieved_ids: list[str],
    expected_id: str,
    k: int = 5,
) -> float:
    """
    正解の根拠がTop-Kに入っていれば1.0、
    入っていなければ0.0。
    """

    top_k = retrieved_ids[:k]

    return 1.0 if expected_id in top_k else 0.0
