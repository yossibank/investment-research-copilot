import argparse

from ..retrieval.chunking import load_chunks


def main() -> None:
    """
    Golden Setの evidence_id を決めるための補助ツール。
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
