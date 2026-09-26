def build_context(results) -> str:
    """
    Vector Searchの結果をClaudeへ渡すContext文字列へ変換する。
    下記の形式で結果を返す。

    [
        (Chunk, score),
        (Chunk, score),
        ...
    ]
    """

    sections: list[str] = []

    for rank, (chunk, score) in enumerate(results, start=1):
        section = (
            f"### CONTEXT {rank}\n"
            f"CHUNK_ID: {chunk.chunk_id}\n"
            f"COMPANY: {chunk.company}\n"
            f"DOCUMENT: {chunk.document_name}\n"
            f"PAGE: {chunk.page}\n"
            f"SCORE: {score:.4f}\n\n"
            f"{chunk.text}"
        )

        sections.append(section)

    return "\n\n".join(sections)
