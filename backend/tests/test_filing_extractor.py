import pytest
from research_copilot.extraction.filing_extractor import extract_filing


def test_empty_filing_text() -> None:
    # pytest.raises()
    #
    # 「この中で指定した例外が発生するはず」というテスト。
    with pytest.raises(
        # ValueErrorが発生する
        ValueError,
        # エラーメッセージも一致するか
        match="Filing text must not be empty",
    ):
        # 空文字で実行する。
        extract_filing("")
