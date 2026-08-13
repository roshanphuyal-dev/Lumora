"""Semantic Scholar Academic Graph API client (ADR 0013,
`docs/adr/0013-paper-search-integration.md`).

The only place Semantic Scholar's API is called (.claude/rules/ai.md) -- nothing outside
`ai/` should call it directly. Used as the orchestrator's optional fallback for
`TaskType.PAPER_SEARCH` (`ai/orchestrator/orchestrator.py`) -- only attempted when arXiv
fails *and* `SEMANTIC_SCHOLAR_API_KEY` is configured, same "gated fallback, never a silent
attempt" precedent as `ai/internet_search/brave_client.py` (ADR 0012).

Unlike Tavily/Brave, an API key is *optional* rather than required at the HTTP level --
Semantic Scholar's Academic Graph API accepts unauthenticated requests against a shared
rate-limit pool (ADR 0013's provider comparison); a dedicated key just raises the ceiling
to an individually-reserved 1 req/sec via the `x-api-key` header. So this client never
refuses to construct or search over a missing key -- whether Semantic Scholar is attempted
*at all* is the orchestrator's call (gated on the env var being set), not this client's.

Enforces a 1-request-per-second rate limit via the same module-level lock + last-call-
timestamp pattern as `ai/paper_search/arxiv_client.py`, plus exponential backoff (honoring
`Retry-After` when present) on HTTP 429.

Never logs/interpolates raw query text -- it's a GET param, same leak risk as Brave's
(`ai/internet_search/brave_client.py`'s sanitization pattern, reused here verbatim).
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime

import httpx

from ai.paper_search.schemas import (
    PaperSearchItem,
    PaperSearchProvider,
    PaperSearchResult,
    normalize_query,
)

_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_TIMEOUT_SECONDS = 30.0
_MIN_REQUEST_INTERVAL_SECONDS = 1.0  # Semantic Scholar's documented keyed limit, 1 req/sec.
_FIELDS = "title,authors,abstract,publicationDate,venue,citationCount,url,openAccessPdf"
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 1.0

_rate_limit_lock = asyncio.Lock()
_last_request_monotonic: float | None = None


class SemanticScholarError(RuntimeError):
    """Raised when the Semantic Scholar API call fails or returns an unparseable response."""


class SemanticScholarClient:
    """Thin wrapper around the Semantic Scholar Academic Graph paper-search endpoint."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    async def search(self, query: str, *, max_results: int = 5) -> PaperSearchResult:
        """Search Semantic Scholar and normalize the response into grounding results.

        An empty-but-successful response (zero papers found) is a *successful* result
        with `results=()`, not a `SemanticScholarError` -- same empty-result semantics as
        `ai/paper_search/arxiv_client.py:ArxivClient.search` (ADR 0013).
        """
        headers = {"x-api-key": self._api_key} if self._api_key else {}
        payload = await self._search_with_retries(
            query=query, max_results=max_results, headers=headers
        )
        items = _extract_items(payload)
        return PaperSearchResult(
            query=query,
            normalized_query=normalize_query(query),
            provider=PaperSearchProvider.SEMANTIC_SCHOLAR,
            results=tuple(items),
            fetched_at=datetime.now(UTC),
        )

    async def _search_with_retries(
        self, *, query: str, max_results: int, headers: dict[str, str]
    ) -> dict:
        attempt = 0
        while True:
            await _throttle()
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                    response = await http_client.get(
                        _API_URL,
                        headers=headers,
                        params={"query": query, "limit": max_results, "fields": _FIELDS},
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < _MAX_RETRIES:
                    await asyncio.sleep(_backoff_seconds(exc.response, attempt))
                    attempt += 1
                    continue
                raise SemanticScholarError(
                    f"Semantic Scholar search failed: {_describe_http_status_error(exc)}"
                ) from exc
            except Exception as exc:  # normalize every other failure to SemanticScholarError;
                # never interpolate `exc`: transport/decoding errors may embed the request
                # URL, which carries `query` as a GET param (ADR 0013).
                raise SemanticScholarError(
                    f"Semantic Scholar search failed: {exc.__class__.__name__}"
                ) from exc


async def _throttle() -> None:
    """Same lock + last-call-timestamp pattern as
    `ai/paper_search/arxiv_client.py:_throttle`, a separate process-wide limiter (a
    different interval applies to this provider, ADR 0013)."""
    global _last_request_monotonic
    async with _rate_limit_lock:
        now = time.monotonic()
        if _last_request_monotonic is not None:
            wait = _MIN_REQUEST_INTERVAL_SECONDS - (now - _last_request_monotonic)
            if wait > 0:
                await asyncio.sleep(wait)
        _last_request_monotonic = time.monotonic()


def _backoff_seconds(response: httpx.Response, attempt: int) -> float:
    """Honor `Retry-After` when present, in whichever of its two HTTP-permitted forms the
    server used (RFC 9110 10.2.3), otherwise fall back to exponential backoff
    (1s, 2s, 4s, ...).
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        delay = _parse_retry_after(retry_after)
        if delay is not None:
            return delay
    return _BASE_BACKOFF_SECONDS * (2**attempt)


def _parse_retry_after(value: str) -> float | None:
    """Parse a `Retry-After` header value in either permitted form:

    - delay-seconds -- a plain non-negative integer (e.g. `"30"`).
    - HTTP-date -- e.g. `"Wed, 21 Oct 2026 07:28:00 GMT"` -- the remaining time until that
      timestamp, clamped to 0 if it's already in the past.

    Returns `None` if `value` matches neither form, so the caller falls back to exponential
    backoff rather than retrying earlier than the server actually instructed.
    """
    stripped = value.strip()
    if stripped.isascii() and stripped.isdigit():
        return float(stripped)

    try:
        retry_at = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max((retry_at - datetime.now(UTC)).total_seconds(), 0.0)


def _extract_items(payload: dict) -> list[PaperSearchItem]:
    raw_items = payload.get("data")
    if not isinstance(raw_items, list):
        return []
    items: list[PaperSearchItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title")
        url = entry.get("url")
        if not isinstance(title, str) or not isinstance(url, str):
            continue
        abstract = entry.get("abstract")
        venue = entry.get("venue")
        citation_count = entry.get("citationCount")
        items.append(
            PaperSearchItem(
                title=title,
                authors=_authors(entry.get("authors")),
                abstract=abstract if isinstance(abstract, str) and abstract else None,
                publication_date=_parse_date(entry.get("publicationDate")),
                url=url,
                pdf_url=_pdf_url(entry.get("openAccessPdf")),
                venue=venue if isinstance(venue, str) and venue else None,
                citation_count=citation_count if isinstance(citation_count, int) else None,
            )
        )
    return items


def _authors(raw_authors: object) -> tuple[str, ...]:
    if not isinstance(raw_authors, list):
        return ()
    names = []
    for author in raw_authors:
        if isinstance(author, dict):
            name = author.get("name")
            if isinstance(name, str) and name:
                names.append(name)
    return tuple(names)


def _pdf_url(raw_open_access_pdf: object) -> str | None:
    if not isinstance(raw_open_access_pdf, dict):
        return None
    url = raw_open_access_pdf.get("url")
    return url if isinstance(url, str) and url else None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _describe_http_status_error(exc: httpx.HTTPStatusError) -> str:
    """Return only safe, operationally useful HTTP metadata."""
    status_code = exc.response.status_code
    retry_after = exc.response.headers.get("Retry-After")
    if retry_after and retry_after.isascii() and retry_after.isdigit():
        return f"HTTP {status_code} (Retry-After: {retry_after})"
    return f"HTTP {status_code}"
