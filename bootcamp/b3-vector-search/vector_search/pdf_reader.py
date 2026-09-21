import json
from pathlib import Path

from pypdf import PdfReader

from .models import PageText

BASE_DIR = Path(__file__).resolve().parents[1]

PDF_PATH = BASE_DIR / "data" / "raw" / "filing.pdf"

OUTPUT_PATH = BASE_DIR / "data" / "parsed" / "pages.json"


def extract_pages(pdf_path: Path) -> list[PageText]:
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
    pages = extract_pages(PDF_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
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
