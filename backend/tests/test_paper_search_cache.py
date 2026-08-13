"""Unit tests for `ai/paper_search/cache.py` (ADR 0013's per-provider caching asymmetry:
arXiv cached for 24h, Semantic Scholar never cached).

The Redis client itself is mocked out (`redis.asyncio.from_url`) -- no real Redis instance
is required to run these tests, per `.claude/rules/testing.md`'s "mock only the actual
external dependency" convention.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from ai.paper_search.cache import get_cached_paper_search_result, set_cached_paper_search_result
from ai.paper_search.schemas import (
    PaperSearchItem,
    PaperSearchProvider,
    PaperSearchResult,
    normalize_query,
)


def _result(provider: PaperSearchProvider) -> PaperSearchResult:
    return PaperSearchResult(
        query="  Fusion   Energy  ",
        normalized_query="fusion energy",
        provider=provider,
        results=(
            PaperSearchItem(
                title="t", authors=("A. Author",), url="https://arxiv.org/abs/1234.5678"
            ),
        ),
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


async def test_get_cached_result_returns_none_for_semantic_scholar_without_redis() -> None:
    with patch("ai.paper_search.cache.redis.from_url") as from_url_mock:
        result = await get_cached_paper_search_result(
            provider=PaperSearchProvider.SEMANTIC_SCHOLAR, query="q", max_results=5
        )

    assert result is None
    from_url_mock.assert_not_called()


async def test_set_cached_paper_search_result_skips_semantic_scholar_without_redis() -> None:
    with patch("ai.paper_search.cache.redis.from_url") as from_url_mock:
        await set_cached_paper_search_result(
            _result(PaperSearchProvider.SEMANTIC_SCHOLAR), max_results=5
        )

    from_url_mock.assert_not_called()


async def test_set_and_get_cached_arxiv_result_round_trips() -> None:
    fake_client = _fake_redis_client()

    with patch("ai.paper_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_paper_search_result(_result(PaperSearchProvider.ARXIV), max_results=5)
        cached = await get_cached_paper_search_result(
            provider=PaperSearchProvider.ARXIV, query="  Fusion   Energy  ", max_results=5
        )

    assert cached is not None
    assert cached.provider == PaperSearchProvider.ARXIV
    assert cached.results[0].url == "https://arxiv.org/abs/1234.5678"
    # TTL applied on write (ADR 0013: 24 hours for arXiv).
    _, kwargs = fake_client.set.call_args
    assert kwargs["ex"] == 24 * 60 * 60


async def test_get_cached_paper_search_result_normalizes_query_for_the_cache_key() -> None:
    fake_client = _fake_redis_client()

    with patch("ai.paper_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_paper_search_result(_result(PaperSearchProvider.ARXIV), max_results=5)
        cached = await get_cached_paper_search_result(
            provider=PaperSearchProvider.ARXIV, query="FUSION energy", max_results=5
        )

    assert cached is not None


async def test_get_cached_paper_search_result_returns_none_on_redis_error() -> None:
    fake_client = AsyncMock()
    fake_client.get.side_effect = ConnectionError("no redis")
    fake_client.aclose = AsyncMock()

    with patch("ai.paper_search.cache.redis.from_url", return_value=fake_client):
        result = await get_cached_paper_search_result(
            provider=PaperSearchProvider.ARXIV, query="q", max_results=5
        )

    assert result is None


async def test_set_cached_paper_search_result_swallows_redis_error() -> None:
    fake_client = AsyncMock()
    fake_client.set.side_effect = ConnectionError("no redis")
    fake_client.aclose = AsyncMock()

    with patch("ai.paper_search.cache.redis.from_url", return_value=fake_client):
        await set_cached_paper_search_result(
            _result(PaperSearchProvider.ARXIV), max_results=5
        )  # no raise


def test_normalize_query_collapses_whitespace_and_casefolds() -> None:
    assert normalize_query("  Fusion   ENERGY \n News ") == "fusion energy news"
