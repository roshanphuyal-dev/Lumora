"""Unit tests for `ai/paper_search/semantic_scholar_client.py:SemanticScholarClient`.

Per `.claude/rules/testing.md`: the actual Semantic Scholar HTTP call is mocked out
(`httpx.AsyncClient`, same pattern as `backend/tests/test_tavily_client.py`), but the
client's own request-building, response-parsing, retry/backoff, and error-normalization
logic all run for real. `asyncio.sleep` is patched in every test that calls `.search()` so
neither the 1-req/sec rate limiter nor the 429 backoff actually slows the test suite down.
"""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.paper_search.schemas import PaperSearchProvider
from ai.paper_search.semantic_scholar_client import SemanticScholarClient, SemanticScholarError


def _mock_http_client(*, response: MagicMock | list[MagicMock]) -> MagicMock:
    http_client = AsyncMock()
    if isinstance(response, list):
        http_client.get.side_effect = response
    else:
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
    client = SemanticScholarClient(api_key="test-key")
    response = _mock_response(
        payload={
            "data": [
                {
                    "title": "Fusion Energy Breakthroughs",
                    "authors": [{"name": "Ada Researcher"}, {"name": "Grace Scientist"}],
                    "abstract": "A survey of recent fusion energy milestones.",
                    "publicationDate": "2024-01-01",
                    "venue": "J. Fusion Energy",
                    "citationCount": 12,
                    "url": "https://www.semanticscholar.org/paper/abc123",
                    "openAccessPdf": {"url": "https://example.com/fusion.pdf"},
                }
            ]
        }
    )

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("  Fusion   Energy  ", max_results=3)

    assert result.provider == PaperSearchProvider.SEMANTIC_SCHOLAR
    assert result.normalized_query == "fusion energy"
    assert len(result.results) == 1
    item = result.results[0]
    assert item.title == "Fusion Energy Breakthroughs"
    assert item.authors == ("Ada Researcher", "Grace Scientist")
    assert item.abstract == "A survey of recent fusion energy milestones."
    assert item.publication_date.isoformat() == "2024-01-01"
    assert item.venue == "J. Fusion Energy"
    assert item.citation_count == 12
    assert item.url == "https://www.semanticscholar.org/paper/abc123"
    assert item.pdf_url == "https://example.com/fusion.pdf"


async def test_search_sends_api_key_header_and_fields_param_when_configured() -> None:
    client = SemanticScholarClient(api_key="test-key")
    response = _mock_response(payload={"data": []})
    http_context = _mock_http_client(response=response)

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        await client.search("q", max_results=7)

    http_client = http_context.__aenter__.return_value
    args, kwargs = http_client.get.call_args
    assert args[0] == "https://api.semanticscholar.org/graph/v1/paper/search"
    assert kwargs["headers"] == {"x-api-key": "test-key"}
    assert kwargs["params"]["query"] == "q"
    assert kwargs["params"]["limit"] == 7
    assert "title" in kwargs["params"]["fields"]
    assert "abstract" in kwargs["params"]["fields"]


async def test_search_omits_api_key_header_when_not_configured() -> None:
    """Unlike Tavily/Brave, a missing key never refuses construction or search -- it just
    sends an unauthenticated request against Semantic Scholar's shared pool (ADR 0013)."""
    client = SemanticScholarClient(api_key=None)
    response = _mock_response(payload={"data": []})
    http_context = _mock_http_client(response=response)

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
        patch("ai.paper_search.semantic_scholar_client.os.environ.get", return_value=None),
    ):
        result = await client.search("q")

    http_client = http_context.__aenter__.return_value
    _, kwargs = http_client.get.call_args
    assert kwargs["headers"] == {}
    assert result.results == ()


async def test_search_returns_successful_empty_result_not_an_error() -> None:
    client = SemanticScholarClient(api_key="test-key")
    response = _mock_response(payload={"data": []})

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("a very obscure niche topic")

    assert result.results == ()


async def test_search_retries_on_429_then_succeeds() -> None:
    client = SemanticScholarClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": "2"}
    status_error = httpx.HTTPStatusError(
        "rate limited", request=MagicMock(), response=error_response
    )
    failing_response = _mock_response(payload={}, status_error=status_error)
    succeeding_response = _mock_response(payload={"data": []})
    http_context = _mock_http_client(response=[failing_response, succeeding_response])
    sleep_mock = AsyncMock()

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=sleep_mock),
    ):
        result = await client.search("q")

    assert result.results == ()
    http_client = http_context.__aenter__.return_value
    assert http_client.get.await_count == 2
    sleep_mock.assert_any_await(2.0)


