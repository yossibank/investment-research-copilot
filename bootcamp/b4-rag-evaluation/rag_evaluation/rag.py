import json
import os
from pathlib import Path

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv
from vector_search.search import search

from .models import RagAnswer

REPO_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(REPO_ROOT / ".env")


def create_client() -> Anthropic:
    """
    Claude API Clientを生成する。
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    return Anthropic(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    )


def build_context(results) -> str:
    """
    Vector Searchの結果をClaudeへ渡すContext文字列へ変換する。
    下記の形式で結果を返す。

    [
        (Chunk, score),
        (Chunk, score),
        ...
    ]
    """

    sections: list[str] = []

    for rank, (chunk, score) in enumerate(results, start=1):
        section = (
            f"### CONTEXT {rank}\n"
            f"CHUNK_ID: {chunk.chunk_id}\n"
            f"COMPANY: {chunk.company}\n"
            f"DOCUMENT: {chunk.document_name}\n"
            f"PAGE: {chunk.page}\n"
            f"SCORE: {score:.4f}\n\n"
            f"{chunk.text}"
        )

        sections.append(section)

    return "\n\n".join(sections)


def answer_question(
    question: str,
    top_k: int = 5,
):
    """
    RAG Pipeline本体。

    処理の流れ:

    Question
        ↓
    B3 Vector Search
        ↓
    Top-K chunks
        ↓
    Claude
        ↓
    RagAnswer

    Claudeの回答だけでなく、Retrieval結果も返す。

    理由:
    Recall@5を別途評価するため。
    """

    if not question.strip():
        raise ValueError("Question must not be empty.")

    # ========================================
    # Retrieval
    # ========================================

    # Semantic Searchの実行
    results = search(question, top_k=top_k)

    # Top-Kの検索結果をContextへ変換する
    context = build_context(results)

    # Claude Modelを取得。
    model = os.getenv("ANTHROPIC_MODEL")

    if not model:
        raise RuntimeError("ANTHROPIC_MODEL is not set.")

    client = create_client()

    # ========================================
    # Generation
    # ========================================

    response = client.messages.parse(
        model=model,
        max_tokens=1024,
        system=(
            "You are an investment research "
            "assistant that answers questions "
            "about company filings. "
            # 一般知識ではなくRetrievalしたContextのみを使用する。
            "Use ONLY the supplied CONTEXT. "
            "Do not use external knowledge. "
            # Contextにない情報を推測させない。
            "Do not guess missing information. "
            # 答えられない場合は無駄に回答を作らない。
            "If the CONTEXT is insufficient, "
            "set is_answerable to false and "
            "answer that that information cannot "
            "be confirmed from the provided material. "
            # 回答不能なのに架空sourceを付けない。
            "When is_answerable is false, "
            "source_chunk_ids and source_pages "
            "must be empty. "
            # 金額や単位を勝手に変更しない
            "When answering, preserve numerical "
            "values and units from the source. "
            # 架空のChunk IDを作らせない。
            "source_chunk_ids must contain only "
            "exact CHUNK_ID values shown in CONTEXT. "
            # Page番号もContext内のものだけにする。
            "source_pages must contain only page "
            "numbers shown in CONTEXT. "
            # Research Copilotは投資判断を代行しない。
            "Do not provide investment advice, "
            "trade recommendations, or definitive "
            "stock-price predictions."
        ),
        messages=[
            {
                "role": "user",
                # 質問とRetrieval結果を渡す
                "content": (f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"),
            }
        ],
        # フォーマット指定。
        output_format=RagAnswer,
    )

    # ClaudeのOutputをRagAnswerとして取得する。
    answer = response.parsed_output

    if answer is None:
        raise RuntimeError("Claude returned no parsed output.")

    return answer, results


def main() -> None:
    """
    Terminalから1問だけRAGを試す
    """

    question = input("質問を入力してください: ")

    try:
        answer, results = answer_question(question)

    except anthropic.APITimeoutError:
        print("Claude API request timed out.")
        return

    except anthropic.RateLimitError:
        print("Claude API rate limit exceeded.")
        return

    except anthropic.APIConnectionError:
        print("Claude not connect to Claude API.")
        return

    except anthropic.APIStatusError as error:
        print("Claude API error:", error.status_code)
        return

    # ========================================
    # Retrieval結果を表示
    # ========================================

    print("\n=== Retrieved Chunks ===")

    for rank, (chunk, score) in enumerate(results, start=1):
        print(f"{rank}. {chunk.chunk_id} (page={chunk.page}, score={score:.4f})")

    # ========================================
    # Claudeの回答を表示
    # ========================================

    print("\n=== Answer ===")

    print(
        json.dumps(
            answer.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
