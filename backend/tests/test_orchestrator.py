"""Routing-decision tests for `ai/orchestrator/orchestrator.py:run_task`.

Per `.claude/rules/ai.md` / `.claude/rules/testing.md`: the actual provider calls
(Gemini SDK, NotebookLM CLI/MCP, OpenCode Zen HTTP) are mocked out via the
`gemini_client`/`notebooklm_client`/`opencode_zen_client` test seams `run_task` exposes,
but the routing decision itself (which `task_type` goes to which provider, that a
mismatched request raises rather than silently misrouting, and the Gemini <-> OpenCode
Zen fallback order per ADR 0008) is exercised for real -- nothing about the routing
logic itself is mocked or skipped.
"""

from unittest.mock import AsyncMock

import pytest
from ai.gemini.client import GeminiClient, GeminiError
from ai.notebooklm.client import (
    DocumentIndexResult,
    NotebookLMClient,
    NotebookLMError,
    NotebookQueryResult,
    QuerySourceCitation,
)
from ai.opencode_zen.client import OpenCodeZenClient, OpenCodeZenError
from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import (
    AIResponse,
    Citation,
    DocumentIndexRequest,
    NotebookQueryRequest,
    ProviderName,
    TeachingExplanationRequest,
)
from ai.orchestrator.task_types import TaskType


def _document_index_request() -> DocumentIndexRequest:
    return DocumentIndexRequest(
        document_id="doc-1",
        notebooklm_notebook_id="nb-1",
        file_path="/tmp/notes.pdf",
    )


def _teaching_explanation_request() -> TeachingExplanationRequest:
    return TeachingExplanationRequest(
        question="What is a derivative?",
        context="A derivative measures rate of change.",
        citations=[Citation(source_id="src-1", chunk_id="chunk-1")],
    )


async def test_document_index_routes_to_notebooklm() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)
    mock_client.index_document.return_value = DocumentIndexResult(
        notebooklm_source_id="nb-source-1", status="indexed"
    )

    response = await run_task(
        TaskType.DOCUMENT_INDEX, _document_index_request(), notebooklm_client=mock_client
    )

    mock_client.index_document.assert_awaited_once_with(
        notebooklm_notebook_id="nb-1",
        file_path="/tmp/notes.pdf",
    )
    assert isinstance(response, AIResponse)
    assert response.task_type == TaskType.DOCUMENT_INDEX
    assert response.provider == ProviderName.NOTEBOOKLM
    assert response.content == "indexed"
    assert response.metadata == {"notebooklm_source_id": "nb-source-1", "document_id": "doc-1"}


async def test_teaching_explanation_routes_to_gemini() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_teaching_explanation.return_value = "A derivative is a rate of change."

    request = _teaching_explanation_request()
    response = await run_task(TaskType.TEACHING_EXPLANATION, request, gemini_client=mock_client)

    mock_client.generate_teaching_explanation.assert_awaited_once_with(
        question=request.question, context=request.context
    )
    assert response.task_type == TaskType.TEACHING_EXPLANATION
    assert response.provider == ProviderName.GEMINI
    assert response.content == "A derivative is a rate of change."
    # Citations carried through end-to-end (.claude/rules/ai.md).
    assert response.citations == request.citations


def _notebook_query_request() -> NotebookQueryRequest:
    return NotebookQueryRequest(notebooklm_notebook_id="nb-1", question="What is a mole?")


async def test_notebook_query_routes_to_notebooklm() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)
    mock_client.query_notebook.return_value = NotebookQueryResult(
        answer="A mole is 6.022e23 particles.",
        citations=[QuerySourceCitation(notebooklm_source_id="nlm-src-1", citation_number=1)],
    )

    response = await run_task(
        TaskType.NOTEBOOK_QUERY, _notebook_query_request(), notebooklm_client=mock_client
    )

    mock_client.query_notebook.assert_awaited_once_with(
        notebooklm_notebook_id="nb-1", question="What is a mole?"
    )
    assert response.task_type == TaskType.NOTEBOOK_QUERY
    assert response.provider == ProviderName.NOTEBOOKLM
    assert response.content == "A mole is 6.022e23 particles."
    assert response.citations == [Citation(source_id="nlm-src-1")]


