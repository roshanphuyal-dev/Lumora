"""Redis-backed cache for `ai.image_search` results (ADR 0010, `docs/TOKEN_OPTIMIZATION.md`).

Standalone cache scoped to this feature — no shared `ai/cache.py` existed yet when this was
built (checked `ai/` for one before writing this). If `TaskType.INTERNET_SEARCH`'s work adds
a shared cache module later, this can be folded into it, but this task type isn't blocked on
that landing first.

Keyed by a hash of the normalized query text + provider name (`docs/TOKEN_OPTIMIZATION.md`'s
"content hash + generation parameters" caching principle, applied here to a retrieval call
rather than a generation call) so `"Simplex Method"` and `"simplex method"` hit the same
entry. TTL is 24h — much longer than a typical AI-response cache: Wikimedia/Openverse images
and their license/attribution metadata are stable, and neither provider imposes a storage-
retention restriction the way e.g. Brave's search ToS does.

A "no good match" result is cached too (as a sentinel), not just successful hits — a niche
topic that returns nothing is exactly the kind of repeat lookup this cache exists to avoid
re-hitting the provider for.

Best-effort: a Redis outage degrades to "always call the provider", it never fails a search
(caching is a cost optimization here, not a correctness dependency). Reads `REDIS_URL`
straight from the environment rather than importing `backend.app.core.config.Settings` —
same `ai/`-is-decoupled-from-`Settings` convention every other provider client's env-key
resolution already follows (`ai/gemini/client.py`, `ai/opencode_zen/client.py`).
"""

from __future__ import annotations

import hashlib
import os

import redis.asyncio as redis

from ai.orchestrator.schemas import TopicImageResult

_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h — images/attribution are stable (ADR 0010).
_NOT_FOUND_SENTINEL = "__not_found__"

_redis_client: redis.Redis | None = None


def _get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def _cache_key(query: str, provider: str) -> str:
    # Never store the raw query text as (part of) the key itself — hash it. Redis keys can
    # show up in ops tooling (SCAN, slow logs, RDB dumps); a student's study topic doesn't
    # belong there in plaintext any more than it belongs in an application log.
    normalized = query.strip().casefold()
    digest = hashlib.sha256(f"{provider}:{normalized}".encode()).hexdigest()
    return f"image_search:{provider}:{digest}"


async def get_cached_result(query: str, provider: str) -> tuple[bool, TopicImageResult | None]:
    """Look up a cached result for `query` against `provider` ("wikimedia"/"openverse").

    Returns `(cache_hit, result)`. `result` is `None` for both a cache miss (`cache_hit`
    is `False`, callers should call the provider) and a cached "no good match" result
    (`cache_hit` is `True`, callers should treat this exactly like a fresh no-match
    response, not call the provider again) — callers must branch on `cache_hit`, not on
    whether `result` is `None`, to tell the two apart.
    """
    try:
        client = _get_redis_client()
        raw = await client.get(_cache_key(query, provider))
    except Exception:  # noqa: BLE001 - cache is best-effort, never blocks a search
        return False, None

    if raw is None:
        return False, None
    if raw == _NOT_FOUND_SENTINEL:
        return True, None
    try:
        return True, TopicImageResult.model_validate_json(raw)
    except Exception:  # noqa: BLE001 - corrupted/stale cache entry, treat as a miss
        return False, None


async def set_cached_result(query: str, provider: str, result: TopicImageResult | None) -> None:
    """Cache `result` (or a "no good match" sentinel, if `result` is `None`) for 24h."""
    try:
        client = _get_redis_client()
        payload = _NOT_FOUND_SENTINEL if result is None else result.model_dump_json()
        await client.set(_cache_key(query, provider), payload, ex=_CACHE_TTL_SECONDS)
    except Exception:  # noqa: BLE001, S110 - cache is best-effort, never blocks a search
        pass
