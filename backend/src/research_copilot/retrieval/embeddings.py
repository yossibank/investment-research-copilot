import numpy as np
from sentence_transformers import SentenceTransformer

from ..paths import EMBEDDINGS_PATH
from .chunking import load_chunks
from .models import Chunk

MODEL_NAME = "intfloat/multilingual-e5-small"


def create_embeddings(chunks: list[Chunk]) -> np.ndarray:
    """
    全チャンクを埋め込みベクトルに変換する。戻り値の形は (チャンク数, 384)。
    """

    model = SentenceTransformer(MODEL_NAME)

    # E5 系のモデルは、検索される側の文に "passage: "、
    # 検索する側の文に "query: " を付ける前提。
    texts = [f"passage: {chunk.text}" for chunk in chunks]

    embeddings = model.encode(
        texts,
        # 長さを 1 に正規化しておくと、検索時の内積がそのままコサイン類似度になる。
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return np.asarray(embeddings)


def main() -> None:
    """
    chunks.json の全チャンクを埋め込みベクトルにして、embeddings.npy に保存する。

    実行: python -m research_copilot.retrieval.embeddings
    """

    chunks = load_chunks()

    embeddings = create_embeddings(chunks)

    np.save(EMBEDDINGS_PATH, embeddings)

    print("Embedding shape:", embeddings.shape)


if __name__ == "__main__":
    main()
