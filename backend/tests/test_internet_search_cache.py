"""Unit tests for `ai/internet_search/cache.py` (ADR 0012's per-provider caching
asymmetry: Tavily cached with a short TTL, Brave never cached).

The Redis client itself is mocked out (`redis.asyncio.from_url`) -- no real Redis instance
is required to run these tests, per `.claude/rules/testing.md`'s "mock only the actual
external dependency" convention.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from ai.internet_search.cache import get_cached_search_result, set_cached_search_result
from ai.internet_search.schemas import (
    InternetSearchItem,
    InternetSearchResult,
    SearchProvider,
    normalize_query,
)


def _result(provider: SearchProvider) -> InternetSearchResult:
    return InternetSearchResult(
        query="  Fusion   Energy  ",
        normalized_query="fusion energy",
        provider=provider,
        results=(InternetSearchItem(title="t", url="https://x", snippet="s"),),
        fetched_at=datetime.now(UTC),
    )


def _fake_redis_client() -> AsyncMock:
    store: dict[str, str] = {}

    async def fake_get(key: str) -> str | None:
        return store.get(key)

    async def fake_set(key: str, value: str, ex: int | None = None) -> None:
        store[key] = value

    fake_client = AsyncMock()
    fake_client.get.side_effect = fake_get
    fake_client.set.side_effect = fake_set
    fake_client.aclose = AsyncMock()
    fake_client._store = store  # exposed for assertions
    return fake_client


async def test_get_cached_search_result_returns_none_for_brave_without_touching_redis() -> None:
    with patch("ai.internet_search.cache.redis.from_url") as from_url_mock:
        result = await get_cached_search_result(
            provider=SearchProvider.BRAVE, query="q", max_results=5
        )

    assert result is None
    from_url_mock.assert_not_called()


async def test_set_cached_search_result_skips_brave_without_touching_redis() -> None:
    with patch("ai.internet_search.cache.redis.from_url") as from_url_mock:
        await set_cached_search_result(_result(SearchProvider.BRAVE), max_results=5)

    from_url_mock.assert_not_called()


async def test_set_and_get_cached_tavily_result_round_trips() -> None:
    fake_client = _fake_redis_client()

    with patch("ai.internet_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_search_result(_result(SearchProvider.TAVILY), max_results=5)
        cached = await get_cached_search_result(
            provider=SearchProvider.TAVILY, query="  Fusion   Energy  ", max_results=5
        )

    assert cached is not None
    assert cached.provider == SearchProvider.TAVILY
    assert cached.results[0].url == "https://x"
    # TTL applied on write (ADR 0012: 10 minutes for Tavily).
    _, kwargs = fake_client.set.call_args
    assert kwargs["ex"] == 600


async def test_get_cached_search_result_normalizes_query_for_the_cache_key() -> None:
    """Differently-whitespaced/cased queries that normalize the same must hit the same
    cache entry."""
    fake_client = _fake_redis_client()

    with patch("ai.internet_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_search_result(_result(SearchProvider.TAVILY), max_results=5)
        cached = await get_cached_search_result(
            provider=SearchProvider.TAVILY, query="FUSION energy", max_results=5
        )

    assert cached is not None


async def test_get_cached_search_result_returns_none_on_redis_error() -> None:
    fake_client = AsyncMock()
    fake_client.get.side_effect = ConnectionError("no redis")
    fake_client.aclose = AsyncMock()

    with patch("ai.internet_search.cache.redis.from_url", return_value=fake_client):
        result = await get_cached_search_result(
            provider=SearchProvider.TAVILY, query="q", max_results=5
        )

    assert result is None


async def test_set_cached_search_result_swallows_redis_error() -> None:
    fake_client = AsyncMock()
    fake_client.set.side_effect = ConnectionError("no redis")
    fake_client.aclose = AsyncMock()

    with patch("ai.internet_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_search_result(_result(SearchProvider.TAVILY), max_results=5)  # no raise


def test_normalize_query_collapses_whitespace_and_casefolds() -> None:
    assert normalize_query("  Fusion   ENERGY \n News ") == "fusion energy news"
