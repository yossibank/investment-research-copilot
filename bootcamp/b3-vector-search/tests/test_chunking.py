import pytest
from vector_search.chunking import chunk_text


def test_chunk_text_short_text() -> None:
    result = chunk_text(
        "短い文章です。",
        max_chars=100,
        overlap=10,
    )

    assert result == ["短い文章です。"]


def test_chunk_text_long_text() -> None:
    text = "A" * 250

    result = chunk_text(
        text,
        max_chars=100,
        overlap=20,
    )

    assert len(result) > 1


def test_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text(
            "test",
            max_chars=100,
            overlap=100,
        )
