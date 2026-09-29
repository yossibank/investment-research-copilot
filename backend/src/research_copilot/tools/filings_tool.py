"""
検索できる資料の一覧を返す読み取り専用ツール。Claude API は呼ばない。
"""

from pydantic import BaseModel, ConfigDict

from ..paths import METADATA_PATH
from ..retrieval.models import DocumentMetadata


class ListFilingsInput(BaseModel):
    """
    資料一覧ツールの入力。引数は取らない。
    """

    model_config = ConfigDict(extra="forbid")


class ListFilingsResult(BaseModel):
    """
    検索できる資料（会社・期間・資料名）の一覧。
    """

    filings: list[DocumentMetadata]


def list_available_filings(tool_input: ListFilingsInput) -> ListFilingsResult:
    """
    data/metadata.json から、検索できる資料の一覧を返す。
    """

    metadata = DocumentMetadata.model_validate_json(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    return ListFilingsResult(filings=[metadata])
