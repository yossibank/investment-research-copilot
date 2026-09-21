def recall_at_k(
    retrieved_ids: list[str],
    expected_id: str,
    k: int = 5,
) -> float:
    """
    検索結果のTop-Kの中に、正解として期待しているIDが含まれているかを評価する。

    含まれている -> 1.0
    含まれていない -> 0.0
    """

    # 例:
    #
    # retrived_ids = [
    #   "chunk-10",
    #   "chunk-21",
    #   "chunk-35",
    #   "chunk-42",
    # ]
    #
    # [:k] = slice
    #
    # リストの先頭からk件だけ取得する。
    #
    # retrived_ids[:3] -> ["chunk-10", "chunk-21", "chunk-35"]
    top_k = retrieved_ids[:k]

    return 1.0 if expected_id in top_k else 0.0
