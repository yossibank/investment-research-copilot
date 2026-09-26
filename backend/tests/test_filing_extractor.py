import pytest
from research_copilot.extraction.filing_extractor import extract_filing


def test_empty_filing_text() -> None:
    """
    空の資料では Claude を呼ぶ前に ValueError になる。
    """

    with pytest.raises(
        ValueError,
        match="Filing text must not be empty",
    ):
        extract_filing("")
