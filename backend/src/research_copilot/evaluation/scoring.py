"""
1 問ずつの採点。Claude API は呼ばないので、テストから直接使える。
"""

import unicodedata

from ..agent.models import CopilotRun
from .models import EvalResult, GoldenCase


def normalize_text(text: str) -> str:
    """
    回答を比較しやすくするため、表記揺れをある程度吸収する。

    例:
        売上高 1,100 億円
            ↓
        売上高 1100 億円
    """

    # NFKC で全角・半角などをある程度統一する。
    text = unicodedata.normalize("NFKC", text)

    return text.lower().replace(" ", "").replace("\n", "").replace(",", "")



def contains_required_terms(
    answer: str,
    required_terms: list[str],
) -> bool:
    """
    Claude の回答に、Golden Set で指定した情報が全て含まれているか確認する。
    """

    normalized_answer = normalize_text(answer)

    return all(normalize_text(term) in normalized_answer for term in required_terms)



def score_case(case: GoldenCase, run: CopilotRun) -> EvalResult:
    """
    Copilot の実行結果（CopilotRun）を GoldenCase と照合して採点する。

    出典は「Claude が返した ID」ではなく、
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
        # 回答不能ケースは正解 Chunk がないので検索の評価対象外。
        retrieval_hit = None
        page_hit = None

        answer_correct = not answer.is_answerable

        # 答えられないのに出典を付けていないか。
        source_hit = len(source_ids) == 0

    # ツール選択:
    #   expected_tool あり → そのツールを使った
    #   expected_tool なし → ツールを 1 つも使っていない
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
    API エラーなどで実行できなかったケース。全指標を失敗として数える。
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
