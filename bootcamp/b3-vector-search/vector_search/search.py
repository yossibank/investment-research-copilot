import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .embeddings import MODEL_NAME
from .models import Chunk

BASE_DIR = Path(__file__).resolve().parents[1]

CHUNKS_PATH = BASE_DIR / "cache" / "chunks.json"

EMBEDDINGS_PATH = BASE_DIR / "cache" / "embeddings.npy"


def load_chunks() -> list[Chunk]:
    # JSON
    #
    # ↓
    #
    # Python list/dict
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    # dict
    #
    # ↓
    #
    # Chunk
    return [Chunk.model_validate(item) for item in raw]


def search(
    query: str,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """
    質問をEmbedding化し、全Chunkとの意味的類似度を計算して、上位top_k件を返す。

    戻り値:

    [
        (Chunk, score),
        (Chunk, score),
        ...
    ]
    """

    # 空の質問を禁止する。
    if not query.strip():
        raise ValueError("Query must not be empty.")

    # Chunkを読み込む。
    chunks = load_chunks()

    # あらかじめ計算して保存しておいた全Chunkのベクトルをロードする。
    embeddings = np.load(EMBEDDINGS_PATH)

    # Chunk数とEmbedding数が一致を前提とする。
    if len(chunks) != len(embeddings):
        raise RuntimeError("Chunk count and embedding count do not match.")

    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode(
        # E5系モデルでは
        # 検索質問には
        #
        # query:
        #
        # を付ける。
        [f"query: {query}"],
        # 正規化する。
        normalize_embeddings=True,
        # リストとして1件のみ渡すので[0]で1件目を取り出す。
    )[0]

    # embedding → 「文章を数字の並びにしたもの」384個の数字に変換される。
    #
    # これらを比較して「数字の並びの似方」を使って計測する。
    #
    # @ は行列積
    #
    # 質問 [0.9, 0.2, 0.1]
    # Chunk A [0.8, 0.2, 0.1]
    #
    # 0.9 * 0.8 + 0.2 * 0.2 + 0.1 * 0.1 → 類似度スコアを算出。
    scores = embeddings @ query_embedding

    # argsort
    #
    # → 「小さい順にならべたときのindex」を返す。
    #
    # [::-1]
    #
    # → sliceで逆順にする。
    #
    # [:top_k]
    #
    # sliceでtop_k件を取得する。
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
    # ======================================================
    # ユーザーから質問を入力
    # ======================================================

    query = input("質問を入力してください: ")

    # ======================================================
    # Vector Search
    # ======================================================

    # Top-5を検索。
    results = search(query, top_k=5)

    print("\n===Search Results ===")

    # ======================================================
    # 検索結果を順位付きで表示
    # ======================================================

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
