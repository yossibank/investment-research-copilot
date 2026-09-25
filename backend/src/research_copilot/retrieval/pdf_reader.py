import json
from pathlib import Path

from pypdf import PdfReader

from ..paths import DATA_DIR
from .models import PageText

PDF_PATH = DATA_DIR / "raw" / "filing.pdf"

OUTPUT_PATH = DATA_DIR / "parsed" / "pages.json"


def extract_pages(pdf_path: Path) -> list[PageText]:
    # ======================================================
    # PDFを開く
    # ======================================================

    # PdfReader(...)でPDFファイルを読み込む。
    #
    # reader.pages
    #
    # PDF内の全ページへアクセスする。
    reader = PdfReader(pdf_path)

    # PageTextへ入れるための空リスト。
    pages: list[PageText] = []

    # ======================================================
    # 全ページを1ページずつ処理
    # ======================================================

    # enumerate()
    #
    # start=1でページ番号は0ではなく1から始まる。
    for page_number, page in enumerate(reader.pages, start=1):
        # PDFのページから文字を抽出する。
        text = page.extract_text() or ""
        # 文章前後の余分な余白や改行を削除する。
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
    # PDFから全ページを抽出
    pages = extract_pages(PDF_PATH)

    # ======================================================
    # 保存先フォルダを作る
    # ======================================================

    # OUTPUT_PATH:
    #
    # data/parsed/pages.json
    #
    # .parent:
    #
    # data/parsed/
    #
    # mkdir()でフォルダ作成
    #
    # parents = True
    # → 上位フォルダも必要なら作る。
    #
    # exist_ok = True
    # → すでに存在していてもエラーにしない
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # PageText → JSON
    # ======================================================

    OUTPUT_PATH.write_text(
        json.dumps(
            # リスト内包表記。
            #
            # model_dump()
            #
            # 各PageTextをdictへ変換する。
            [page.model_dump() for page in pages],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # len(pages)
    #
    # 抽出できたページ数を取得。
    print(f"Extracted {len(pages)} pages.")


if __name__ == "__main__":
    main()
