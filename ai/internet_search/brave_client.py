"""Brave Search API client — LLM Context endpoint (ADR 0012,
`docs/adr/0012-internet-search-integration.md`).

The only place Brave's API is called (.claude/rules/ai.md) — nothing outside `ai/`
should call it directly. Used as the orchestrator's optional fallback for
`TaskType.INTERNET_SEARCH` (`ai/orchestrator/orchestrator.py`) — only attempted when Tavily
fails *and* `BRAVE_SEARCH_API_KEY` is configured; ADR 0012 explicitly rejects a silent
Brave attempt when it isn't configured.

Hits `/res/v1/llm/context` specifically (not `/res/v1/web/search`) — Brave's LLM Context
API, purpose-built for a caller-controlled LLM pipeline like this one (ADR 0012's provider
comparison). Its response shape is `{"grounding": {"generic": [{"url", "title",
"snippets"}]}, "sources": {"<url>": {"title", "hostname", "age", ...}}}`, not the plain web
search API's `{"web": {"results": [...]}}` shape.

Results returned by this client must never be persistently cached (ADR 0012, Brave's
Search API terms) — `ai/internet_search/cache.py` enforces this by refusing to write a
Brave-provider result, but this client itself holds no cache either way.

Never logs raw query text, response bodies, or the API key (ADR 0012). The query is sent as
a GET parameter, so `httpx.HTTPStatusError`'s default `str()` (which embeds the request
URL) would leak it into an error message — every exception here is deliberately reduced to
its class name (plus, for an HTTP status error, only the status code and any `Retry-After`
header) before being folded into `BraveError`, matching `ai/image_search/client.py`'s
`WikimediaClient`/`OpenverseClient` (Codex-reviewed, same GET-with-query-param shape).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from ai.internet_search.schemas import (
    InternetSearchItem,
    InternetSearchResult,
    SearchProvider,
    normalize_query,
)

_API_URL = "https://api.search.brave.com/res/v1/llm/context"
_TIMEOUT_SECONDS = 30.0


class BraveError(RuntimeError):
    """Raised when the Brave API call fails, is misconfigured, or returns no usable results."""


class BraveClient:
    """Thin wrapper around Brave Search's LLM Context endpoint."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY")
        if not resolved_key:
            raise BraveError("BRAVE_SEARCH_API_KEY is not configured (see backend/.env.example).")
        self._api_key = resolved_key

    async def search(self, query: str, *, max_results: int = 5) -> InternetSearchResult:
        """Run a Brave LLM Context search and normalize the response into grounding results."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.get(
                    _API_URL,
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._api_key,
                    },
                    params={"q": query, "count": max_results},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            # Only the status code / Retry-After header — never `str(exc)` (embeds the
            # request URL, which carries `query` as a GET param) and never the response
            # body (ADR 0012).
            raise BraveError(f"Brave search failed: {_describe_http_status_error(exc)}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize every other failure to BraveError;
            # deliberately not interpolating `exc` for the same raw-query-text reason above.
            raise BraveError(f"Brave search failed: {exc.__class__.__name__}") from exc

        items = _extract_items(payload)
        if not items:
            raise BraveError("Brave returned no usable results.")
        return InternetSearchResult(
            query=query,
            normalized_query=normalize_query(query),
            provider=SearchProvider.BRAVE,
            results=tuple(items),
            fetched_at=datetime.now(UTC),
        )


def _describe_http_status_error(exc: httpx.HTTPStatusError) -> str:
    status_code = exc.response.status_code
    retry_after = exc.response.headers.get("Retry-After")
    if retry_after:
        return f"HTTP {status_code} (Retry-After: {retry_after})"
    return f"HTTP {status_code}"


def _extract_items(payload: dict) -> list[InternetSearchItem]:
    grounding = payload.get("grounding")
    generic = grounding.get("generic") if isinstance(grounding, dict) else None
    if not isinstance(generic, list):
        return []

    sources = payload.get("sources")
    sources = sources if isinstance(sources, dict) else {}

    items: list[InternetSearchItem] = []
    for entry in generic:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        title = entry.get("title")
        if not isinstance(url, str) or not isinstance(title, str):
            continue
        items.append(
            InternetSearchItem(
                title=title,
                url=url,
                snippet=_join_snippets(entry.get("snippets")),
                published_at=_parse_published_at(sources.get(url)),
                score=None,
            )
        )
    return items


def _join_snippets(snippets: object) -> str:
    """`grounding.generic[].snippets` is a list of extracted text chunks relevant to the
    query -- joined into one string for `InternetSearchItem.snippet`."""
    if not isinstance(snippets, list):
        return ""
    return " ".join(snippet for snippet in snippets if isinstance(snippet, str))


def _parse_published_at(source_entry: object) -> datetime | None:
    """`sources[url].age` is documented as 4 fixed positions (full date, `YYYY-MM-DD`,
    relative age, ISO 8601 timestamp) -- only the ISO 8601 position (index 3) is reliably
    parseable."""
    if not isinstance(source_entry, dict):
        return None
    age = source_entry.get("age")
    if not isinstance(age, list) or len(age) < 4:
        return None
    return _parse_datetime(age[3])


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
