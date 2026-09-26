from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    """
    決算資料 1 件の情報。data/metadata.json から読む。
    """

    company: str
    period: str
    document_name: str
    source_url: str
    retrieved_at: str


class PageText(BaseModel):
    """
    PDF の 1 ページ分のテキスト。
    """

    page: int
    text: str


class Chunk(BaseModel):
    """
    検索の単位。本文と、出典の表示に使うメタデータを持つ。
    """

    chunk_id: str
    text: str

    company: str
    period: str
    document_name: str

    page: int
    source_url: str
