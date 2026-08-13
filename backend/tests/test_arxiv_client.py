"""Unit tests for `ai/paper_search/arxiv_client.py:ArxivClient`.

Per `.claude/rules/testing.md`: the actual arXiv HTTP call is mocked out
(`httpx.AsyncClient`, same pattern as `backend/tests/test_tavily_client.py`), but the
client's own request-building, Atom-XML-parsing, and error-normalization logic all run for
real. `asyncio.sleep` is patched in every test that calls `.search()` so the 1-req/3s rate
limiter (`ai/paper_search/arxiv_client.py:_fetch`) never actually slows the test suite
down -- same precedent as `backend/tests/test_generated_materials.py`'s
`patch("app.workers.studio_tasks.asyncio.sleep", new=AsyncMock())`.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.paper_search import arxiv_client as arxiv_client_module
from ai.paper_search.arxiv_client import ArxivClient, ArxivError
from ai.paper_search.schemas import PaperSearchProvider

_ATOM_ENTRY = """<entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <updated>2024-01-01T00:00:00Z</updated>
    <published>2024-01-01T00:00:00Z</published>
    <title>  Fusion Energy Breakthroughs
  in Tokamak Design </title>
    <summary>  A survey of recent fusion energy milestones
  in tokamak reactor design.  </summary>
    <author><name>Ada Researcher</name></author>
    <author><name>Grace Scientist</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1" rel="related"
      type="application/pdf"/>
    <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom">
      J. Fusion Energy 42, 100 (2024)
    </arxiv:journal_ref>
  </entry>"""


def _atom_feed(entries_xml: str = "") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query</title>
  <id>http://arxiv.org/api/query</id>
  <updated>2024-01-01T00:00:00Z</updated>
  {entries_xml}
</feed>"""


def _mock_http_client(*, response: MagicMock) -> MagicMock:
    http_client = AsyncMock()
    http_client.get.return_value = response
    context_manager = MagicMock()
    context_manager.__aenter__.return_value = http_client
    context_manager.__aexit__.return_value = False
    return context_manager


def _mock_response(*, text: str, status_error: Exception | None = None) -> MagicMock:
    response = MagicMock()
    response.text = text
    if status_error is not None:
        response.raise_for_status.side_effect = status_error
    return response


async def test_search_returns_normalized_results() -> None:
    client = ArxivClient()
    response = _mock_response(text=_atom_feed(_ATOM_ENTRY))

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("  Fusion   Energy  ", max_results=3)

    assert result.provider == PaperSearchProvider.ARXIV
    assert result.query == "  Fusion   Energy  "
    assert result.normalized_query == "fusion energy"
    assert len(result.results) == 1
    item = result.results[0]
    assert item.title == "Fusion Energy Breakthroughs in Tokamak Design"
    assert item.authors == ("Ada Researcher", "Grace Scientist")
    assert item.abstract == "A survey of recent fusion energy milestones in tokamak reactor design."
    assert item.url == "http://arxiv.org/abs/2401.00001v1"
    assert item.pdf_url == "http://arxiv.org/pdf/2401.00001v1"
    assert item.venue == "J. Fusion Energy 42, 100 (2024)"
    assert item.citation_count is None
    assert item.publication_date is not None
    assert item.publication_date.isoformat() == "2024-01-01"


