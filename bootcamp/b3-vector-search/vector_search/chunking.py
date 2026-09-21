import json
from pathlib import Path

from .models import (
    Chunk,
    DocumentMetadata,
    PageText,
)

BASE_DIR = Path(__file__).resolve().parents[1]

PAGES_PATH = BASE_DIR / "data" / "parsed" / "pages.json"

METADATA_PATH = BASE_DIR / "data" / "metadata.json"

CACHE_PATH = BASE_DIR / "cache" / "chunks.json"


def chunk_text(
    text: str,
    max_chars: int = 800,
    overlap: int = 120,
) -> list[str]:
    # ======================================================
    # 引数チェック
    # ======================================================

    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")

    if overlap < 0:
        raise ValueError("overlap must not be negative.")

    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars.")

    # 分割した文字列を保存する空リスト。
    chunks: list[str] = []

    # 最初は文字列の先頭位置0から。
    start = 0

    while start < len(text):
        # ----------------------------------------------
        # 今回のChunkの終了位置を決める
        # ----------------------------------------------

        # 文章末尾を超えないようにmin()で小さい方を選ぶ。
        end = min(
            start + max_chars,
            len(text),
        )

        # ----------------------------------------------
        # 文章を切り出す
        # ----------------------------------------------

        # text[start:end]
        #
        # sliceでstart文字目からendの直前まで取得する。
        chunk = text[start:end].strip()

        # 空でなければ保存。
        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        # ----------------------------------------------
        # 次のChunkの開始位置
        # ----------------------------------------------

        # startの位置を end - overlap で文字を重複させる。
        start = end - overlap

    return chunks


def build_chunks(
    pages: list[PageText],
    metadata: DocumentMetadata,
) -> list[Chunk]:
    # 完成したChunkを保存するリスト。
    chunks: list[Chunk] = []

    # ======================================================
    # PDFを1ページずつ処理
    # ======================================================

    for page in pages:
        # そのページの本文をChunkingする。
        page_chunks = chunk_text(page.text)

        # ==================================================
        # 1ページ内のChunkを1個ずつ処理
        # ==================================================

        for index, text in enumerate(page_chunks):
            # Chunk固有IDを作る。
            #
            # 例: パナソニック...-p7-c0
            chunk_id = f"{metadata.company}-p{page.page}-c{index}"

            # ==================================================
            # Chunkモデルを作る
            # ==================================================

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


def main() -> None:
    # ======================================================
    # pages.jsonを読み込む
    # ======================================================

    # read_text()
    #
    # → JSONファイルを文字列として取得。
    #
    # json.loads()
    #
    # → JSON文字列をlist/dictへ変換する。
    pages_raw = json.loads(PAGES_PATH.read_text(encoding="utf-8"))

    # ======================================================
    # dict → PageText
    # ======================================================

    # pages_raw
    #
    # [
    #   {"page": 1, "text": "..."},
    #   ...
    # ]
    #
    # model_validate()でPageTextオブジェクトへ変換する。
    pages = [PageText.model_validate(item) for item in pages_raw]

    # ======================================================
    # metadata.json → DocumentMetadata
    # ======================================================

    # model_validate_json
    #
    # → JSON文字列を直接Pydanticモデルへ変換する。
    metadata = DocumentMetadata.model_validate_json(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    # ページ + metadata
    #
    # ↓
    #
    # Chunkのリストへ変換する。
    chunks = build_chunks(pages, metadata)

    # cache/フォルダがなければ作成する。
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # Chunk → JSON保存
    # ======================================================

    CACHE_PATH.write_text(
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
