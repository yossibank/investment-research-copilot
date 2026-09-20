import pytest
from structured_extraction.filing_extractor import extract_filing


def test_empty_filing_text() -> None:
    with pytest.raises(
        ValueError,
        match="Filing text must not be empty",
    ):
        extract_filing("")
