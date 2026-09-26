import argparse
import json
import math
import os
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path
from time import perf_counter

from ..api.copilot import CopilotRun, execute_copilot
from ..paths import EVALUATION_DIR, REPO_ROOT
from ..retrieval.embeddings import MODEL_NAME
from ..retrieval.search import search
from .models import EvalResult, GoldenCase

DEFAULT_DATASET = EVALUATION_DIR / "datasets" / "golden_mvp.jsonl"

RESULTS_DIR = EVALUATION_DIR / "results"


def normalize_text(text: str) -> str:
    """
    回答を比較しやすくするため、表記揺れをある程度吸収する。

    例:
        売上高 1,100 億円
            ↓
        売上高1100億円
    """

    # NFKCで全角・半角などをある程度統一する。
    text = unicodedata.normalize("NFKC", text)

    return text.lower().replace(" ", "").replace("\n", "").replace(",", "")


def contains_required_terms(
    answer: str,
    required_terms: list[str],
) -> bool:
    """
    Claudeの回答に、Golden Setで指定した情報が全て含まれているか確認する。
    """

    normalized_answer = normalize_text(answer)

    return all(normalize_text(term) in normalized_answer for term in required_terms)


def load_golden_cases(path: Path = DEFAULT_DATASET) -> list[GoldenCase]:
    """
    JSONLを1行ずつGoldenCaseへ変換する。
    """

    cases: list[GoldenCase] = []

    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            cases.append(GoldenCase.model_validate_json(line))

    return cases


# ============================================================
# 1問の採点（APIを呼ばないのでテストできる）
# ============================================================


def score_case(case: GoldenCase, run: CopilotRun) -> EvalResult:
    """
    Copilotの実行結果(CopilotRun)をGoldenCaseと照合して採点する。

    出典は「Claudeが返したID」ではなく、
    検索結果と照合した後の run.sources で採点する。
    """

    retrieved_ids = [chunk.chunk_id for chunk, _ in run.results]
    retrieved_pages = [chunk.page for chunk, _ in run.results]
    source_ids = [source.chunk_id for source in run.sources]

    answer = run.answer

    if case.expected_answerable:
        if case.evidence_id is None or case.evidence_page is None:
            raise RuntimeError(f"{case.id}: evidence_id / evidence_page is required.")

        retrieval_hit: bool | None = case.evidence_id in retrieved_ids
        page_hit: bool | None = case.evidence_page in retrieved_pages

        answer_correct = answer.is_answerable and contains_required_terms(
            answer=answer.answer,
            required_terms=case.required_terms,
        )

        source_hit = case.evidence_id in source_ids

    else:
        # 回答不能ケースは正解Chunkがないので検索の評価対象外。
        retrieval_hit = None
        page_hit = None

        answer_correct = not answer.is_answerable

        # 答えられないのに出典を付けていないか。
        source_hit = len(source_ids) == 0

    # ツール選択:
    #   expected_tool あり → そのツールを使った
    #   expected_tool なし → ツールを1つも使っていない
    if case.expected_tool is None:
        tool_correct = len(run.tools_used) == 0
    else:
        tool_correct = case.expected_tool in run.tools_used

    return EvalResult(
        id=case.id,
        question=case.question,
        category=case.category,
        expected_answerable=case.expected_answerable,
        actual_answerable=answer.is_answerable,
        retrieval_hit=retrieval_hit,
        page_hit=page_hit,
        answer_correct=answer_correct,
        source_hit=source_hit,
        tool_correct=tool_correct,
        answer=answer.answer,
        expected_tool=case.expected_tool,
        tools_used=run.tools_used,
        retrieved_chunk_ids=retrieved_ids,
        source_chunk_ids=source_ids,
        expected_evidence_id=case.evidence_id,
        latency_ms=round(run.total_ms, 1),
        retrieval_ms=round(run.retrieval_ms, 1),
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
    )


