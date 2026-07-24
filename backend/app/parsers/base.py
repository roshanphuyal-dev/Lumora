"""Shared result types for document parsers (see app/parsers/registry.py)."""

from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    """One natural unit of a parsed document (a PDF page, a PPTX slide, ...).

    `index` is 1-based to match how humans refer to pages/slides.
    """

    index: int
    text: str


@dataclass
class ParsedDocument:
    """Structured result of parsing a document's raw bytes into text.

    `text` is the full plain-text concatenation (what gets stored in
    `Document.extracted_text`); `sections` preserves natural structure
    (pages/slides) where the format has one, for callers that want it later
    (e.g. citing a page number). Formats without page boundaries (DOCX, images)
    return a single section rather than a fabricated one.
    """

    text: str
    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int | None = None
    title: str | None = None
