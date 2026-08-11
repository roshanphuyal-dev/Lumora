"""Unit tests for `ai/image_search/cache.py`.

The Redis client itself is mocked (no real Redis dependency for this unit-test tier, same
`.claude/rules/testing.md` split as every other provider client -- a real-Redis smoke test
is a separate concern, not run on every PR). What's under test here is the cache's own
logic: normalized-query keying, the found/not-found/miss three-way distinction, and its
best-effort (never-raises) contract.
"""

from unittest.mock import AsyncMock, patch

from ai.image_search.cache import _cache_key, get_cached_result, set_cached_result
from ai.orchestrator.schemas import TopicImageResult


def _result() -> TopicImageResult:
    return TopicImageResult(
        image_url="https://upload.wikimedia.org/wikipedia/commons/simplex.png",
        attribution="Jane Doe",
        license="CC BY-SA 4.0",
        source_url="https://commons.wikimedia.org/wiki/File:simplex.png",
    )


def _mock_redis(**attrs) -> AsyncMock:
    client = AsyncMock()
    for name, value in attrs.items():
        getattr(client, name).return_value = value
    return client


async def test_get_cached_result_is_a_miss_when_key_absent() -> None:
    with patch("ai.image_search.cache._get_redis_client", return_value=_mock_redis(get=None)):
        cache_hit, result = await get_cached_result("the simplex method", "wikimedia")

    assert cache_hit is False
    assert result is None


async def test_get_cached_result_returns_cached_hit() -> None:
    redis_mock = _mock_redis(get=_result().model_dump_json())
    with patch("ai.image_search.cache._get_redis_client", return_value=redis_mock):
        cache_hit, result = await get_cached_result("the simplex method", "wikimedia")

    assert cache_hit is True
    assert result == _result()


async def test_get_cached_result_distinguishes_cached_not_found_from_a_miss() -> None:
    redis_mock = _mock_redis(get="__not_found__")
    with patch("ai.image_search.cache._get_redis_client", return_value=redis_mock):
        cache_hit, result = await get_cached_result("a wildly obscure topic", "openverse")

    assert cache_hit is True
    assert result is None


async def test_get_cached_result_treats_corrupted_entry_as_a_miss() -> None:
    redis_mock = _mock_redis(get="not valid json")
    with patch("ai.image_search.cache._get_redis_client", return_value=redis_mock):
        cache_hit, result = await get_cached_result("topic", "wikimedia")

    assert cache_hit is False
    assert result is None


async def test_get_cached_result_degrades_to_a_miss_on_redis_failure() -> None:
    with patch("ai.image_search.cache._get_redis_client", side_effect=ConnectionError("down")):
        cache_hit, result = await get_cached_result("topic", "wikimedia")

    assert cache_hit is False
    assert result is None


async def test_set_cached_result_stores_serialized_result_with_ttl() -> None:
    redis_mock = _mock_redis()
    with patch("ai.image_search.cache._get_redis_client", return_value=redis_mock):
        await set_cached_result("the simplex method", "wikimedia", _result())

    args, kwargs = redis_mock.set.call_args
    assert args[1] == _result().model_dump_json()
    assert kwargs["ex"] == 24 * 60 * 60


async def test_set_cached_result_stores_not_found_sentinel() -> None:
    redis_mock = _mock_redis()
    with patch("ai.image_search.cache._get_redis_client", return_value=redis_mock):
        await set_cached_result("a wildly obscure topic", "openverse", None)

    args, _kwargs = redis_mock.set.call_args
    assert args[1] == "__not_found__"


async def test_set_cached_result_never_raises_on_redis_failure() -> None:
    with patch("ai.image_search.cache._get_redis_client", side_effect=ConnectionError("down")):
        await set_cached_result("topic", "wikimedia", _result())  # must not raise


async def test_cache_key_normalizes_query_case_and_whitespace() -> None:
    """`"Simplex Method"` and `"  simplex method  "` must hit the same Redis key."""

    key_a = _cache_key("Simplex Method", "wikimedia")
    key_b = _cache_key("  simplex method  ", "wikimedia")
    assert key_a == key_b


async def test_cache_key_never_contains_the_raw_query_text() -> None:

    assert "super-secret-topic" not in _cache_key("super-secret-topic", "wikimedia")
