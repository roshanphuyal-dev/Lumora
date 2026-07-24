"""PDF text extraction (pypdf) — see app/parsers/registry.py for dispatch."""

import io

from pypdf import PdfReader

from app.parsers.base import ParsedDocument, ParsedSection


def parse(file_bytes: bytes) -> ParsedDocument:
    """Extract per-page text and metadata from a PDF's raw bytes."""
    reader = PdfReader(io.BytesIO(file_bytes))

    sections = [
        ParsedSection(index=index, text=(page.extract_text() or "").strip())
        for index, page in enumerate(reader.pages, start=1)
    ]
    text = "\n\n".join(section.text for section in sections if section.text)
    title = reader.metadata.title if reader.metadata else None

    return ParsedDocument(text=text, sections=sections, page_count=len(reader.pages), title=title)
