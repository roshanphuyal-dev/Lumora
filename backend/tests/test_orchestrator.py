"""Routing-decision tests for `ai/orchestrator/orchestrator.py:run_task`.

Per `.claude/rules/ai.md` / `.claude/rules/testing.md`: the actual provider calls
(Gemini SDK, NotebookLM CLI/MCP, OpenCode Zen HTTP) are mocked out via the
`gemini_client`/`notebooklm_client`/`opencode_zen_client` test seams `run_task` exposes,
but the routing decision itself (which `task_type` goes to which provider, that a
mismatched request raises rather than silently misrouting, and the Gemini <-> OpenCode
Zen fallback order per ADR 0008) is exercised for real -- nothing about the routing
logic itself is mocked or skipped.
"""

import json
from unittest.mock import AsyncMock, patch

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
    GradingItem,
    NotebookQueryRequest,
    ProviderName,
    QuestionItem,
    QuizGenerationRequest,
    QuizGradingRequest,
    TeachingExplanationRequest,
)
from ai.orchestrator.task_types import TaskType
from pydantic import TypeAdapter


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


# ---------------------------------------------------------------------------
# QUIZ_GENERATION / QUIZ_GRADING (ADR 0011) -- Gemini only, no OpenCode Zen fallback.
# ---------------------------------------------------------------------------


def _quiz_generation_request() -> QuizGenerationRequest:
    return QuizGenerationRequest(
        topic="Cell biology",
        context="Mitochondria produce ATP.",
        citations=[Citation(source_id="src-1", chunk_id="chunk-1")],
        question_types=["mcq"],
        count=5,
        difficulty="mixed",
    )


def _quiz_generation_items_json() -> str:
    return json.dumps(
        [
            {
                "question_type": "mcq",
                "prompt": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria"],
                "correct_answer": "Mitochondria",
                "difficulty": "easy",
                "explanation": "Mitochondria produce ATP.",
            }
        ]
    )


async def test_quiz_generation_routes_to_gemini() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.return_value = _quiz_generation_items_json()

    request = _quiz_generation_request()
    response = await run_task(TaskType.QUIZ_GENERATION, request, gemini_client=mock_client)

    mock_client.generate_quiz.assert_awaited_once_with(
        topic=request.topic,
        context=request.context,
        question_types=request.question_types,
        count=request.count,
        difficulty=request.difficulty,
    )
    assert response.task_type == TaskType.QUIZ_GENERATION
    assert response.provider == ProviderName.GEMINI
    # The orchestrator re-serializes via `QuestionItem.model_dump()` (fills in the
    # unset-field `None`s), so compare parsed items rather than raw JSON text.
    items_adapter = TypeAdapter(list[QuestionItem])
    assert items_adapter.validate_json(response.content) == items_adapter.validate_json(
        _quiz_generation_items_json()
    )
    # Citations carried through end-to-end (.claude/rules/ai.md).
    assert response.citations == request.citations


async def test_quiz_generation_rejects_mismatched_request_type() -> None:
    mock_client = AsyncMock(spec=GeminiClient)

    with pytest.raises(OrchestrationError, match="QuizGenerationRequest"):
        await run_task(
            TaskType.QUIZ_GENERATION, _teaching_explanation_request(), gemini_client=mock_client
        )

    mock_client.generate_quiz.assert_not_awaited()


async def test_quiz_generation_wraps_gemini_error() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.side_effect = GeminiError("quota exhausted")

    with pytest.raises(OrchestrationError, match="quota exhausted"):
        await run_task(
            TaskType.QUIZ_GENERATION, _quiz_generation_request(), gemini_client=mock_client
        )


async def test_quiz_generation_wraps_invalid_json_as_orchestration_error() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.return_value = "not a valid question list"

    with pytest.raises(OrchestrationError, match="invalid quiz"):
        await run_task(
            TaskType.QUIZ_GENERATION, _quiz_generation_request(), gemini_client=mock_client
        )