def failed_result(case: GoldenCase, error: Exception) -> EvalResult:
    """
    APIエラーなどで実行できなかったケース。全指標を失敗として数える。
    """

    return EvalResult(
        id=case.id,
        question=case.question,
        category=case.category,
        expected_answerable=case.expected_answerable,
        actual_answerable=False,
        retrieval_hit=False if case.expected_answerable else None,
        page_hit=False if case.expected_answerable else None,
        answer_correct=False,
        source_hit=False,
        tool_correct=False,
        answer="",
        expected_tool=case.expected_tool,
        expected_evidence_id=case.evidence_id,
        error=f"{type(error).__name__}: {error}",
    )


# ============================================================
# 集計（APIを呼ばないのでテストできる）
# ============================================================


def percentile(values: list[float], p: float) -> float | None:
    """
    nearest-rank法のパーセンタイル。p50 / p95 に使う。
    """

    if not values:
        return None

    ordered = sorted(values)
    rank = math.ceil(p / 100 * len(ordered))

    return ordered[max(rank, 1) - 1]


def rate(flags: list[bool]) -> float | None:
    if not flags:
        return None

    return sum(flags) / len(flags)


def summarize(results: list[EvalResult]) -> dict:
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
        # 「答えた」ケースのうち、検証後の出典が1つ以上付いた割合
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


# ============================================================
# 実行
# ============================================================


def git_commit() -> str:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        return f"{commit}-dirty" if dirty else commit

    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def warmup() -> float:
    """
    埋め込みモデルの読み込みを先に済ませる（Claude APIは呼ばない）。
    初回だけ遅い時間をレイテンシの集計に混ぜないため。
    """

    started = perf_counter()
    search("ウォームアップ", top_k=1)

    return (perf_counter() - started) * 1000


def evaluate(
    dataset: Path = DEFAULT_DATASET,
    limit: int | None = None,
    top_k: int = 5,
    save_as: str | None = None,
) -> dict:
    cases = load_golden_cases(dataset)

    if limit is not None:
        cases = cases[:limit]

    if not cases:
        raise RuntimeError("No golden cases found.")

    if save_as and limit is not None:
        raise RuntimeError("--save-as は全件実行（--limit なし）のときだけ使えます。")

    warmup_ms = warmup()
    print(f"warmup: {warmup_ms:.0f} ms")

    results: list[EvalResult] = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.id} {case.question}")

        try:
            run = execute_copilot(case.question, top_k=top_k)
            results.append(score_case(case, run))

        except Exception as error:  # 1問の失敗で全体を止めない
            print(f"  ! failed: {error}")
            results.append(failed_result(case, error))

    report = {
        "metadata": {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "git_commit": git_commit(),
            "model": os.getenv("ANTHROPIC_MODEL"),
            "embedding_model": MODEL_NAME,
            "top_k": top_k,
            "dataset": display_path(dataset),
            "limit": limit,
            "warmup_ms": round(warmup_ms, 1),
        },
        "summary": summarize(results),
        "results": [result.model_dump() for result in results],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    text = json.dumps(report, ensure_ascii=False, indent=2)

    (RESULTS_DIR / "latest.json").write_text(text + "\n", encoding="utf-8")

    if save_as:
        (RESULTS_DIR / f"{save_as}.json").write_text(text + "\n", encoding="utf-8")

    print("\n=== Evaluation Summary ===")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    return report


def main() -> None:
    """
    python -m research_copilot.evaluation.evaluator --limit 1
    python -m research_copilot.evaluation.evaluator --limit 3
    python -m research_copilot.evaluation.evaluator --save-as mvp-baseline
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--save-as", type=str, default=None)

    args = parser.parse_args()

    evaluate(
        dataset=args.dataset.resolve(),
        limit=args.limit,
        top_k=args.top_k,
        save_as=args.save_as,
    )


if __name__ == "__main__":
    main()
