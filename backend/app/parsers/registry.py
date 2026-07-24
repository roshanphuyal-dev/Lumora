"""Dispatch a Document to the parser for its file type.

Looked up by mime_type first (the more precise/standard signal), falling back
to file_type (extension-style) for cases where mime_type is missing or generic.
"""

from collections.abc import Callable

from app.parsers import docx_parser, image_parser, pdf_parser, pptx_parser
from app.parsers.base import ParsedDocument

Parser = Callable[[bytes], ParsedDocument]


class UnsupportedFileTypeError(ValueError):
    """Raised when no parser is registered for a document's mime_type/file_type."""


_MIME_TYPE_PARSERS: dict[str, Parser] = {
    "application/pdf": pdf_parser.parse,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
        pptx_parser.parse
    ),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": docx_parser.parse,
    "image/png": image_parser.parse,
    "image/jpeg": image_parser.parse,
    "image/webp": image_parser.parse,
    "image/tiff": image_parser.parse,
    "image/bmp": image_parser.parse,
}

_FILE_TYPE_PARSERS: dict[str, Parser] = {
    "pdf": pdf_parser.parse,
    "pptx": pptx_parser.parse,
    "docx": docx_parser.parse,
    "png": image_parser.parse,
    "jpg": image_parser.parse,
    "jpeg": image_parser.parse,
    "webp": image_parser.parse,
    "tiff": image_parser.parse,
    "bmp": image_parser.parse,
    "image": image_parser.parse,
}


def get_parser(mime_type: str, file_type: str) -> Parser:
    """Return the parser function for a document, or raise if none matches."""
    parser = _MIME_TYPE_PARSERS.get(mime_type.lower())
    if parser is not None:
        return parser

    parser = _FILE_TYPE_PARSERS.get(file_type.lower())
    if parser is not None:
        return parser

    raise UnsupportedFileTypeError(
        f"No parser registered for mime_type={mime_type!r}, file_type={file_type!r}"
    )
