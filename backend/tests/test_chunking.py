import pytest

from app.rag.chunking import chunk_text


def test_chunk_text_prefers_boundaries_and_overlaps() -> None:
    text = "First paragraph.\n\nSecond paragraph is longer.\n\nThird paragraph."
    chunks = chunk_text(text, target_chars=40, overlap_chars=8)

    assert len(chunks) >= 2
    assert all(len(chunk.text) <= 40 for chunk in chunks)
    assert all(len(chunk.content_hash) == 64 for chunk in chunks)
    assert chunks == chunk_text(text, target_chars=40, overlap_chars=8)


def test_chunk_text_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_text("text", target_chars=100, overlap_chars=100)
