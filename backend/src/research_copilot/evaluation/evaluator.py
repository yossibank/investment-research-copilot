"""
評価データの全問で Copilot を実行し、採点・集計して結果を保存する。Claude API を呼ぶ。

実行: python -m research_copilot.evaluation.evaluator --limit 3
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from time import perf_counter

from ..agent.orchestrator import execute_copilot
from ..paths import EVALUATION_DIR, REPO_ROOT
from ..retrieval.embeddings import MODEL_NAME
from ..retrieval.search import search
from .metrics import summarize
from .models import EvalResult, GoldenCase
from .scoring import failed_result, score_case

DEFAULT_DATASET = EVALUATION_DIR / "datasets" / "golden_mvp.jsonl"

RESULTS_DIR = EVALUATION_DIR / "results"


def load_golden_cases(path: Path = DEFAULT_DATASET) -> list[GoldenCase]:
    """
    JSONL を 1 行ずつ GoldenCase へ変換する。
    """

    cases: list[GoldenCase] = []

    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            cases.append(GoldenCase.model_validate_json(line))

    return cases



def git_commit() -> str:
    """
    評価したコードの commit を返す。未 commit の変更があれば末尾に -dirty を付ける。
    """

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
    """
    結果ファイルに記録するため、リポジトリのルートからの相対パスにする。
    """

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)



def warmup() -> float:
    """
    埋め込みモデルの読み込みを先に済ませる（Claude API は呼ばない）。
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
    """
    評価データの全問で Copilot を実行して採点し、結果を evaluation/results/ に保存する。
    """

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

        except Exception as error:  # 1 問の失敗で全体を止めない
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
