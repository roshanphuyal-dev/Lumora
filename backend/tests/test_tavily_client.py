"""Unit tests for `ai/internet_search/tavily_client.py:TavilyClient`.

Per `.claude/rules/testing.md`: the actual Tavily HTTP call is mocked out
(`httpx.AsyncClient`, same pattern as `backend/tests/test_opencode_zen_client.py`), but the
client's own request-building, response-parsing, and error-normalization logic all run for
real.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.internet_search.schemas import SearchProvider
from ai.internet_search.tavily_client import TavilyClient, TavilyError


def _mock_http_client(*, response: MagicMock) -> MagicMock:
    http_client = AsyncMock()
    http_client.post.return_value = response
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
    client = TavilyClient(api_key="test-key")
    response = _mock_response(
        payload={
            "results": [
                {
                    "title": "Fusion breakthrough",
                    "url": "https://example.com/fusion",
                    "content": "Scientists announced a milestone.",
                    "score": 0.9,
                }
            ]
        }
    )

    with patch(
        "ai.internet_search.tavily_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        result = await client.search("  Fusion   Energy  News ", max_results=3)

    assert result.provider == SearchProvider.TAVILY
    assert result.query == "  Fusion   Energy  News "
    assert result.normalized_query == "fusion energy news"
    assert len(result.results) == 1
    item = result.results[0]
    assert item.title == "Fusion breakthrough"
    assert item.url == "https://example.com/fusion"
    assert item.snippet == "Scientists announced a milestone."
    assert item.score == 0.9


async def test_search_sends_bearer_auth_and_no_answer_mode() -> None:
    client = TavilyClient(api_key="test-key")
    response = _mock_response(
        payload={"results": [{"title": "t", "url": "https://x", "content": "c"}]}
    )
    http_context = _mock_http_client(response=response)

    with patch("ai.internet_search.tavily_client.httpx.AsyncClient", return_value=http_context):
        await client.search("q", max_results=7)

    http_client = http_context.__aenter__.return_value
    _, kwargs = http_client.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer test-key"}
    assert kwargs["json"]["include_answer"] is False
    assert kwargs["json"]["search_depth"] == "basic"
    assert kwargs["json"]["max_results"] == 7
    assert kwargs["json"]["query"] == "q"
    # Regression guard for docs/SECURITY.md's Tavily invariant: only the bare query
    # string and search parameters ever reach Tavily. Checking value-per-key (above)
    # doesn't catch a future change that silently *adds* a key (e.g. notebook context
    # appended to the request body) -- assert the full key set too.
    assert set(kwargs["json"].keys()) == {"query", "search_depth", "include_answer", "max_results"}


async def test_search_raises_on_rate_limit_without_leaking_request_or_response() -> None:
    client = TavilyClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": "30"}
    status_error = httpx.HTTPStatusError(
        "secret query and provider response body",
        request=MagicMock(),
        response=error_response,
    )
    response = _mock_response(payload={}, status_error=status_error)
    http_context = _mock_http_client(response=response)

    with patch(
        "ai.internet_search.tavily_client.httpx.AsyncClient",
        return_value=http_context,
    ):
        with pytest.raises(TavilyError) as exc_info:
            await client.search("secret query")

    message = str(exc_info.value)
    assert "secret query" not in message
    assert "provider response body" not in message
    assert "HTTP 429" in message
    assert "Retry-After: 30" in message
    http_context.__aenter__.return_value.post.assert_awaited_once()


async def test_search_raises_on_empty_results() -> None:
    client = TavilyClient(api_key="test-key")
    response = _mock_response(payload={"results": []})

    with patch(
        "ai.internet_search.tavily_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        with pytest.raises(TavilyError, match="no usable results"):
            await client.search("q")


async def test_search_skips_malformed_result_entries() -> None:
    """An entry missing `title`/`url` is dropped rather than raising -- a partially
    malformed response still returns whatever's usable."""
    client = TavilyClient(api_key="test-key")
    response = _mock_response(
        payload={
            "results": [
                {"title": "no url", "content": "c"},
                {"title": "Good", "url": "https://good", "content": "c"},
            ]
        }
    )

    with patch(
        "ai.internet_search.tavily_client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        result = await client.search("q")

    assert len(result.results) == 1
    assert result.results[0].url == "https://good"


def test_constructor_raises_when_api_key_missing() -> None:
    with patch("ai.internet_search.tavily_client.os.environ.get", return_value=None):
        with pytest.raises(TavilyError, match="TAVILY_API_KEY"):
            TavilyClient()


def test_constructor_reads_api_key_from_environment() -> None:
    with patch("ai.internet_search.tavily_client.os.environ.get", return_value="from-env"):
        client = TavilyClient()

    assert client._api_key == "from-env"
