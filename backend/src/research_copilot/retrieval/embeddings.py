"""
埋め込み（文章 → ベクトル）に関する処理をまとめたモジュール。

E5 系のモデルは、検索される側の文に "passage: "、検索する側の文に "query: " を付ける前提。
どちらも同じモデルでベクトルにし、長さを 1 に正規化しておくと、検索時の内積がそのままコサイン類似度になる。
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from ..paths import EMBEDDINGS_PATH
from .chunking import load_chunks
from .models import Chunk

MODEL_NAME = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    埋め込みモデルを初回だけ読み込み、2 回目以降は同じものを使い回す。

    読み込みに数秒かかるため（評価の warmup で約 8 秒）、質問のたびには読み込まない。
    """

    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str], show_progress_bar: bool = False) -> np.ndarray:
    """
    検索される側の文章をベクトルにする。戻り値の形は (件数, 384)。
    """

    embeddings = get_embedding_model().encode(
        [f"passage: {text}" for text in texts],
        normalize_embeddings=True,
        show_progress_bar=show_progress_bar,
    )

    return np.asarray(embeddings)


def embed_query(query: str) -> np.ndarray:
    """
    検索する側の質問をベクトルにする。戻り値の形は (384,)。
    """

    embeddings = get_embedding_model().encode(
        [f"query: {query}"],
        normalize_embeddings=True,
    )

    return np.asarray(embeddings)[0]


def create_embeddings(chunks: list[Chunk]) -> np.ndarray:
    """
    全チャンクを埋め込みベクトルに変換する。戻り値の形は (チャンク数, 384)。
    """

    return embed_passages([chunk.text for chunk in chunks], show_progress_bar=True)


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
