"""Link-resource text extraction: fetch a URL and strip it down to plain text.

Unlike the file parsers in this package (`Callable[[bytes], ParsedDocument]`,
dispatched via `app/parsers/registry.py`), a link resource has no uploaded
bytes to parse — fetching *is* the parse step, so this is async and takes a
URL directly rather than going through the registry.
"""

import logging
from html.parser import HTMLParser

import httpx

from app.parsers.base import ParsedDocument

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT_SECONDS = 20.0
_SKIP_TAGS = {"script", "style", "noscript"}
# httpx's default UA ("python-httpx/x.y") gets 403'd by sites with basic bot
# filtering (e.g. Wikipedia) -- a descriptive UA identifying this as a fetcher
# is both more honest and less likely to be blocked than spoofing a browser.
_USER_AGENT = "Lumora-DocumentFetcher/1.0 (+student resource ingestion)"


class _TextExtractor(HTMLParser):
    """Strips tags, keeping visible text (and `<title>`) — treats page content as
    data, never as instructions, per `.claude/rules/security.md`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        stripped = data.strip()
        if not stripped:
            return
        if self._in_title and self.title is None:
            self.title = stripped
        else:
            self._chunks.append(stripped)

    def text(self) -> str:
        return "\n".join(self._chunks)


async def parse_url(url: str) -> ParsedDocument:
    """Fetch `url` and extract its visible text content."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_FETCH_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    text = extractor.text()

    return ParsedDocument(text=text, sections=[], page_count=None, title=extractor.title)
