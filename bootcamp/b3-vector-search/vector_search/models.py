from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    company: str
    period: str
    document_name: str
    source_url: str
    retrived_at: str


class PageText(BaseModel):
    page: int
    text: str


class Chunk(BaseModel):
    chunk_id: str
    text: str

    company: str
    period: str
    document_name: str

    page: int
    source_url: str