async def test_search_retries_honoring_http_date_retry_after() -> None:
    """`Retry-After` may be sent as an HTTP-date instead of delay-seconds (RFC 9110
    10.2.3, e.g. "Wed, 21 Oct 2026 07:28:00 GMT") -- when the server sends that form, the
    remaining time until it must be honored rather than falling back to the local
    exponential backoff (which would retry earlier than the server instructed)."""
    client = SemanticScholarClient(api_key="test-key")
    retry_at = datetime.now(UTC) + timedelta(seconds=5)
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": format_datetime(retry_at, usegmt=True)}
    status_error = httpx.HTTPStatusError(
        "rate limited", request=MagicMock(), response=error_response
    )
    failing_response = _mock_response(payload={}, status_error=status_error)
    succeeding_response = _mock_response(payload={"data": []})
    http_context = _mock_http_client(response=[failing_response, succeeding_response])
    sleep_mock = AsyncMock()

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=sleep_mock),
    ):
        result = await client.search("q")

    assert result.results == ()
    # `sleep_mock` also captures the rate-limiter's own throttle sleep (`_throttle`, called
    # on every attempt), so assert one of the recorded delays honors the ~5s remaining
    # until the HTTP-date rather than asserting a single call -- a wide-but-discriminating
    # margin (vs. the 1.0s exponential fallback) to absorb test-execution jitter.
    delays = [call_args.args[0] for call_args in sleep_mock.await_args_list]
    assert any(3.0 <= delay <= 5.5 for delay in delays), delays


async def test_search_falls_back_to_exponential_backoff_on_unparseable_retry_after() -> None:
    client = SemanticScholarClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": "not-a-valid-value"}
    status_error = httpx.HTTPStatusError(
        "rate limited", request=MagicMock(), response=error_response
    )
    failing_response = _mock_response(payload={}, status_error=status_error)
    succeeding_response = _mock_response(payload={"data": []})
    http_context = _mock_http_client(response=[failing_response, succeeding_response])
    sleep_mock = AsyncMock()

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=sleep_mock),
    ):
        await client.search("q")

    # Same reasoning as the HTTP-date test above -- `sleep_mock` also captures the
    # rate-limiter's own throttle sleep, so check the backoff delay is present among the
    # recorded calls rather than asserting there was exactly one.
    sleep_mock.assert_any_await(1.0)  # _BASE_BACKOFF_SECONDS * 2**0


async def test_search_raises_after_exhausting_retries_on_429() -> None:
    client = SemanticScholarClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {}
    status_error = httpx.HTTPStatusError(
        "rate limited", request=MagicMock(), response=error_response
    )
    failing_response = _mock_response(payload={}, status_error=status_error)
    http_context = _mock_http_client(response=failing_response)

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(SemanticScholarError, match="HTTP 429"):
            await client.search("q")


async def test_search_raises_on_http_error_without_leaking_query() -> None:
    client = SemanticScholarClient(api_key="test-key")
    error_response = MagicMock()
    error_response.status_code = 403
    error_response.headers = {}
    status_error = httpx.HTTPStatusError(
        "Client error for url "
        "'https://api.semanticscholar.org/graph/v1/paper/search"
        "?query=super+secret+student+query'",
        request=MagicMock(),
        response=error_response,
    )
    response = _mock_response(payload={}, status_error=status_error)
    http_context = _mock_http_client(response=response)

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=http_context,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(SemanticScholarError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "HTTP 403" in message


async def test_search_raises_on_connection_error_without_leaking_query() -> None:
    client = SemanticScholarClient(api_key="test-key")
    connect_error = httpx.ConnectError(
        "Connection refused: https://api.semanticscholar.org/graph/v1/paper/search"
        "?query=super+secret+student+query"
    )

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            side_effect=connect_error,
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(SemanticScholarError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "ConnectError" in message


async def test_search_skips_malformed_result_entries() -> None:
    client = SemanticScholarClient(api_key="test-key")
    response = _mock_response(
        payload={
            "data": [
                {"authors": [], "abstract": "no title or url"},
                {
                    "title": "Good",
                    "url": "https://good",
                    "authors": [],
                },
            ]
        }
    )

    with (
        patch(
            "ai.paper_search.semantic_scholar_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.semantic_scholar_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("q")

    assert len(result.results) == 1
    assert result.results[0].url == "https://good"


def test_constructor_reads_api_key_from_environment() -> None:
    with patch("ai.paper_search.semantic_scholar_client.os.environ.get", return_value="from-env"):
        client = SemanticScholarClient()

    assert client._api_key == "from-env"


def test_constructor_does_not_raise_when_api_key_missing() -> None:
    """Unlike TavilyClient/BraveClient, a missing key is not a construction-time error --
    it's the orchestrator's job to decide whether to attempt Semantic Scholar at all
    (ADR 0013)."""
    with patch("ai.paper_search.semantic_scholar_client.os.environ.get", return_value=None):
        client = SemanticScholarClient()

    assert client._api_key is None