async def test_search_sends_search_query_and_max_results_params() -> None:
    client = ArxivClient()
    response = _mock_response(text=_atom_feed())
    http_context = _mock_http_client(response=response)

    with (
        patch("ai.paper_search.arxiv_client.httpx.AsyncClient", return_value=http_context),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        await client.search("neural networks", max_results=7)

    http_client = http_context.__aenter__.return_value
    args, kwargs = http_client.get.call_args
    assert args[0] == "https://export.arxiv.org/api/query"
    assert kwargs["params"] == {"search_query": "all:neural networks", "max_results": 7}


async def test_search_returns_successful_empty_result_not_an_error() -> None:
    """ADR 0013: a well-formed zero-entry response is a *successful* empty result, not an
    `ArxivError` -- this is the empty-result-semantics contract
    `ai/orchestrator/orchestrator.py:_run_paper_search` depends on to avoid a spurious
    Semantic Scholar fallback attempt."""
    client = ArxivClient()
    response = _mock_response(text=_atom_feed())

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("a very obscure niche topic")

    assert result.results == ()
    assert result.provider == PaperSearchProvider.ARXIV


async def test_search_skips_malformed_entries() -> None:
    """An entry missing a title is dropped rather than raising -- a partially malformed
    response still returns whatever's usable."""
    malformed_entry = """<entry>
        <id>http://arxiv.org/abs/2401.00002v1</id>
        <summary>no title here</summary>
        <author><name>Nobody</name></author>
      </entry>"""
    client = ArxivClient()
    response = _mock_response(text=_atom_feed(malformed_entry + _ATOM_ENTRY))

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.search("q")

    assert len(result.results) == 1
    assert result.results[0].url == "http://arxiv.org/abs/2401.00001v1"


async def test_search_raises_on_unparseable_response() -> None:
    client = ArxivClient()
    response = _mock_response(text="not xml at all <<<")

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(ArxivError, match="unparseable"):
            await client.search("q")


async def test_search_raises_on_rate_limit_without_leaking_query() -> None:
    client = ArxivClient()
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.headers = {"Retry-After": "30"}
    status_error = httpx.HTTPStatusError(
        "Client error for url "
        "'http://export.arxiv.org/api/query?search_query=all:super+secret+student+query'",
        request=MagicMock(),
        response=error_response,
    )
    response = _mock_response(text="", status_error=status_error)
    http_context = _mock_http_client(response=response)

    with (
        patch("ai.paper_search.arxiv_client.httpx.AsyncClient", return_value=http_context),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(ArxivError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "HTTP 429" in message
    assert "Retry-After: 30" in message


async def test_search_raises_on_connection_error_without_leaking_query() -> None:
    client = ArxivClient()
    connect_error = httpx.ConnectError(
        "Connection refused: "
        "http://export.arxiv.org/api/query?search_query=all:super+secret+student+query"
    )

    with (
        patch("ai.paper_search.arxiv_client.httpx.AsyncClient", side_effect=connect_error),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=AsyncMock()),
    ):
        with pytest.raises(ArxivError) as exc_info:
            await client.search("super secret student query")

    message = str(exc_info.value)
    assert "super secret student query" not in message
    assert "secret" not in message
    assert "ConnectError" in message


async def test_throttle_sleeps_when_called_again_before_the_interval_elapses() -> None:
    """A second `search()` call within `_MIN_REQUEST_INTERVAL_SECONDS` of the first must
    sleep before issuing its request (ADR 0013's 1-req/3s rate limit)."""
    client = ArxivClient()
    response = _mock_response(text=_atom_feed())
    sleep_mock = AsyncMock()

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            return_value=_mock_http_client(response=response),
        ),
        patch("ai.paper_search.arxiv_client.asyncio.sleep", new=sleep_mock),
    ):
        await client.search("first")
        await client.search("second")

    sleep_mock.assert_awaited()


async def test_search_holds_the_rate_limit_lock_across_the_entire_http_request() -> None:
    """arXiv's documented limit is "1 request/3s, one connection at a time" -- not just the
    interval. A second concurrent `search()` call must not open its own HTTP connection
    until the first call's request has fully completed, not merely until the first call's
    throttle sleep finishes. Releasing the rate-limit lock right after the sleep (before the
    HTTP request starts) would let a second call's request begin while a slow first request
    is still in flight, which is exactly the bug this regression test guards against.
    """
    call_order: list[str] = []
    release_first = asyncio.Event()

    async def slow_get(*args, **kwargs) -> MagicMock:
        call_order.append("first_started")
        await release_first.wait()
        call_order.append("first_finished")
        return _mock_response(text=_atom_feed())

    async def fast_get(*args, **kwargs) -> MagicMock:
        call_order.append("second_started")
        return _mock_response(text=_atom_feed())

    def _context(get_side_effect) -> MagicMock:
        http_client = AsyncMock()
        http_client.get.side_effect = get_side_effect
        context = MagicMock()
        context.__aenter__.return_value = http_client
        context.__aexit__.return_value = False
        return context

    contexts = iter([_context(slow_get), _context(fast_get)])
    client = ArxivClient()

    with (
        patch(
            "ai.paper_search.arxiv_client.httpx.AsyncClient",
            side_effect=lambda *a, **k: next(contexts),
        ),
        # No interval to wait out here -- this test isolates the "one connection at a
        # time" guarantee from the separate 1-req/3s interval (covered by the test above).
        patch.object(arxiv_client_module, "_MIN_REQUEST_INTERVAL_SECONDS", 0.0),
        patch.object(arxiv_client_module, "_last_request_monotonic", None),
    ):
        task1 = asyncio.create_task(client.search("first"))
        for _ in range(3):
            await asyncio.sleep(0)  # let task1 acquire the lock and reach the blocking get()

        task2 = asyncio.create_task(client.search("second"))
        for _ in range(3):
            await asyncio.sleep(0)  # let task2 try to acquire the (still-held) lock

        # task2 must be blocked on the lock, not already inside its own HTTP request.
        assert call_order == ["first_started"]

        release_first.set()
        await task1
        await task2

    assert call_order == ["first_started", "first_finished", "second_started"]
