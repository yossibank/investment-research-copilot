"""
決算 PDF からページごとのテキストを取り出し、pages.json に保存する。
"""

import json
from pathlib import Path

from pypdf import PdfReader

from ..paths import DATA_DIR, PAGES_PATH
from .models import PageText

PDF_PATH = DATA_DIR / "raw" / "filing.pdf"


def extract_pages(pdf_path: Path) -> list[PageText]:
    """
    PDF からページごとのテキストを取り出す。

    ページ番号は PDF の 1 ページ目を 1 とする（出典として表示するページと合わせるため）。
    文字を取り出せないページ（画像だけのページなど）は飛ばす。
    """

    reader = PdfReader(pdf_path)

    pages: list[PageText] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()

        if not text:
            continue

        pages.append(
            PageText(
                page=page_number,
                text=text,
            )
        )

    return pages


def main() -> None:
    """
    data/raw/filing.pdf からページごとのテキストを取り出し、pages.json に保存する。

    実行: python -m research_copilot.retrieval.pdf_reader
    """

    pages = extract_pages(PDF_PATH)

    PAGES_PATH.parent.mkdir(parents=True, exist_ok=True)

    PAGES_PATH.write_text(
        json.dumps(
            [page.model_dump() for page in pages],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Extracted {len(pages)} pages.")


if __name__ == "__main__":
    main()
