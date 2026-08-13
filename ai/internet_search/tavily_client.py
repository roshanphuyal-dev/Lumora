"""Tavily Search API client (ADR 0012, `docs/adr/0012-internet-search-integration.md`).

The only place Tavily's API is called (.claude/rules/ai.md) — nothing outside `ai/`
should call it directly. Used as the orchestrator's primary provider for
`TaskType.INTERNET_SEARCH` (`ai/orchestrator/orchestrator.py`), with Brave
(`ai/internet_search/brave_client.py`) as an optional fallback.

Always requests `include_answer=false`/`search_depth="basic"` — ADR 0012's synthesis-pass
decision means Tavily's own "answer" mode is never used; only its ranked results are, and
Gemini synthesizes the final student-facing answer from them
(`ai/orchestrator/orchestrator.py:_run_internet_search`).

Never logs raw query text, response bodies, or the API key (ADR 0012).
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

_API_URL = "https://api.tavily.com/search"
_TIMEOUT_SECONDS = 30.0


class TavilyError(RuntimeError):
    """Raised when the Tavily API call fails, is misconfigured, or returns no usable results."""


class TavilyClient:
    """Thin wrapper around the Tavily Search API."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not resolved_key:
            raise TavilyError("TAVILY_API_KEY is not configured (see backend/.env.example).")
        self._api_key = resolved_key

    async def search(self, query: str, *, max_results: int = 5) -> InternetSearchResult:
        """Run a basic Tavily search and normalize the response into grounding results.

        `include_answer=false`, `search_depth="basic"` per ADR 0012 — retrieval only,
        never a provider-generated answer.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.post(
                    _API_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": False,
                        "max_results": max_results,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise TavilyError(f"Tavily search failed: {_describe_http_status_error(exc)}") from exc
        except Exception as exc:  # normalize every other failure to TavilyError;
            # never interpolate `exc`: transport/decoding errors may contain provider
            # response data or request details (ADR 0012).
            raise TavilyError(f"Tavily search failed: {exc.__class__.__name__}") from exc

        items = _extract_items(payload)
        if not items:
            raise TavilyError("Tavily returned no usable results.")
        return InternetSearchResult(
            query=query,
            normalized_query=normalize_query(query),
            provider=SearchProvider.TAVILY,
            results=tuple(items),
            fetched_at=datetime.now(UTC),
        )


def _extract_items(payload: dict) -> list[InternetSearchItem]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return []
    items: list[InternetSearchItem] = []
    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        title = entry.get("title")
        if not isinstance(url, str) or not isinstance(title, str):
            continue
        content = entry.get("content")
        score = entry.get("score")
        items.append(
            InternetSearchItem(
                title=title,
                url=url,
                snippet=content if isinstance(content, str) else "",
                published_at=_parse_datetime(entry.get("published_date")),
                score=score if isinstance(score, int | float) else None,
            )
        )
    return items


def _describe_http_status_error(exc: httpx.HTTPStatusError) -> str:
    """Return only safe, operationally useful HTTP metadata."""
    status_code = exc.response.status_code
    retry_after = exc.response.headers.get("Retry-After")
    if retry_after and retry_after.isascii() and retry_after.isdigit():
        return f"HTTP {status_code} (Retry-After: {retry_after})"
    return f"HTTP {status_code}"


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
