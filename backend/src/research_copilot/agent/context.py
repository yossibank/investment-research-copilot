from ..retrieval.models import Chunk


def build_context(results: list[tuple[Chunk, float]]) -> str:
    """
    検索結果を、Claude に渡す CONTEXT 文字列に変換する。

    各チャンクに CHUNK_ID を付けて渡し、回答の根拠として
    その ID を返させる（validate_sources で実際の検索結果と照合する）。
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
