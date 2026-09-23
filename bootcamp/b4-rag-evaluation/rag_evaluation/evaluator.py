import argparse
import json
import unicodedata
from pathlib import Path

from .models import EvalResult, GoldenCase
from .rag import answer_question

BASE_DIR = Path(__file__).resolve().parents[1]

GOLDEN_PATH = BASE_DIR / "eval" / "golden_20.jsonl"

RESULTS_DIR = BASE_DIR / "eval" / "results"


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

    例:
        answer:
            売上高は1,100億円です。

        required_terms:
            [
                "売上高",
                "1100億円"
            ]

        ↓

        True
    """

    normalized_answer = normalize_text(answer)

    # 全ての条件がTrueならTrue。
    return all(normalize_text(term) in normalized_answer for term in required_terms)


def load_golden_cases() -> list[GoldenCase]:
    """
    golden_20.jsonを読み込む。
    JSONLなので1行ごとにGoldenCaseへ変換する。
    """

    cases: list[GoldenCase] = []

    with GOLDEN_PATH.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            # JSON文字列
            # ↓
            # GoldenCase
            cases.append(GoldenCase.model_validate_json(line))

    return cases


def evaluate(limit: int | None = None) -> None:
    """
    Golden Setを使ってRAGを評価する。

    limit=None
        全件実行

    limit=1
        最初の1件だけ実行

    limit=3
        最初の3件だけ実行
    """

    cases = load_golden_cases()

    if limit is not None:
        cases = cases[:limit]

    if not cases:
        raise RuntimeError("No golden cases found.")

    results: list[EvalResult] = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.question}")

        # ====================================
        # RAG実行
        # ====================================

        answer, retrieved = answer_question(case.question, top_k=5)

        # RetrievedされたChunk ID一覧
        retrieved_ids = [chunk.chunk_id for chunk, _ in retrieved]

        # Retrievalされたページ一覧
        retrieved_pages = [chunk.page for chunk, _ in retrieved]

        # ====================================
        # Answerable Case
        # ====================================

        if case.expected_answerable:
            # 回答可能問題には、正解となるevidenceが必要。
            if case.evidence_id is None:
                raise RuntimeError(f"{case.id}: evidence_id is required.")

            if case.evidence_page is None:
                raise RuntimeError(f"{case.id}: evidencce_page is required.")

            # --------------------------------
            # Retrieval Evaluation
            # --------------------------------

            # 正解ChunkがTop-5の中にあるか。
            retrieval_hit = case.evidence_id in retrieved_ids

            # 正解ページがTop-5の中にあるか。
            page_hit = case.evidence_page in retrieved_pages

            # --------------------------------
            # Generation Evaluation
            # --------------------------------

            # Claudeが回答可能だと判断し、必須情報も全て回答に含んでいるか。
            answer_correct = answer.is_answerable and contains_required_terms(
                answer=answer.answer,
                required_terms=case.required_terms,
            )

            # --------------------------------
            # Source Attribution Evaluation
            # --------------------------------

            # Claude自身が指定したsourceの中に、Goldenの正解Chunkがあるか。
            source_hit = case.evidence_id in answer.source_chunk_ids

        # ====================================
        # Unanswerable Case
        # ====================================

        else:
            # 回答不能なケースには正解Chunk自体が存在しない。
            # そのため、Retrieval Recallの評価対象にしない。
            retrieval_hit = None
            page_hit = None

            # 回答不能ケースでは、is_answerable=Falseなら正解
            answer_correct = not answer.is_answerable

            # 答えられないのに、架空のsourceを付けていないか確認する。
            source_hit = (
                len(answer.source_chunk_ids) == 0 and len(answer.source_pages) == 0
            )

        # ====================================
        # 1問分の結果を保存
        # ====================================

        result = EvalResult(
            id=case.id,
            question=case.question,
            expected_answerable=case.expected_answerable,
            actual_answerable=answer.is_answerable,
            retrieval_hit=retrieval_hit,
            page_hit=page_hit,
            answer_correct=answer_correct,
            source_hit=source_hit,
            answer=answer.answer,
            retrieved_chunk_ids=retrieved_ids,
            expected_evidence_id=case.evidence_id,
        )

        results.append(result)

    # ========================================
    # Metrics集計
    # ========================================

    total = len(results)

    # Recall@5は正解Chunkが存在する問題だけで測る。
    # 回答不能問題は除外する。
    retrieval_results = [
        result for result in results if result.retrieval_hit is not None
    ]

    if retrieval_results:
        recall_at_5 = sum(
            bool(result.retrieval_hit) for result in retrieval_results
        ) / len(retrieval_results)

        page_recall_at_5 = sum(
            bool(result.page_hit) for result in retrieval_results
        ) / len(retrieval_results)

    else:
        recall_at_5 = 0.0
        page_recall_at_5 = 0.0

    # Answer Accuracyは Answerable / Unanswerableを含めた全ケースで計算する。
    answer_accuracy = sum(result.answer_correct for result in results) / total

    # Source Match Rateも全ケースで計算する。
    source_match_rate = sum(result.source_hit for result in results) / total

    summary = {
        "total": total,
        "retrieval_cases": len(retrieval_results),
        "recall_at_5": recall_at_5,
        "page_recall_at_5": page_recall_at_5,
        "answer_accuracy": answer_accuracy,
        "source_match_rate": source_match_rate,
    }

    # ========================================
    # 評価結果保存
    # ========================================

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (RESULTS_DIR / "latest.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "results": [result.model_dump() for result in results],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================
    # Terminal表示
    # ========================================

    print("\n=== Evaluation Summary ===")

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    """
    CLIからEvaluatorを実行する。

    1件:
    python -m rag_evaluation.evaluator --limit 1

    3件
    python -m rag_evaluation.evaluator --limit 3

    全件
    python -m rag_evaluation.evaluator
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    evaluate(limit=args.limit)


if __name__ == "__main__":
    main()