async def test_quiz_generation_never_falls_back_to_opencode_zen_on_gemini_failure() -> None:
    """No fallback exists for QUIZ_GENERATION (ADR 0011/docs/AI.md) -- confirm
    OpenCodeZenClient is never even instantiated on a Gemini failure, not just that the
    final error message happens to mention Gemini."""
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.side_effect = GeminiError("provider unavailable")

    with patch(
        "ai.orchestrator.orchestrator.OpenCodeZenClient",
        side_effect=AssertionError(
            "OpenCodeZenClient must never be constructed for QUIZ_GENERATION"
        ),
    ):
        with pytest.raises(OrchestrationError, match="provider unavailable"):
            await run_task(
                TaskType.QUIZ_GENERATION, _quiz_generation_request(), gemini_client=mock_client
            )


def _quiz_grading_request() -> QuizGradingRequest:
    return QuizGradingRequest(
        items=[
            GradingItem(
                question_id="q-1",
                question_type="short_answer",
                prompt="Explain photosynthesis.",
                reference_answer="Plants convert light into chemical energy.",
                student_answer="Plants use sunlight to make food.",
            )
        ]
    )


def _quiz_grading_results_json() -> str:
    return json.dumps(
        [
            {
                "question_id": "q-1",
                "score": 0.8,
                "is_correct": True,
                "feedback": "Good, but missing the ATP synthesis detail.",
                "topic_tag": "photosynthesis",
            }
        ]
    )


async def test_quiz_grading_routes_to_gemini() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.grade_quiz_answers.return_value = _quiz_grading_results_json()

    request = _quiz_grading_request()
    response = await run_task(TaskType.QUIZ_GRADING, request, gemini_client=mock_client)

    mock_client.grade_quiz_answers.assert_awaited_once_with(
        items=[
            {
                "question_id": "q-1",
                "question_type": "short_answer",
                "prompt": "Explain photosynthesis.",
                "reference_answer": "Plants convert light into chemical energy.",
                "student_answer": "Plants use sunlight to make food.",
            }
        ]
    )
    assert response.task_type == TaskType.QUIZ_GRADING
    assert response.provider == ProviderName.GEMINI
    assert json.loads(response.content) == json.loads(_quiz_grading_results_json())


async def test_quiz_grading_short_circuits_on_empty_items_without_calling_gemini() -> None:
    mock_client = AsyncMock(spec=GeminiClient)

    response = await run_task(
        TaskType.QUIZ_GRADING, QuizGradingRequest(items=[]), gemini_client=mock_client
    )

    mock_client.grade_quiz_answers.assert_not_awaited()
    assert response.content == "[]"
    assert response.provider == ProviderName.GEMINI


async def test_quiz_grading_rejects_mismatched_request_type() -> None:
    mock_client = AsyncMock(spec=GeminiClient)

    with pytest.raises(OrchestrationError, match="QuizGradingRequest"):
        await run_task(
            TaskType.QUIZ_GRADING, _teaching_explanation_request(), gemini_client=mock_client
        )

    mock_client.grade_quiz_answers.assert_not_awaited()


async def test_quiz_grading_wraps_gemini_error() -> None:
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.grade_quiz_answers.side_effect = GeminiError("quota exhausted")

    with pytest.raises(OrchestrationError, match="quota exhausted"):
        await run_task(TaskType.QUIZ_GRADING, _quiz_grading_request(), gemini_client=mock_client)


async def test_quiz_grading_never_falls_back_to_opencode_zen_on_gemini_failure() -> None:
    """Same no-fallback guarantee as QUIZ_GENERATION -- a bad parse would silently persist
    a wrong grade as a student's score, so QUIZ_GRADING must fail hard, never degrade
    (ADR 0011)."""
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.grade_quiz_answers.side_effect = GeminiError("provider unavailable")

    with patch(
        "ai.orchestrator.orchestrator.OpenCodeZenClient",
        side_effect=AssertionError("OpenCodeZenClient must never be constructed for QUIZ_GRADING"),
    ):
        with pytest.raises(OrchestrationError, match="provider unavailable"):
            await run_task(
                TaskType.QUIZ_GRADING, _quiz_grading_request(), gemini_client=mock_client
            )
