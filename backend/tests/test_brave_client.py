"""Unit tests for `ai/internet_search/brave_client.py:BraveClient`.

Per `.claude/rules/testing.md`: the actual Brave HTTP call is mocked out
(`httpx.AsyncClient`, same pattern as `backend/tests/test_tavily_client.py`), but the
client's own request-building, response-parsing, and error-normalization logic all run for
real.

Payloads use Brave's LLM Context endpoint's documented response shape
(`{"grounding": {"generic": [...]}, "sources": {...}}`), not the plain web search API's
`{"web": {"results": [...]}}` shape -- the two are different endpoints/schemas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.internet_search.brave_client import BraveClient, BraveError
from ai.internet_search.schemas import SearchProvider


def _mock_http_client(*, response: MagicMock) -> MagicMock:
    http_client = AsyncMock()
    http_client.get.return_value = response
    context_manager = MagicMock()
    context_manager.__aenter__.return_value = http_client
    context_manager.__aexit__.return_value = False
    return context_manager


def _mock_response(*, payload: dict, status_error: Exception | None = None) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    return response


async def test_search_returns_normalized_results() -> None:
    client = BraveClient(api_key="test-key")
    response = _mock_response(
        payload={
            "grounding": {
                "generic": [
                    {
                        "url": "https://example.com/fusion",
                        "title": "Fusion breakthrough",
                        "snippets": ["Scientists announced a milestone.", "More detail."],
                    }
                ],
                "poi": {},
                "map": [],
            },
            "sources": {
                "https://example.com/fusion": {
                    "title": "Fusion breakthrough",
                    "hostname": "example.com",
                    "age": [
                        "August 1, 2026",
                        "2026-08-01",
                        "a few days ago",
                        "2026-08-01T00:00:00",
                    ],
                }
            },
        }
    )

    with patch(
        "ai.internet_search.brave_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        result = await client.search("  Fusion   Energy  News ", max_results=3)

    assert result.provider == SearchProvider.BRAVE
    assert result.normalized_query == "fusion energy news"
    assert len(result.results) == 1
    item = result.results[0]
    assert item.title == "Fusion breakthrough"
    assert item.url == "https://example.com/fusion"
    assert item.snippet == "Scientists announced a milestone. More detail."
    assert item.score is None
    assert item.published_at is not None


async def test_search_handles_missing_sources_entry() -> None:
    """A `grounding.generic` item with no matching `sources[url]` entry (e.g.
    `enable_source_metadata` not requested) still yields a usable item, just without
    `published_at`."""
    client = BraveClient(api_key="test-key")
    response = _mock_response(
        payload={
            "grounding": {"generic": [{"url": "https://x", "title": "t", "snippets": ["s"]}]},
            "sources": {},
        }
    )

    with patch(
        "ai.internet_search.brave_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        result = await client.search("q")

    assert len(result.results) == 1
    assert result.results[0].published_at is None


async def test_search_hits_llm_context_endpoint_with_subscription_token_header() -> None:
    client = BraveClient(api_key="test-key")
    response = _mock_response(
        payload={"grounding": {"generic": [{"url": "https://x", "title": "t", "snippets": ["s"]}]}}
    )
    http_context = _mock_http_client(response=response)

    with patch("ai.internet_search.brave_client.httpx.AsyncClient", return_value=http_context):
        await client.search("q", max_results=7)

    http_client = http_context.__aenter__.return_value
    args, kwargs = http_client.get.call_args
    assert args[0] == "https://api.search.brave.com/res/v1/llm/context"
    assert kwargs["headers"]["X-Subscription-Token"] == "test-key"
    assert kwargs["params"] == {"q": "q", "count": 7}


async def test_search_raises_on_http_error_without_leaking_query_or_url() -> None:
    """ADR 0012: raw query text must never leak into an error message. Brave sends `query`
    as a GET param, so `httpx.HTTPStatusError`'s default `str()` (which embeds the request
    URL) would leak it if interpolated directly -- assert it never is, and that the safe
    status-code/Retry-After detail is surfaced instead."""
    client = BraveClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": "30"}
    status_error = httpx.HTTPStatusError(
        "Client error '429 Too Many Requests' for url "
        "'https://api.search.brave.com/res/v1/llm/context?q=super+secret+student+query'",
        request=MagicMock(),
        response=error_response,
    )
    response = _mock_response(payload={}, status_error=status_error)

    with patch(
        "ai.internet_search.brave_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        with pytest.raises(BraveError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "429" in message
    assert "30" in message


async def test_search_raises_on_connection_error_without_leaking_query() -> None:
    """Same leak check as above, for a non-HTTP-status failure (e.g. a connection error,
    whose `str()` can also embed the request URL/query)."""
    client = BraveClient(api_key="test-key")
    connect_error = httpx.ConnectError(
        "Connection refused: https://api.search.brave.com/res/v1/llm/context"
        "?q=super+secret+student+query"
    )

    with patch("ai.internet_search.brave_client.httpx.AsyncClient", side_effect=connect_error):
        with pytest.raises(BraveError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "ConnectError" in message


async def test_search_raises_on_empty_results() -> None:
    client = BraveClient(api_key="test-key")
    response = _mock_response(payload={"grounding": {"generic": []}, "sources": {}})

    with patch(
        "ai.internet_search.brave_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        with pytest.raises(BraveError, match="no usable results"):
            await client.search("q")


async def test_search_skips_malformed_result_entries() -> None:
    client = BraveClient(api_key="test-key")
    response = _mock_response(
        payload={
            "grounding": {
                "generic": [
                    {"title": "no url", "snippets": ["d"]},
                    {"url": "https://good", "title": "Good", "snippets": ["d"]},
                ]
            },
            "sources": {},
        }
    )

    with patch(
        "ai.internet_search.brave_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        result = await client.search("q")

    assert len(result.results) == 1
    assert result.results[0].url == "https://good"


def test_constructor_raises_when_api_key_missing() -> None:
    with patch("ai.internet_search.brave_client.os.environ.get", return_value=None):
        with pytest.raises(BraveError, match="BRAVE_SEARCH_API_KEY"):
            BraveClient()


def test_constructor_reads_api_key_from_environment() -> None:
    with patch("ai.internet_search.brave_client.os.environ.get", return_value="from-env"):
        client = BraveClient()

    assert client._api_key == "from-env"