async def test_notebook_query_rejects_mismatched_request_type() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)

    with pytest.raises(OrchestrationError, match="NotebookQueryRequest"):
        await run_task(
            TaskType.NOTEBOOK_QUERY,
            _teaching_explanation_request(),
            notebooklm_client=mock_client,
        )

    mock_client.query_notebook.assert_not_awaited()


async def test_notebook_query_wraps_notebooklm_error() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)
    mock_client.query_notebook.side_effect = NotebookLMError("not authenticated")

    with pytest.raises(OrchestrationError, match="not authenticated"):
        await run_task(
            TaskType.NOTEBOOK_QUERY, _notebook_query_request(), notebooklm_client=mock_client
        )


async def test_document_index_rejects_mismatched_request_type() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)

    with pytest.raises(OrchestrationError, match="DocumentIndexRequest"):
        await run_task(
            TaskType.DOCUMENT_INDEX,
            _teaching_explanation_request(),
            notebooklm_client=mock_client,
        )

    mock_client.index_document.assert_not_awaited()


async def test_teaching_explanation_rejects_mismatched_request_type() -> None:
    mock_client = AsyncMock(spec=GeminiClient)

    with pytest.raises(OrchestrationError, match="TeachingExplanationRequest"):
        await run_task(
            TaskType.TEACHING_EXPLANATION,
            _document_index_request(),
            gemini_client=mock_client,
        )

    mock_client.generate_teaching_explanation.assert_not_awaited()


async def test_unknown_task_type_raises_instead_of_misrouting() -> None:
    with pytest.raises(OrchestrationError, match="No routing rule"):
        await run_task("not_a_real_task_type", _document_index_request())  # type: ignore[arg-type]


async def test_document_index_wraps_notebooklm_error() -> None:
    mock_client = AsyncMock(spec=NotebookLMClient)
    mock_client.index_document.side_effect = NotebookLMError("CLI unavailable")

    with pytest.raises(OrchestrationError, match="CLI unavailable"):
        await run_task(
            TaskType.DOCUMENT_INDEX, _document_index_request(), notebooklm_client=mock_client
        )


async def test_teaching_explanation_falls_back_to_opencode_zen_on_gemini_error() -> None:
    """Gemini unavailable/rate-limited/quota-exhausted -> OpenCode Zen picks it up (ADR 0008)."""
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_teaching_explanation.side_effect = GeminiError("quota exhausted")
    opencode_zen_mock = AsyncMock(spec=OpenCodeZenClient)
    opencode_zen_mock.generate_teaching_explanation.return_value = (
        "A derivative is a rate of change."
    )

    request = _teaching_explanation_request()
    response = await run_task(
        TaskType.TEACHING_EXPLANATION,
        request,
        gemini_client=gemini_mock,
        opencode_zen_client=opencode_zen_mock,
    )

    opencode_zen_mock.generate_teaching_explanation.assert_awaited_once_with(
        question=request.question, context=request.context
    )
    assert response.provider == ProviderName.OPENCODE_ZEN
    assert response.content == "A derivative is a rate of change."
    assert response.citations == request.citations


async def test_teaching_explanation_wraps_errors_from_both_providers() -> None:
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_teaching_explanation.side_effect = GeminiError("empty response")
    opencode_zen_mock = AsyncMock(spec=OpenCodeZenClient)
    opencode_zen_mock.generate_teaching_explanation.side_effect = OpenCodeZenError("no usable text")

    with pytest.raises(OrchestrationError, match="empty response") as exc_info:
        await run_task(
            TaskType.TEACHING_EXPLANATION,
            _teaching_explanation_request(),
            gemini_client=gemini_mock,
            opencode_zen_client=opencode_zen_mock,
        )

    assert "no usable text" in str(exc_info.value)
