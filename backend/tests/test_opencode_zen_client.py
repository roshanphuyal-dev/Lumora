"""Unit tests for `ai/opencode_zen/client.py:OpenCodeZenClient`.

Per `.claude/rules/testing.md`: the actual OpenCode Zen HTTP call is mocked out
(`httpx.AsyncClient`), but the client's own request-building, response-parsing, and
error-normalization logic all run for real.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai.opencode_zen.client import OpenCodeZenClient, OpenCodeZenError


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


async def test_generate_teaching_explanation_returns_message_content() -> None:
    client = OpenCodeZenClient(api_key="test-key")
    response = _mock_response(
        payload={"choices": [{"message": {"content": "A derivative is a rate of change."}}]}
    )

    with patch(
        "ai.opencode_zen.client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ) as mock_client_cls:
        text = await client.generate_teaching_explanation(question="What is a derivative?")

    assert text == "A derivative is a rate of change."
    mock_client_cls.assert_called_once()


async def test_generate_teaching_explanation_sends_bearer_auth_and_model() -> None:
    client = OpenCodeZenClient(api_key="test-key")
    response = _mock_response(payload={"choices": [{"message": {"content": "ok"}}]})
    http_context = _mock_http_client(response=response)

    with patch("ai.opencode_zen.client.httpx.AsyncClient", return_value=http_context):
        await client.generate_teaching_explanation(question="q", context="c")

    http_client = http_context.__aenter__.return_value
    _, kwargs = http_client.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer test-key"}
    assert kwargs["json"]["model"]
    assert kwargs["json"]["messages"][-1]["content"].count("q") >= 1


async def test_generate_teaching_explanation_raises_on_http_error() -> None:
    client = OpenCodeZenClient(api_key="test-key")
    status_error = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=MagicMock())
    response = _mock_response(payload={}, status_error=status_error)

    with patch(
        "ai.opencode_zen.client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        with pytest.raises(OpenCodeZenError, match="rate limited"):
            await client.generate_teaching_explanation(question="q")


async def test_generate_teaching_explanation_raises_on_empty_content() -> None:
    client = OpenCodeZenClient(api_key="test-key")
    response = _mock_response(payload={"choices": []})

    with patch(
        "ai.opencode_zen.client.httpx.AsyncClient",
        return_value=_mock_http_client(response=response),
    ):
        with pytest.raises(OpenCodeZenError, match="no usable text"):
            await client.generate_teaching_explanation(question="q")


def test_constructor_raises_when_api_key_missing() -> None:
    with patch("ai.opencode_zen.client.os.environ.get", return_value=None):
        with pytest.raises(OpenCodeZenError, match="OPENCODE_ZEN_API_KEY"):
            OpenCodeZenClient()


def test_constructor_reads_api_key_from_environment() -> None:
    with patch("ai.opencode_zen.client.os.environ.get", return_value="from-env"):
        client = OpenCodeZenClient()

    assert client._api_key == "from-env"
