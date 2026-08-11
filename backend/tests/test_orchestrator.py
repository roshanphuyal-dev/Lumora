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
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from ai.gemini.client import GeminiClient, GeminiError
from ai.image_search.client import (
    OpenverseClient,
    OpenverseError,
    WikimediaClient,
    WikimediaError,
)
from ai.internet_search.brave_client import BraveClient, BraveError
from ai.internet_search.schemas import InternetSearchItem, InternetSearchResult, SearchProvider
from ai.internet_search.tavily_client import TavilyClient, TavilyError
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
    ASSERTION_REASON_OPTIONS,
    AIResponse,
    Citation,
    DocumentIndexRequest,
    GradingItem,
    InternetSearchRequest,
    NotebookQueryRequest,
    ProviderName,
    QuestionItem,
    QuizGenerationRequest,
    QuizGradingRequest,
    TeachingExplanationRequest,
    TopicImageResult,
    TopicImageSearchRequest,
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
                "topic": "cell-organelles",
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


def _assertion_reason_item_json(
    *, options: list[str] | None = None, correct_answer: str | None = None
) -> str:
    """One `assertion_reason` `QuestionItem` as Gemini would return it. Defaults to a
    valid item (canonical `ASSERTION_REASON_OPTIONS`, `correct_answer` matching the first
    option) -- callers override `options`/`correct_answer` to construct invalid variants.
    """
    return json.dumps(
        [
            {
                "question_type": "assertion_reason",
                "prompt": "Assess the assertion and reason.",
                "assertion": "Mitochondria produce ATP.",
                "reason": "Mitochondria have their own DNA.",
                "options": list(ASSERTION_REASON_OPTIONS) if options is None else options,
                "correct_answer": ASSERTION_REASON_OPTIONS[0]
                if correct_answer is None
                else correct_answer,
                "difficulty": "hard",
                "topic": "cell-respiration",
            }
        ]
    )


async def test_quiz_generation_accepts_valid_assertion_reason_item() -> None:
    """A valid `assertion_reason` item -- canonical options, `correct_answer` one of
    them -- passes the orchestrator's `_validate_assertion_reason_items` check and is
    returned normally."""
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.return_value = _assertion_reason_item_json()

    response = await run_task(
        TaskType.QUIZ_GENERATION, _quiz_generation_request(), gemini_client=mock_client
    )

    items_adapter = TypeAdapter(list[QuestionItem])
    items = items_adapter.validate_json(response.content)
    assert items[0].question_type == "assertion_reason"
    assert items[0].options == list(ASSERTION_REASON_OPTIONS)
    assert items[0].correct_answer == ASSERTION_REASON_OPTIONS[0]


async def test_quiz_generation_rejects_assertion_reason_correct_answer_not_in_options() -> None:
    """`correct_answer` must be one of `options` -- otherwise the question is
    ungradeable-correct (the frontend only ever submits back an option string,
    `_grade_objective` exact-matches against `correct_answer`)."""
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.return_value = _assertion_reason_item_json(
        correct_answer="Neither assertion nor reason is addressed."
    )

    with pytest.raises(OrchestrationError, match="correct_answer isn't one of its options"):
        await run_task(
            TaskType.QUIZ_GENERATION, _quiz_generation_request(), gemini_client=mock_client
        )


async def test_quiz_generation_rejects_assertion_reason_wrong_option_count() -> None:
    """`options` must be exactly the 4 canonical strings -- a truncated/extended set (even
    if every present string is otherwise canonical) doesn't match the frontend's rendered
    choices and must be rejected."""
    mock_client = AsyncMock(spec=GeminiClient)
    mock_client.generate_quiz.return_value = _assertion_reason_item_json(
        options=list(ASSERTION_REASON_OPTIONS[:3])
    )

    with pytest.raises(OrchestrationError, match="canonical 4-option set"):
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


# ---------------------------------------------------------------------------
# TOPIC_IMAGE_SEARCH (ADR 0010) -- Wikimedia primary, Openverse fallback, no LLM
# synthesis step at all.
# ---------------------------------------------------------------------------


