import numpy as np
from sentence_transformers import SentenceTransformer

from ..paths import EMBEDDINGS_PATH
from .chunking import load_chunks
from .models import Chunk

MODEL_NAME = "intfloat/multilingual-e5-small"


def create_embeddings(chunks: list[Chunk]) -> np.ndarray:
    # ======================================================
    # Embeddingモデル読み込み
    # ======================================================

    model = SentenceTransformer(MODEL_NAME)

    # ======================================================
    # Chunk文章を取り出す
    # ======================================================

    # リスト内包表記。
    #
    # 全Chunkから、
    #
    # "passage: 本文..."
    #
    # という文字列リストを作る。
    #
    # E5系モデルでは、
    # 検索対象文章には
    #
    # passage:
    #
    # を付ける。

    texts = [f"passage: {chunk.text}" for chunk in chunks]

    # ======================================================
    # 文章 → Embedding
    # ======================================================

    # 例:
    #   売上高は2,018,914百万円...
    #   ↓
    #   [0.023, -0.119, 0.481, ...]

    embeddings = model.encode(
        texts,
        # 全ベクトルの長さを1に正規化する。
        # あとで内積を使ってcosine similarity相当を計算できる。
        normalize_embeddings=True,
        # 処理進捗をターミナルに表示する。
        show_progress_bar=True,
    )

    return np.asarray(embeddings)


def main() -> None:
    # Chunkを読み込む。
    chunks = load_chunks()

    # 全ChunkをEmbeddingへ変換。
    embeddings = create_embeddings(chunks)

    # .npyはNumPy専用のバイナリ形式。
    # JSONより高速かつ、数値配列をそのまま保存しやすい。
    np.save(EMBEDDINGS_PATH, embeddings)

    # shape:
    #
    # 配列の形を表示する。
    #
    # 例:
    #   (30, 384)
    #   30 Chunk × 384次元
    print("Embedding shape:", embeddings.shape)


if __name__ == "__main__":
    main()
