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
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")

    if overlap < 0:
        raise ValueError("overlap must not be negative.")

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
    chunks: list[Chunk] = []

    for page in pages:
        page_chunks = chunk_text(page.text)

        for index, text in enumerate(page_chunks):
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


def main() -> None:
    pages_raw = json.loads(PAGES_PATH.read_text(encoding="utf-8"))

    pages = [PageText.model_validate(item) for item in pages_raw]

    metadata = DocumentMetadata.model_validate_json(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    chunks = build_chunks(pages, metadata)

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

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
