"""
採点結果の集計（正解率・レイテンシのパーセンタイル・トークン数）。Claude API は呼ばない。
"""

import math

from .models import EvalResult


def percentile(values: list[float], p: float) -> float | None:
    """
    nearest-rank 法のパーセンタイル。p50 / p95 に使う。
    """

    if not values:
        return None

    ordered = sorted(values)
    rank = math.ceil(p / 100 * len(ordered))

    return ordered[max(rank, 1) - 1]



def rate(flags: list[bool]) -> float | None:
    """
    True の割合を返す。対象が 0 件なら None（0% と区別するため）。
    """

    if not flags:
        return None

    return sum(flags) / len(flags)



def summarize(results: list[EvalResult]) -> dict:
    """
    全問の採点結果から、指標ごとの正解率・レイテンシ・トークン数を集計する。
    """

    retrieval_results = [r for r in results if r.retrieval_hit is not None]
    answered = [r for r in results if r.actual_answerable]
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]

    token_results = [r for r in results if r.input_tokens is not None]

    by_category: dict[str, dict] = {}

    for category in sorted({r.category for r in results}):
        items = [r for r in results if r.category == category]
        by_category[category] = {
            "total": len(items),
            "answer_accuracy": rate([r.answer_correct for r in items]),
        }

    return {
        "total": len(results),
        "errors": sum(r.error is not None for r in results),
        "retrieval_cases": len(retrieval_results),
        "recall_at_5": rate([bool(r.retrieval_hit) for r in retrieval_results]),
        "page_recall_at_5": rate([bool(r.page_hit) for r in retrieval_results]),
        "answer_accuracy": rate([r.answer_correct for r in results]),
        "source_match_rate": rate([r.source_hit for r in results]),
        # 「答えた」ケースのうち、検証後の出典が 1 つ以上付いた割合
        "source_attribution_rate": rate(
            [len(r.source_chunk_ids) > 0 for r in answered]
        ),
        "tool_selection_accuracy": rate([r.tool_correct for r in results]),
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "input_tokens_total": sum(r.input_tokens or 0 for r in token_results)
        if token_results
        else None,
        "output_tokens_total": sum(r.output_tokens or 0 for r in token_results)
        if token_results
        else None,
        # 料金はモデルと時期で変わるため、ここでは計算しない。
        "cost_usd": None,
        "cost_note": "未測定（トークン数のみ記録）",
        "by_category": by_category,
    }
