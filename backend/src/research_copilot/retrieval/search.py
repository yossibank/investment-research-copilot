import numpy as np

from ..paths import EMBEDDINGS_PATH
from .chunking import load_chunks
from .embeddings import embed_query
from .models import Chunk


def search(
    query: str,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """
    質問と意味が近いチャンクを、類似度が高い順に top_k 件返す。
    """

    if not query.strip():
        raise ValueError("Query must not be empty.")

    chunks = load_chunks()

    embeddings = np.load(EMBEDDINGS_PATH)

    # chunks.json と embeddings.npy は同じ順番で保存されている前提。
    # 件数がずれていたら、chunking を作り直した後に embeddings を作り直していない。
    if len(chunks) != len(embeddings):
        raise RuntimeError("Chunk count and embedding count do not match.")

    query_embedding = embed_query(query)

    # どちらも正規化済みなので、内積がそのままコサイン類似度になる。
    # 形は (チャンク数, 384) @ (384,) → (チャンク数,)。
    scores = embeddings @ query_embedding

    top_indices = np.argsort(scores)[::-1][:top_k]

    results: list[tuple[Chunk, float]] = []

    for index in top_indices:
        results.append(
            (
                chunks[int(index)],
                float(scores[index]),
            )
        )

    return results


def main() -> None:
    """
    ターミナルで質問を入力し、検索結果の上位 5 件を表示する。Claude は呼ばない。

    実行: python -m research_copilot.retrieval.search
    """

    query = input("質問を入力してください: ")

    results = search(query, top_k=5)

    print("\n===Search Results ===")

    for rank, (chunk, score) in enumerate(results, start=1):
        print(f"\n--- Rank {rank} ---")

        print(f"Score: {score:.4f}")

        print(f"Company: {chunk.company}")

        print(f"Document: {chunk.document_name}")

        print(f"Page: {chunk.page}")

        print(f"Chunk ID: {chunk.chunk_id}")

        print(chunk.text[:500])


if __name__ == "__main__":
    main()
