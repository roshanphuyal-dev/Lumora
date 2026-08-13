"""arXiv API client (ADR 0013, `docs/adr/0013-paper-search-integration.md`).

The only place arXiv's API is called (.claude/rules/ai.md) -- nothing outside `ai/` should
call it directly. Used as the orchestrator's primary provider for `TaskType.PAPER_SEARCH`
(`ai/orchestrator/orchestrator.py`), with Semantic Scholar
(`ai/paper_search/semantic_scholar_client.py`) as an optional fallback.

Fully keyless -- GET `export.arxiv.org/api/query` with `search_query`/`max_results` params,
Atom 1.0 XML response (title, authors, summary/abstract, published date, abstract-page
link, PDF link, optional `arxiv:journal_ref`). Enforces arXiv's documented 1-request-per-
3-seconds, single-connection rate limit via a module-level `asyncio.Lock` + last-call
timestamp -- process-wide, since the limit is a property of the remote endpoint, not of
any one `ArxivClient` instance.

Empty-result handling (ADR 0013): a well-formed response with zero `<entry>` elements is a
*successful* `PaperSearchResult` with `results=()`, never an `ArxivError` -- this mirrors
`_run_internet_search`'s documented empty-result semantics exactly (no special-casing an
empty-but-successful result; only a raised provider error triggers the Semantic Scholar
fallback in `ai/orchestrator/orchestrator.py:_run_paper_search`).

Never logs/interpolates raw query text -- it's a GET param, same leak risk as Brave's
(`ai/internet_search/brave_client.py`'s `_describe_http_status_error` pattern, reused here
verbatim): every exception is reduced to its class name (plus, for an HTTP status error,
only the status code and any `Retry-After` header) before being folded into `ArxivError`.
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime

import httpx

from ai.paper_search.schemas import (
    PaperSearchItem,
    PaperSearchProvider,
    PaperSearchResult,
    normalize_query,
)

_API_URL = "https://export.arxiv.org/api/query"
_TIMEOUT_SECONDS = 30.0
_MIN_REQUEST_INTERVAL_SECONDS = 3.0  # arXiv's documented 1 req/3s, single connection.

_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"
_NS = {"atom": _ATOM_NS, "arxiv": _ARXIV_NS}

_rate_limit_lock = asyncio.Lock()
_last_request_monotonic: float | None = None


class ArxivError(RuntimeError):
    """Raised when the arXiv API call fails or returns an unparseable response."""


class ArxivClient:
    """Thin wrapper around the arXiv `export.arxiv.org/api/query` Atom API. Keyless."""

    async def search(self, query: str, *, max_results: int = 5) -> PaperSearchResult:
        """Search arXiv and normalize the Atom response into grounding results.

        An empty-but-well-formed response (zero papers found) is a *successful* result
        with `results=()`, not an `ArxivError` -- see this module's docstring.
        """
        payload = await _fetch(query, max_results=max_results)

        try:
            items = _extract_items(payload)
        except ET.ParseError as exc:
            raise ArxivError(
                f"arXiv returned an unparseable response: {exc.__class__.__name__}"
            ) from exc

        return PaperSearchResult(
            query=query,
            normalized_query=normalize_query(query),
            provider=PaperSearchProvider.ARXIV,
            results=tuple(items),
            fetched_at=datetime.now(UTC),
        )


async def _fetch(query: str, *, max_results: int) -> str:
    """Issue the arXiv HTTP request, holding `_rate_limit_lock` across both the throttle
    wait AND the request itself.

    arXiv's documented limit isn't just "no more than 1 request per 3 seconds" -- it's also
    "one connection at a time." Releasing the lock as soon as the throttle wait ends (before
    the HTTP call starts) would satisfy the interval but not the single-connection rule: a
    slow request taking longer than 3 seconds would let a second call's HTTP request begin
    while the first is still in flight. Holding the lock for the full duration -- including
    recording `_last_request_monotonic` only once we're already inside it, right before
    issuing the request -- guarantees only one arXiv HTTP call is ever in flight process-
    wide (ADR 0013).
    """
    global _last_request_monotonic
    async with _rate_limit_lock:
        now = time.monotonic()
        if _last_request_monotonic is not None:
            wait = _MIN_REQUEST_INTERVAL_SECONDS - (now - _last_request_monotonic)
            if wait > 0:
                await asyncio.sleep(wait)
        _last_request_monotonic = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS, follow_redirects=True
            ) as http_client:
                response = await http_client.get(
                    _API_URL,
                    params={"search_query": f"all:{query}", "max_results": max_results},
                )
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as exc:
            raise ArxivError(f"arXiv search failed: {_describe_http_status_error(exc)}") from exc
        except Exception as exc:  # normalize every other failure to ArxivError;
            # never interpolate `exc`: transport/decoding errors may embed the request URL,
            # which carries `query` as a GET param (ADR 0013).
            raise ArxivError(f"arXiv search failed: {exc.__class__.__name__}") from exc


def _extract_items(payload: str) -> list[PaperSearchItem]:
    root = ET.fromstring(payload)
    items: list[PaperSearchItem] = []
    for entry in root.findall("atom:entry", _NS):
        title = _text(entry, "atom:title")
        url = _entry_url(entry)
        if not title or not url:
            continue
        items.append(
            PaperSearchItem(
                title=_collapse_whitespace(title),
                authors=_authors(entry),
                abstract=_collapse_whitespace(_text(entry, "atom:summary")) or None,
                publication_date=_parse_date(_text(entry, "atom:published")),
                url=url,
                pdf_url=_pdf_url(entry),
                venue=_text(entry, "arxiv:journal_ref"),
                citation_count=None,  # arXiv's API never provides this (ADR 0013).
            )
        )
    return items


def _text(entry: ET.Element, path: str) -> str | None:
    element = entry.find(path, _NS)
    if element is None or element.text is None:
        return None
    return element.text.strip() or None


def _collapse_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())


def _authors(entry: ET.Element) -> tuple[str, ...]:
    names = []
    for author in entry.findall("atom:author", _NS):
        name = author.find("atom:name", _NS)
        if name is not None and name.text and name.text.strip():
            names.append(name.text.strip())
    return tuple(names)


def _entry_url(entry: ET.Element) -> str | None:
    """The abstract-page URL -- prefers the `rel="alternate"` HTML link (or the default,
    unspecified-`rel` link, which the Atom spec treats as `alternate`), falling back to
    `<id>` (also the abs-page URL for an arXiv entry) if no such link is present."""
    for link in entry.findall("atom:link", _NS):
        rel = link.get("rel", "alternate")
        if rel == "alternate":
            href = link.get("href")
            if href:
                return href
    return _text(entry, "atom:id")


def _pdf_url(entry: ET.Element) -> str | None:
    for link in entry.findall("atom:link", _NS):
        if link.get("rel") == "related" and link.get("type") == "application/pdf":
            return link.get("href")
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _describe_http_status_error(exc: httpx.HTTPStatusError) -> str:
    """Return only safe, operationally useful HTTP metadata."""
    status_code = exc.response.status_code
    retry_after = exc.response.headers.get("Retry-After")
    if retry_after and retry_after.isascii() and retry_after.isdigit():
        return f"HTTP {status_code} (Retry-After: {retry_after})"
    return f"HTTP {status_code}"