def _topic_image_search_request() -> TopicImageSearchRequest:
    return TopicImageSearchRequest(query="the simplex method")


def _topic_image_result() -> TopicImageResult:
    return TopicImageResult(
        image_url="https://upload.wikimedia.org/wikipedia/commons/simplex.png",
        attribution="Jane Doe",
        license="CC BY-SA 4.0",
        source_url="https://commons.wikimedia.org/wiki/File:simplex.png",
    )


async def test_topic_image_search_routes_to_wikimedia_when_found() -> None:
    wikimedia_mock = AsyncMock(spec=WikimediaClient)
    wikimedia_mock.search_image.return_value = _topic_image_result()
    openverse_mock = AsyncMock(spec=OpenverseClient)

    request = _topic_image_search_request()
    response = await run_task(
        TaskType.TOPIC_IMAGE_SEARCH,
        request,
        wikimedia_client=wikimedia_mock,
        openverse_client=openverse_mock,
    )

    wikimedia_mock.search_image.assert_awaited_once_with(request.query)
    openverse_mock.search_image.assert_not_awaited()
    assert response.task_type == TaskType.TOPIC_IMAGE_SEARCH
    assert response.provider == ProviderName.WIKIMEDIA
    assert response.metadata == {"found": "true"}
    assert json.loads(response.content) == _topic_image_result().model_dump()


async def test_topic_image_search_falls_back_to_openverse_when_wikimedia_errors() -> None:
    wikimedia_mock = AsyncMock(spec=WikimediaClient)
    wikimedia_mock.search_image.side_effect = WikimediaError("commons unreachable")
    openverse_mock = AsyncMock(spec=OpenverseClient)
    openverse_mock.search_image.return_value = _topic_image_result()

    request = _topic_image_search_request()
    response = await run_task(
        TaskType.TOPIC_IMAGE_SEARCH,
        request,
        wikimedia_client=wikimedia_mock,
        openverse_client=openverse_mock,
    )

    openverse_mock.search_image.assert_awaited_once_with(request.query)
    assert response.provider == ProviderName.OPENVERSE
    assert response.metadata == {"found": "true"}
    assert json.loads(response.content) == _topic_image_result().model_dump()


async def test_topic_image_search_raises_when_both_providers_fail() -> None:
    wikimedia_mock = AsyncMock(spec=WikimediaClient)
    wikimedia_mock.search_image.side_effect = WikimediaError("commons unreachable")
    openverse_mock = AsyncMock(spec=OpenverseClient)
    openverse_mock.search_image.side_effect = OpenverseError("openverse unreachable")

    with pytest.raises(OrchestrationError, match="commons unreachable") as exc_info:
        await run_task(
            TaskType.TOPIC_IMAGE_SEARCH,
            _topic_image_search_request(),
            wikimedia_client=wikimedia_mock,
            openverse_client=openverse_mock,
        )

    assert "openverse unreachable" in str(exc_info.value)


async def test_topic_image_search_returns_not_found_when_neither_has_a_match() -> None:
    """Both providers respond successfully but find nothing -- a real outcome (ADR 0010's
    Tradeoffs section), not an error: no `OrchestrationError`, distinguished from a hit via
    `metadata["found"]`.
    """
    wikimedia_mock = AsyncMock(spec=WikimediaClient)
    wikimedia_mock.search_image.return_value = None
    openverse_mock = AsyncMock(spec=OpenverseClient)
    openverse_mock.search_image.return_value = None

    response = await run_task(
        TaskType.TOPIC_IMAGE_SEARCH,
        _topic_image_search_request(),
        wikimedia_client=wikimedia_mock,
        openverse_client=openverse_mock,
    )

    assert response.task_type == TaskType.TOPIC_IMAGE_SEARCH
    assert response.metadata == {"found": "false"}
    assert response.content == ""


