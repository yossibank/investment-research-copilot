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
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    return [Chunk.model_validate(item) for item in raw]


def search(
    query: str,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    if not query.strip():
        raise ValueError("Query must not be empty.")

    chunks = load_chunks()

    embeddings = np.load(EMBEDDINGS_PATH)

    if len(chunks) != len(embeddings):
        raise RuntimeError("Chunk count and embedding count do not match.")

    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode(
        [f"query: {query}"],
        normalize_embeddings=True,
    )[0]

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
