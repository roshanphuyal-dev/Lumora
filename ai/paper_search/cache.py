"""Minimal Redis-backed cache for `TaskType.PAPER_SEARCH` results (ADR 0013,
`docs/adr/0013-paper-search-integration.md`).

Mirrors `ai/internet_search/cache.py`'s shape and per-provider-caching-asymmetry pattern
exactly: arXiv results cache for 24h (arXiv's own guidance -- results only change when new
articles are added, no need to re-query more than once/day); Semantic Scholar results must
never be persistently cached at all (its default license's public-display/commercial-use
terms make persistence a legal question, not a code decision -- same restriction already
applied to Brave in `ai/internet_search/cache.py`, ADR 0012).

Reuses the same `REDIS_URL` setting Celery's broker/result backend are configured from
(`backend/app/core/config.py:Settings.redis_url`) via a plain `redis.asyncio` client, same
as `ai/internet_search/cache.py` -- this is a cache client, not a Celery concern.

Cache failures (Redis unreachable, corrupt payload, etc.) degrade to "no cache" rather than
failing the request -- caching is a performance optimization here, not a correctness
requirement.
"""

from __future__ import annotations

import hashlib
import os

import redis.asyncio as redis

from ai.paper_search.schemas import (
    PaperSearchProvider,
    PaperSearchResult,
    normalize_query,
)

_REDIS_URL_ENV = "REDIS_URL"
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_KEY_PREFIX = "paper_search"
_ARXIV_TTL_SECONDS = 24 * 60 * 60  # 24 hours (ADR 0013, arXiv's own caching guidance).


def _client() -> redis.Redis:
    url = os.environ.get(_REDIS_URL_ENV, _DEFAULT_REDIS_URL)
    return redis.from_url(url)


def _cache_key(*, provider: PaperSearchProvider, query: str, max_results: int) -> str:
    digest_input = f"{normalize_query(query)}|{provider.value}|{max_results}"
    digest = hashlib.sha256(digest_input.encode()).hexdigest()
    return f"{_KEY_PREFIX}:{digest}"


async def get_cached_paper_search_result(
    *, provider: PaperSearchProvider, query: str, max_results: int
) -> PaperSearchResult | None:
    """Return a cached result, or `None` on a cache miss, Semantic Scholar (never cached),
    or any Redis/deserialization error.
    """
    if provider is PaperSearchProvider.SEMANTIC_SCHOLAR:
        return None  # Semantic Scholar results are never cached (ADR 0013).

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
        return PaperSearchResult.model_validate_json(raw)
    except ValueError:
        return None


async def set_cached_paper_search_result(result: PaperSearchResult, *, max_results: int) -> None:
    """Cache `result`, subject to the per-provider TTL/no-cache policy (ADR 0013).

    Silently no-ops on a Redis error -- caching is best-effort, never allowed to fail the
    request that produced `result`.
    """
    if result.provider is PaperSearchProvider.SEMANTIC_SCHOLAR:
        return  # Semantic Scholar results must not be persistently cached (ADR 0013).

    client = _client()
    try:
        await client.set(
            _cache_key(provider=result.provider, query=result.query, max_results=max_results),
            result.model_dump_json(),
            ex=_ARXIV_TTL_SECONDS,
        )
    except Exception:  # noqa: BLE001, S110 - caching is best-effort, never fails the request
        pass
    finally:
        await client.aclose()
