"""
資料の中から文字列を含むチャンクを探す補助ツール。Claude API は呼ばない。
"""

import argparse

from ..retrieval.chunking import load_chunks


def main() -> None:
    """
    資料の中から文字列を含むチャンクを探す。評価データの evidence_id を決めるときに使う。

    実行: python -m research_copilot.evaluation.find_chunk 2,018,914
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("term", help="資料内の文字列（数値など）")
    args = parser.parse_args()

    hits = [chunk for chunk in load_chunks() if args.term in chunk.text]

    if not hits:
        print("見つかりませんでした（全角・空白の違いに注意）")

    for chunk in hits:
        index = chunk.text.index(args.term)
        snippet = chunk.text[max(index - 40, 0) : index + 40].replace("\n", " ")
        print(f"{chunk.chunk_id}  (page {chunk.page})\n    …{snippet}…")


if __name__ == "__main__":
    main()
