"""Unit tests for `ai/image_search/client.py:WikimediaClient`/`OpenverseClient`.

Per `.claude/rules/testing.md`: the actual Wikimedia/Openverse HTTP calls are mocked out
(`httpx.AsyncClient`), but each client's request-building, response-parsing, and
error-normalization logic all run for real. The cache layer (`ai/image_search/cache.py`) is
patched to a deterministic miss so these tests exercise the HTTP/parsing path regardless of
whether a real Redis is reachable in the test environment (`ai/image_search/cache.py`'s cache
is best-effort by design, so this isn't testing around a "real" dependency being absent).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.image_search.client import (
    OpenverseClient,
    OpenverseError,
    WikimediaClient,
    WikimediaError,
)


@pytest.fixture(autouse=True)
def _cache_miss():
    """Every test starts from a cache miss and no-ops the cache write, isolating the
    HTTP/parsing logic under test from `ai/image_search/cache.py`'s Redis dependency."""
    with (
        patch("ai.image_search.client.get_cached_result", AsyncMock(return_value=(False, None))),
        patch("ai.image_search.client.set_cached_result", AsyncMock(return_value=None)),
    ):
        yield


def _mock_http_client(
    *, get_response: MagicMock | None = None, post_response: MagicMock | None = None
) -> MagicMock:
    http_client = AsyncMock()
    if get_response is not None:
        http_client.get.return_value = get_response
    if post_response is not None:
        http_client.post.return_value = post_response
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


WIKIMEDIA_HIT_PAYLOAD = {
    "query": {
        "pages": {
            "123": {
                "imageinfo": [
                    {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/simplex.png",
                        "descriptionurl": "https://commons.wikimedia.org/wiki/File:simplex.png",
                        "extmetadata": {
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "Artist": {"value": '<a href="/wiki/User:Jane">Jane Doe</a>'},
                        },
                    }
                ]
            }
        }
    }
}


async def test_wikimedia_search_image_returns_parsed_result() -> None:
    client = WikimediaClient()
    response = _mock_response(payload=WIKIMEDIA_HIT_PAYLOAD)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        result = await client.search_image("the simplex method")

    assert result is not None
    assert result.image_url == "https://upload.wikimedia.org/wikipedia/commons/simplex.png"
    assert result.license == "CC BY-SA 4.0"
    assert result.attribution == "Jane Doe"  # HTML stripped
    assert result.source_url == "https://commons.wikimedia.org/wiki/File:simplex.png"


async def test_wikimedia_search_image_returns_none_on_empty_results() -> None:
    client = WikimediaClient()
    response = _mock_response(payload={"query": {"pages": {}}})

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        result = await client.search_image("a wildly obscure made-up topic")

    assert result is None


async def test_wikimedia_search_image_returns_none_when_license_or_attribution_missing() -> None:
    """A result missing required attribution/license fields isn't usable (ADR 0010) --
    treated as no match rather than a fabricated placeholder."""
    client = WikimediaClient()
    payload = {
        "query": {
            "pages": {
                "123": {
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/x.png",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:x.png",
                            "extmetadata": {},
                        }
                    ]
                }
            }
        }
    }
    response = _mock_response(payload=payload)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        result = await client.search_image("topic")

    assert result is None


async def test_wikimedia_search_image_raises_on_http_error() -> None:
    client = WikimediaClient()
    status_error = httpx.HTTPStatusError("boom", request=MagicMock(), response=MagicMock())
    response = _mock_response(payload={}, status_error=status_error)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        with pytest.raises(WikimediaError, match="HTTPStatusError"):
            await client.search_image("topic")


async def test_wikimedia_search_image_error_never_embeds_raw_query() -> None:
    """Errors must never leak the raw query text (docs/SECURITY.md#ai-specific-risks) --
    an `httpx.HTTPStatusError`'s `str()` embeds the request URL, which carries the query
    as a param, so the client must not interpolate `str(exc)` into its own error message.
    """
    client = WikimediaClient()
    request = httpx.Request(
        "GET", "https://commons.wikimedia.org/w/api.php?gsrsearch=super-secret-topic"
    )
    status_error = httpx.HTTPStatusError(
        "error for url super-secret-topic", request=request, response=MagicMock()
    )
    response = _mock_response(payload={}, status_error=status_error)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        with pytest.raises(WikimediaError) as exc_info:
            await client.search_image("super-secret-topic")

    assert "super-secret-topic" not in str(exc_info.value)


OPENVERSE_HIT_PAYLOAD = {
    "results": [
        {
            "url": "https://images.openverse.org/simplex.jpg",
            "foreign_landing_url": "https://flickr.com/photos/x/simplex",
            "attribution": "'Simplex' by Jane Doe is licensed under CC-BY 4.0.",
            "license": "cc-by",
            "license_version": "4.0",
        }
    ]
}


async def test_openverse_search_image_returns_parsed_result() -> None:
    client = OpenverseClient()
    response = _mock_response(payload=OPENVERSE_HIT_PAYLOAD)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        result = await client.search_image("the simplex method")

    assert result is not None
    assert result.image_url == "https://images.openverse.org/simplex.jpg"
    assert result.license == "CC-BY 4.0"
    assert result.attribution == "'Simplex' by Jane Doe is licensed under CC-BY 4.0."
    assert result.source_url == "https://flickr.com/photos/x/simplex"


async def test_openverse_search_image_returns_none_on_empty_results() -> None:
    client = OpenverseClient()
    response = _mock_response(payload={"results": []})

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        result = await client.search_image("a wildly obscure made-up topic")

    assert result is None


async def test_openverse_search_image_raises_on_http_error() -> None:
    client = OpenverseClient()
    status_error = httpx.HTTPStatusError("boom", request=MagicMock(), response=MagicMock())
    response = _mock_response(payload={}, status_error=status_error)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        return_value=_mock_http_client(get_response=response),
    ):
        with pytest.raises(OpenverseError, match="HTTPStatusError"):
            await client.search_image("topic")


async def test_openverse_search_image_works_anonymously_without_credentials() -> None:
    """No `OPENVERSE_CLIENT_ID`/`OPENVERSE_CLIENT_SECRET` set -> no token request is made,
    the search still succeeds anonymously (ADR 0010: Openverse's keyless tier is sufficient
    for this MVP fallback)."""
    client = OpenverseClient(client_id=None, client_secret=None)
    response = _mock_response(payload=OPENVERSE_HIT_PAYLOAD)
    http_context = _mock_http_client(get_response=response)

    with patch("ai.image_search.client.httpx.AsyncClient", return_value=http_context):
        result = await client.search_image("topic")

    assert result is not None
    http_client = http_context.__aenter__.return_value
    _, kwargs = http_client.get.call_args
    assert "Authorization" not in kwargs["headers"]


async def test_openverse_search_image_sends_bearer_token_when_credentials_configured() -> None:
    client = OpenverseClient(client_id="id", client_secret="secret")
    token_response = _mock_response(payload={"access_token": "tok-123"})
    search_response = _mock_response(payload=OPENVERSE_HIT_PAYLOAD)

    # Two separate `httpx.AsyncClient()` context managers are opened: one for the token
    # exchange (POST), one for the actual search (GET).
    token_context = _mock_http_client(post_response=token_response)
    search_context = _mock_http_client(get_response=search_response)

    with patch(
        "ai.image_search.client.httpx.AsyncClient",
        side_effect=[token_context, search_context],
    ):
        result = await client.search_image("topic")

    assert result is not None
    search_http_client = search_context.__aenter__.return_value
    _, kwargs = search_http_client.get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"
