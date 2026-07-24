"""Image OCR (pytesseract + Pillow) — see app/parsers/registry.py for dispatch.

Requires the `tesseract-ocr` system binary to be installed wherever this runs
(pytesseract is a thin wrapper around the CLI, not a pure-Python OCR engine)
— see the deployment image / devops setup for the package install.
"""

import io

import pytesseract
from PIL import Image

from app.parsers.base import ParsedDocument, ParsedSection


def parse(file_bytes: bytes) -> ParsedDocument:
    """Run OCR over an image's raw bytes and return the recognized text."""
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image).strip()
    sections = [ParsedSection(index=1, text=text)] if text else []

    return ParsedDocument(text=text, sections=sections, page_count=1, title=None)