async def test_topic_image_search_not_found_when_wikimedia_errors_openverse_has_no_match() -> None:
    """One provider erroring isn't "both fail" -- the other provider's definitive "no
    match" still yields the not-found contract, not a hard failure."""
    wikimedia_mock = AsyncMock(spec=WikimediaClient)
    wikimedia_mock.search_image.side_effect = WikimediaError("commons unreachable")
    openverse_mock = AsyncMock(spec=OpenverseClient)
    openverse_mock.search_image.return_value = None

    response = await run_task(
        TaskType.TOPIC_IMAGE_SEARCH,
        _topic_image_search_request(),
        wikimedia_client=wikimedia_mock,
        openverse_client=openverse_mock,
    )

    assert response.metadata == {"found": "false"}


async def test_topic_image_search_rejects_mismatched_request_type() -> None:
    wikimedia_mock = AsyncMock(spec=WikimediaClient)

    with pytest.raises(OrchestrationError, match="TopicImageSearchRequest"):
        await run_task(
            TaskType.TOPIC_IMAGE_SEARCH,
            _teaching_explanation_request(),
            wikimedia_client=wikimedia_mock,
        )

    wikimedia_mock.search_image.assert_not_awaited()


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


# ---------------------------------------------------------------------------
# INTERNET_SEARCH (ADR 0012) -- Tavily primary, Brave optional fallback, Gemini synthesis.
# ---------------------------------------------------------------------------


def _internet_search_request() -> InternetSearchRequest:
    return InternetSearchRequest(query="latest news on fusion energy", max_results=3)


def _search_result(provider: SearchProvider) -> InternetSearchResult:
    return InternetSearchResult(
        query="latest news on fusion energy",
        normalized_query="latest news on fusion energy",
        provider=provider,
        results=(
            InternetSearchItem(
                title="Fusion breakthrough",
                url="https://example.com/fusion",
                snippet="Scientists announced a new fusion milestone.",
            ),
        ),
        fetched_at=datetime.now(UTC),
    )


def _bypassed_internet_search_cache(*, cached_result: InternetSearchResult | None = None):
    """Patch the orchestrator's cache seam so INTERNET_SEARCH tests don't depend on a real
    Redis instance being reachable -- `ai/internet_search/cache.py` is unit-tested
    separately (`backend/tests/test_internet_search_cache.py`)."""
    return (
        patch(
            "ai.orchestrator.orchestrator.get_cached_search_result",
            AsyncMock(return_value=cached_result),
        ),
        patch(
            "ai.orchestrator.orchestrator.set_cached_search_result", AsyncMock(return_value=None)
        ),
    )


async def test_internet_search_routes_to_tavily_then_gemini_synthesizes() -> None:
    tavily_mock = AsyncMock(spec=TavilyClient)
    tavily_mock.search.return_value = _search_result(SearchProvider.TAVILY)
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_internet_search_synthesis.return_value = (
        "Fusion energy has seen a breakthrough (source: https://example.com/fusion)."
    )

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache()
    with get_cache_patch, set_cache_patch as set_cache_mock:
        response = await run_task(
            TaskType.INTERNET_SEARCH,
            request,
            tavily_client=tavily_mock,
            gemini_client=gemini_mock,
        )

    tavily_mock.search.assert_awaited_once_with(request.query, max_results=request.max_results)
    set_cache_mock.assert_awaited_once()
    gemini_mock.generate_internet_search_synthesis.assert_awaited_once_with(
        question=request.query,
        results=[
            {
                "title": "Fusion breakthrough",
                "url": "https://example.com/fusion",
                "snippet": "Scientists announced a new fusion milestone.",
            }
        ],
    )
    assert response.task_type == TaskType.INTERNET_SEARCH
    assert response.provider == ProviderName.GEMINI
    assert response.content.startswith("Fusion energy")
    assert response.citations == [
        Citation(
            source_id="https://example.com/fusion",
            excerpt="Scientists announced a new fusion milestone.",
        )
    ]
    assert response.metadata == {"search_provider": "tavily"}


async def test_internet_search_uses_cached_tavily_result_without_calling_tavily() -> None:
    tavily_mock = AsyncMock(spec=TavilyClient)
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_internet_search_synthesis.return_value = "answer"

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache(
        cached_result=_search_result(SearchProvider.TAVILY)
    )
    with get_cache_patch, set_cache_patch as set_cache_mock:
        response = await run_task(
            TaskType.INTERNET_SEARCH,
            request,
            tavily_client=tavily_mock,
            gemini_client=gemini_mock,
        )

    tavily_mock.search.assert_not_awaited()
    set_cache_mock.assert_not_awaited()  # already cached, no need to re-cache
    assert response.metadata == {"search_provider": "tavily"}


