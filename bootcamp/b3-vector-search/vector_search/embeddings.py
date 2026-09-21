import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .models import Chunk

BASE_DIR = Path(__file__).resolve().parents[1]

CHUNKS_PATH = BASE_DIR / "cache" / "chunks.json"

EMBEDDINGS_PATH = BASE_DIR / "cache" / "embeddings.npy"

MODEL_NAME = "intfloat/multilingual-e5-small"


def load_chunks() -> list[Chunk]:
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    return [Chunk.model_validate(item) for item in raw]


def create_embeddings(chunks: list[Chunk]) -> np.ndarray:
    model = SentenceTransformer(MODEL_NAME)

    texts = [f"passage: {chunk.text}" for chunk in chunks]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return np.asarray(embeddings)


def main() -> None:
    chunks = load_chunks()

    embeddings = create_embeddings(chunks)

    np.save(EMBEDDINGS_PATH, embeddings)

    print("Embedding shape:", embeddings.shape)


if __name__ == "__main__":
    main()
