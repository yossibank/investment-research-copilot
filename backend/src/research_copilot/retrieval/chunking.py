import json

from ..paths import CHUNKS_PATH, DATA_DIR, PAGES_PATH
from .models import (
    Chunk,
    DocumentMetadata,
    PageText,
)

METADATA_PATH = DATA_DIR / "metadata.json"


def chunk_text(
    text: str,
    max_chars: int = 800,
    overlap: int = 120,
) -> list[str]:
    """
    テキストを max_chars 文字ずつに分割する。

    分割の境目で文が切れても前後のチャンクで拾えるように、
    隣り合うチャンクを overlap 文字だけ重ねる。
    """

    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")

    if overlap < 0:
        raise ValueError("overlap must not be negative.")

    # overlap が max_chars 以上だと start が前に進まず、無限ループになる。
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars.")

    chunks: list[str] = []

    start = 0

    while start < len(text):
        end = min(
            start + max_chars,
            len(text),
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def build_chunks(
    pages: list[PageText],
    metadata: DocumentMetadata,
) -> list[Chunk]:
    """
    ページごとにチャンク分割し、出典の表示に必要なメタデータを付ける。
    """

    chunks: list[Chunk] = []

    for page in pages:
        page_chunks = chunk_text(page.text)

        for index, text in enumerate(page_chunks):
            # 評価データ（golden_mvp.jsonl）の evidence_id もこの形式で書いているので、
            # 形式を変えるときは評価データも直す必要がある。
            chunk_id = f"{metadata.company}-p{page.page}-c{index}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=text,
                    company=metadata.company,
                    period=metadata.period,
                    document_name=metadata.document_name,
                    page=page.page,
                    source_url=metadata.source_url,
                )
            )

    return chunks


def load_chunks() -> list[Chunk]:
    """
    main() で保存した chunks.json を読み込む。
    """

    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    return [Chunk.model_validate(item) for item in raw]


def main() -> None:
    """
    pages.json と metadata.json からチャンクを作り、chunks.json に保存する。

    実行: python -m research_copilot.retrieval.chunking
    """

    pages_raw = json.loads(PAGES_PATH.read_text(encoding="utf-8"))

    pages = [PageText.model_validate(item) for item in pages_raw]

    metadata = DocumentMetadata.model_validate_json(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    chunks = build_chunks(pages, metadata)

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)

    CHUNKS_PATH.write_text(
        json.dumps(
            [chunk.model_dump() for chunk in chunks],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Created {len(chunks)} chunks.")


if __name__ == "__main__":
    main()