async def test_internet_search_falls_back_to_brave_when_tavily_fails(monkeypatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-test-key")
    tavily_mock = AsyncMock(spec=TavilyClient)
    tavily_mock.search.side_effect = TavilyError("quota exhausted")
    brave_mock = AsyncMock(spec=BraveClient)
    brave_mock.search.return_value = _search_result(SearchProvider.BRAVE)
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_internet_search_synthesis.return_value = "answer"

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache()
    with get_cache_patch, set_cache_patch as set_cache_mock:
        response = await run_task(
            TaskType.INTERNET_SEARCH,
            request,
            tavily_client=tavily_mock,
            brave_client=brave_mock,
            gemini_client=gemini_mock,
        )

    brave_mock.search.assert_awaited_once_with(request.query, max_results=request.max_results)
    assert response.metadata == {"search_provider": "brave"}
    # Brave results are never cached (ADR 0012) -- only Tavily's success path caches.
    set_cache_mock.assert_not_awaited()
    assert response.citations == [
        Citation(
            source_id="https://example.com/fusion",
            excerpt="Scientists announced a new fusion milestone.",
        )
    ]


async def test_internet_search_skips_brave_when_not_configured(monkeypatch) -> None:
    """No `BRAVE_SEARCH_API_KEY` -> a Tavily failure is final, never a silent Brave attempt
    (ADR 0012's Consequences)."""
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    tavily_mock = AsyncMock(spec=TavilyClient)
    tavily_mock.search.side_effect = TavilyError("quota exhausted")

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache()
    with (
        get_cache_patch,
        set_cache_patch,
        patch(
            "ai.orchestrator.orchestrator.BraveClient",
            side_effect=AssertionError(
                "BraveClient must never be constructed when BRAVE_SEARCH_API_KEY is unset"
            ),
        ),
    ):
        with pytest.raises(OrchestrationError, match="quota exhausted"):
            await run_task(TaskType.INTERNET_SEARCH, request, tavily_client=tavily_mock)


async def test_internet_search_raises_when_both_providers_fail(monkeypatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-test-key")
    tavily_mock = AsyncMock(spec=TavilyClient)
    tavily_mock.search.side_effect = TavilyError("tavily down")
    brave_mock = AsyncMock(spec=BraveClient)
    brave_mock.search.side_effect = BraveError("brave down")

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache()
    with get_cache_patch, set_cache_patch:
        with pytest.raises(OrchestrationError, match="tavily down") as exc_info:
            await run_task(
                TaskType.INTERNET_SEARCH,
                request,
                tavily_client=tavily_mock,
                brave_client=brave_mock,
            )

    assert "brave down" in str(exc_info.value)


async def test_internet_search_wraps_gemini_synthesis_error() -> None:
    tavily_mock = AsyncMock(spec=TavilyClient)
    tavily_mock.search.return_value = _search_result(SearchProvider.TAVILY)
    gemini_mock = AsyncMock(spec=GeminiClient)
    gemini_mock.generate_internet_search_synthesis.side_effect = GeminiError("synthesis failed")

    request = _internet_search_request()
    get_cache_patch, set_cache_patch = _bypassed_internet_search_cache()
    with get_cache_patch, set_cache_patch:
        with pytest.raises(OrchestrationError, match="synthesis failed"):
            await run_task(
                TaskType.INTERNET_SEARCH,
                request,
                tavily_client=tavily_mock,
                gemini_client=gemini_mock,
            )


async def test_internet_search_rejects_mismatched_request_type() -> None:
    tavily_mock = AsyncMock(spec=TavilyClient)

    with pytest.raises(OrchestrationError, match="InternetSearchRequest"):
        await run_task(
            TaskType.INTERNET_SEARCH, _teaching_explanation_request(), tavily_client=tavily_mock
        )

    tavily_mock.search.assert_not_awaited()
