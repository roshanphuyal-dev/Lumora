"""Minimal Redis-backed cache for `TaskType.INTERNET_SEARCH` results (ADR 0012,
`docs/adr/0012-internet-search-integration.md`).

A per-provider-asymmetric cache, not a general AI-response cache framework -- a general
framework was explicitly rejected as premature in ADR 0012's Alternatives Considered; build
only what this feature needs. Tavily results cache for a short TTL; Brave results must
never be cached at all, per Brave's Search API terms (ADR 0012's Tradeoffs/Consequences).

Reuses the same `REDIS_URL` setting Celery's broker/result backend are configured from
(`backend/app/core/config.py:Settings.redis_url`, `backend/app/workers/celery_app.py`) via
a plain `redis.asyncio` client -- this is a cache client, not a Celery concern, so it talks
to Redis directly rather than through Celery.

Cache failures (Redis unreachable, corrupt payload, etc.) degrade to "no cache" rather than
failing the request -- caching is a performance optimization here, not a correctness
requirement.
"""

from __future__ import annotations

import hashlib
import os

import redis.asyncio as redis

from ai.internet_search.schemas import InternetSearchResult, SearchProvider, normalize_query

_REDIS_URL_ENV = "REDIS_URL"
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_KEY_PREFIX = "internet_search"
_TAVILY_TTL_SECONDS = 10 * 60  # 10 minutes (ADR 0012).


def _client() -> redis.Redis:
    url = os.environ.get(_REDIS_URL_ENV, _DEFAULT_REDIS_URL)
    return redis.from_url(url)


def _cache_key(*, provider: SearchProvider, query: str, max_results: int) -> str:
    digest_input = f"{normalize_query(query)}|{provider.value}|{max_results}"
    digest = hashlib.sha256(digest_input.encode()).hexdigest()
    return f"{_KEY_PREFIX}:{digest}"


async def get_cached_search_result(
    *, provider: SearchProvider, query: str, max_results: int
) -> InternetSearchResult | None:
    """Return a cached result, or `None` on a cache miss, Brave (never cached), or any
    Redis/deserialization error.
    """
    if provider is SearchProvider.BRAVE:
        return None  # Brave results are never cached (ADR 0012).

    client = _client()
    try:
        raw = await client.get(_cache_key(provider=provider, query=query, max_results=max_results))
    except Exception:  # noqa: BLE001 - a cache error degrades to a miss, never fails the request
        return None
    finally:
        await client.aclose()

    if raw is None:
        return None
    try:
        return InternetSearchResult.model_validate_json(raw)
    except ValueError:
        return None


async def set_cached_search_result(result: InternetSearchResult, *, max_results: int) -> None:
    """Cache `result`, subject to the per-provider TTL/no-cache policy (ADR 0012).

    Silently no-ops on a Redis error -- caching is best-effort, never allowed to fail the
    request that produced `result`.
    """
    if result.provider is SearchProvider.BRAVE:
        return  # Brave results must not be persistently cached (ADR 0012).

    client = _client()
    try:
        await client.set(
            _cache_key(provider=result.provider, query=result.query, max_results=max_results),
            result.model_dump_json(),
            ex=_TAVILY_TTL_SECONDS,
        )
    except Exception:  # noqa: BLE001 - caching is best-effort, never fails the request
        pass
    finally:
        await client.aclose()
