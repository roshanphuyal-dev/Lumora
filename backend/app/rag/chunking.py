"""Deterministic, section-aware text chunking for local retrieval."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_BOUNDARY_RE = re.compile(r"\n\s*\n|\n(?=\S)")


@dataclass(frozen=True)
class ChunkDraft:
    text: str
    content_hash: str


def chunk_text(
    text: str, *, target_chars: int = 3200, overlap_chars: int = 400
) -> list[ChunkDraft]:
    """Split text near paragraph/line boundaries with bounded character overlap."""
    if target_chars <= 0 or overlap_chars < 0 or overlap_chars >= target_chars:
        raise ValueError("Chunk target must be positive and overlap smaller than target.")
    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[ChunkDraft] = []
    start = 0
    while start < len(normalized):
        hard_end = min(start + target_chars, len(normalized))
        end = hard_end
        if hard_end < len(normalized):
            boundaries = [
                match.end() for match in _BOUNDARY_RE.finditer(normalized, start, hard_end)
            ]
            if boundaries:
                end = boundaries[-1]
        value = normalized[start:end].strip()
        if value:
            chunks.append(
                ChunkDraft(text=value, content_hash=hashlib.sha256(value.encode()).hexdigest())
            )
        if end == len(normalized):
            break
        start = max(start + 1, end - overlap_chars)
    return chunks
