"""The AI Orchestration Layer (docs/AI.md#ai-architecture).

This is the *only* place feature code talks to a model provider. It receives a
`task_type` + a request, decides which provider handles it per the Routing Logic order
in `docs/AI.md#routing-logic`, and returns a normalized task response (`AIResponse` for
content, `TextEmbeddingResponse` for vectors; `ai/orchestrator/schemas.py`). Feature code
(backend services, Celery tasks, etc.)
imports `run_task` from this module and never imports a provider SDK directly
(.claude/rules/ai.md).

Phase 1 routing implemented here:
  - `TaskType.DOCUMENT_INDEX`       -> NotebookLM (Routing Logic step 1, docs/AI.md)
  - `TaskType.NOTEBOOK_QUERY`       -> NotebookLM, retrieval only — Routing Logic step 1,
    docs/AI.md. Callers needing a teaching-framed answer feed the result into
    `TEACHING_EXPLANATION` as `context` themselves; this task type doesn't chain the two.
  - `TaskType.TEACHING_EXPLANATION` -> Gemini, falling back to OpenCode Zen on any Gemini
    failure (unavailable, rate-limited, daily quota exhausted) — Routing Logic step 2 + 5,
    docs/AI.md, ADR 0008.

Later phases add more task types and routing branches per the same table — extend
`run_task`, don't scatter routing decisions into callers.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

from pydantic import TypeAdapter, ValidationError

from ai.gemini.client import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
    GeminiClient,
    GeminiError,
)
from ai.image_search.client import (
    OpenverseClient,
    OpenverseError,
    WikimediaClient,
    WikimediaError,
)
from ai.internet_search.brave_client import BraveClient, BraveError
from ai.internet_search.cache import get_cached_search_result, set_cached_search_result
from ai.internet_search.schemas import InternetSearchResult, SearchProvider
from ai.internet_search.tavily_client import TavilyClient, TavilyError
from ai.notebooklm.client import NotebookLMClient, NotebookLMError
from ai.opencode_zen.client import OpenCodeZenClient, OpenCodeZenError
from ai.orchestrator.schemas import (
    ASSERTION_REASON_OPTIONS,
    AIResponse,
    AIStreamChunk,
    ChatResponseRequest,
    Citation,
    DocumentIndexRequest,
    FlashcardGenerationRequest,
    FlashcardItem,
    InternetSearchRequest,
    NotebookQueryRequest,
    NotesGenerationRequest,
    PaperSearchRequest,
    ProviderName,
    QuestionGradeResult,
    QuestionItem,
    QuizGenerationRequest,
    QuizGradingRequest,
    StructuredNoteGenerationRequest,
    StudioArtifactCreateRequest,
    TeachingExplanationRequest,
    TextEmbeddingRequest,
    TextEmbeddingResponse,
    TopicImageResult,
    TopicImageSearchRequest,
)
from ai.orchestrator.task_types import TaskType
from ai.paper_search.arxiv_client import ArxivClient, ArxivError
from ai.paper_search.cache import (
    get_cached_paper_search_result,
    set_cached_paper_search_result,
)
from ai.paper_search.schemas import PaperSearchProvider, PaperSearchResult
from ai.paper_search.semantic_scholar_client import (
    SemanticScholarClient,
    SemanticScholarError,
)

TaskRequest = (
    DocumentIndexRequest
    | NotebookQueryRequest
    | TeachingExplanationRequest
    | ChatResponseRequest
    | NotesGenerationRequest
    | FlashcardGenerationRequest
    | StructuredNoteGenerationRequest
    | StudioArtifactCreateRequest
    | QuizGenerationRequest
    | QuizGradingRequest
    | TopicImageSearchRequest
    | InternetSearchRequest
    | PaperSearchRequest
    | TextEmbeddingRequest
)

TaskResponse = AIResponse | TextEmbeddingResponse


class OrchestrationError(RuntimeError):
    """Raised when a `task_type` can't be routed, or the routed provider call fails."""


async def run_task(
    task_type: TaskType,
    request: TaskRequest,
    *,
    gemini_client: GeminiClient | None = None,
    notebooklm_client: NotebookLMClient | None = None,
    opencode_zen_client: OpenCodeZenClient | None = None,
    wikimedia_client: WikimediaClient | None = None,
    openverse_client: OpenverseClient | None = None,
    tavily_client: TavilyClient | None = None,
    brave_client: BraveClient | None = None,
    arxiv_client: ArxivClient | None = None,
    semantic_scholar_client: SemanticScholarClient | None = None,
) -> TaskResponse:
    """Route `request` to its provider and return the task's normalized response shape.

    `gemini_client`/`notebooklm_client`/`opencode_zen_client`/`wikimedia_client`/
    `openverse_client`/`tavily_client`/`brave_client`/`arxiv_client`/
    `semantic_scholar_client` are optional seams for tests — feature code should leave them
    unset and let the orchestrator construct the real provider client.
    """
    if task_type is TaskType.DOCUMENT_INDEX:
        if not isinstance(request, DocumentIndexRequest):
            raise OrchestrationError("DOCUMENT_INDEX requires a DocumentIndexRequest.")
        return await _run_document_index(request, notebooklm_client)

    if task_type is TaskType.NOTEBOOK_QUERY:
        if not isinstance(request, NotebookQueryRequest):
            raise OrchestrationError("NOTEBOOK_QUERY requires a NotebookQueryRequest.")
        return await _run_notebook_query(request, notebooklm_client)

    if task_type is TaskType.TEACHING_EXPLANATION:
        if not isinstance(request, TeachingExplanationRequest):
            raise OrchestrationError(
                "TEACHING_EXPLANATION requires a TeachingExplanationRequest."
            )
        return await _run_teaching_explanation(
            request, gemini_client, opencode_zen_client
        )

    if task_type is TaskType.NOTES_GENERATION:
        if not isinstance(request, NotesGenerationRequest):
            raise OrchestrationError(
                "NOTES_GENERATION requires a NotesGenerationRequest."
            )
        return await _run_notes_generation(request, gemini_client, opencode_zen_client)

    if task_type is TaskType.FLASHCARD_GENERATION:
        if not isinstance(request, FlashcardGenerationRequest):
            raise OrchestrationError(
                "FLASHCARD_GENERATION requires a FlashcardGenerationRequest."
            )
        return await _run_flashcard_generation(
            request, gemini_client, opencode_zen_client
        )

    if task_type is TaskType.STRUCTURED_NOTE_GENERATION:
        if not isinstance(request, StructuredNoteGenerationRequest):
            raise OrchestrationError(
                "STRUCTURED_NOTE_GENERATION requires a StructuredNoteGenerationRequest."
            )
        return await _run_structured_note_generation(request, gemini_client)

    if task_type is TaskType.STUDIO_ARTIFACT_CREATE:
        if not isinstance(request, StudioArtifactCreateRequest):
            raise OrchestrationError(
                "STUDIO_ARTIFACT_CREATE requires a StudioArtifactCreateRequest."
            )
        return await _run_studio_artifact_create(request, notebooklm_client)

    if task_type is TaskType.QUIZ_GENERATION:
        if not isinstance(request, QuizGenerationRequest):
            raise OrchestrationError(
                "QUIZ_GENERATION requires a QuizGenerationRequest."
            )
        return await _run_quiz_generation(request, gemini_client)

    if task_type is TaskType.QUIZ_GRADING:
        if not isinstance(request, QuizGradingRequest):
            raise OrchestrationError("QUIZ_GRADING requires a QuizGradingRequest.")
        return await _run_quiz_grading(request, gemini_client)

    if task_type is TaskType.TOPIC_IMAGE_SEARCH:
        if not isinstance(request, TopicImageSearchRequest):
            raise OrchestrationError(
                "TOPIC_IMAGE_SEARCH requires a TopicImageSearchRequest."
            )
        return await _run_topic_image_search(
            request, wikimedia_client, openverse_client
        )

    if task_type is TaskType.INTERNET_SEARCH:
        if not isinstance(request, InternetSearchRequest):
            raise OrchestrationError(
                "INTERNET_SEARCH requires an InternetSearchRequest."
            )
        return await _run_internet_search(
            request, tavily_client, brave_client, gemini_client
        )

    if task_type is TaskType.TEXT_EMBEDDING:
        if not isinstance(request, TextEmbeddingRequest):
            raise OrchestrationError("TEXT_EMBEDDING requires a TextEmbeddingRequest.")
        return await _run_text_embedding(request, gemini_client)

    if task_type is TaskType.PAPER_SEARCH:
        if not isinstance(request, PaperSearchRequest):
            raise OrchestrationError("PAPER_SEARCH requires a PaperSearchRequest.")
        return await _run_paper_search(
            request, arxiv_client, semantic_scholar_client, gemini_client
        )

    raise OrchestrationError(f"No routing rule for task_type={task_type!r}.")


async def _run_text_embedding(
    request: TextEmbeddingRequest, gemini_client: GeminiClient | None
) -> TextEmbeddingResponse:
    try:
        embeddings = await (gemini_client or GeminiClient()).embed_texts(
            texts=request.texts,
            purpose=request.purpose.value,
        )
    except GeminiError as exc:
        raise OrchestrationError(str(exc)) from exc

    return TextEmbeddingResponse(
        task_type=TaskType.TEXT_EMBEDDING,
        provider=ProviderName.GEMINI,
        embeddings=embeddings,
        model=EMBEDDING_MODEL_NAME,
        dimensions=EMBEDDING_DIMENSIONS,
    )


async def stream_task(
    task_type: TaskType,
    request: ChatResponseRequest,
    *,
    gemini_client: GeminiClient | None = None,
    opencode_zen_client: OpenCodeZenClient | None = None,
) -> AsyncIterator[AIStreamChunk]:
    """Route a streaming task without exposing provider clients to feature code."""
    if task_type is not TaskType.CHAT_RESPONSE or not isinstance(
        request, ChatResponseRequest
    ):
        raise OrchestrationError(
            "CHAT_RESPONSE streaming requires a ChatResponseRequest."
        )

    emitted = False
    try:
        async for content in (gemini_client or GeminiClient()).stream_chat_response(
            question=request.question,
            context=request.context,
            history=request.history,
            explanation_depth=request.explanation_depth,
            explanation_style=request.explanation_style,
        ):
            emitted = True
            yield AIStreamChunk(content=content, provider=ProviderName.GEMINI)
        if not emitted:
            raise GeminiError("Gemini returned an empty response stream.")
        return
    except GeminiError as gemini_error:
        if emitted:
            raise OrchestrationError(str(gemini_error)) from gemini_error

    # The fallback client does not expose token streaming. Yield its complete response as
    # one SSE delta rather than fabricating token boundaries after generation completes.
    fallback_context = "\n\n".join(
        part for part in (request.history, request.context) if part
    )
    try:
        content = await (
            opencode_zen_client or OpenCodeZenClient()
        ).generate_teaching_explanation(
            question=request.question,
            context=fallback_context,
            explanation_depth=request.explanation_depth,
            explanation_style=request.explanation_style,
        )
    except OpenCodeZenError as exc:
        raise OrchestrationError(
            f"CHAT_RESPONSE failed on every provider: {exc}"
        ) from exc
    yield AIStreamChunk(content=content, provider=ProviderName.OPENCODE_ZEN)


async def _run_document_index(
    request: DocumentIndexRequest, client: NotebookLMClient | None
) -> AIResponse:
    try:
        result = await (client or NotebookLMClient()).index_document(
            notebooklm_notebook_id=request.notebooklm_notebook_id,
            file_path=request.file_path,
        )
    except NotebookLMError as exc:
        raise OrchestrationError(str(exc)) from exc

    return AIResponse(
        task_type=TaskType.DOCUMENT_INDEX,
        provider=ProviderName.NOTEBOOKLM,
        content=result.status,
        citations=[],
        metadata={
            "notebooklm_source_id": result.notebooklm_source_id,
            "document_id": request.document_id,
        },
    )


async def _run_notebook_query(
    request: NotebookQueryRequest, client: NotebookLMClient | None
) -> AIResponse:
    try:
        result = await (client or NotebookLMClient()).query_notebook(
            notebooklm_notebook_id=request.notebooklm_notebook_id,
            question=request.question,
        )
    except NotebookLMError as exc:
        raise OrchestrationError(str(exc)) from exc

    return AIResponse(
        task_type=TaskType.NOTEBOOK_QUERY,
        provider=ProviderName.NOTEBOOKLM,
        content=result.answer,
        citations=[
            Citation(source_id=c.notebooklm_source_id) for c in result.citations
        ],
        metadata={},
    )


async def _run_studio_artifact_create(
    request: StudioArtifactCreateRequest, client: NotebookLMClient | None
) -> AIResponse:
    try:
        result = await (client or NotebookLMClient()).create_studio_artifact(
            notebooklm_notebook_id=request.notebooklm_notebook_id,
            artifact_type=request.artifact_type,
            options=request.options,
        )
    except NotebookLMError as exc:
        raise OrchestrationError(str(exc)) from exc

    return AIResponse(
        task_type=TaskType.STUDIO_ARTIFACT_CREATE,
        provider=ProviderName.NOTEBOOKLM,
        content=result.mind_map_json or "",
        citations=[],
        metadata={
            "notebooklm_artifact_id": result.notebooklm_artifact_id,
            "status": result.status,
        },
    )


async def _run_teaching_explanation(
    request: TeachingExplanationRequest,
    gemini_client: GeminiClient | None,
    opencode_zen_client: OpenCodeZenClient | None,
) -> AIResponse:
    """Try Gemini first, falling back to OpenCode Zen on any Gemini failure (ADR 0008).

    "Failure" isn't split by cause (network error vs rate limit vs daily quota exhausted)
    -- `GeminiClient` already normalizes all of those to `GeminiError`
    (`ai/gemini/client.py`), and any of them should trigger the same fallback. The two
    providers are tried in a fixed order here (Gemini primary, OpenCode Zen fallback) since
    that's the only routing this task type needs today; nothing about this loop assumes
    Gemini must always be primary; it's just fixed rather than provider order also being
    a per-task config, since only one task type routes through this fallback so far.
    """
    errors: list[str] = []

    try:
        text = await (gemini_client or GeminiClient()).generate_teaching_explanation(
            question=request.question,
            context=request.context,
            explanation_depth=request.explanation_depth,
            explanation_style=request.explanation_style,
        )
        return _teaching_explanation_response(request, ProviderName.GEMINI, text)
    except GeminiError as exc:
        errors.append(f"gemini: {exc}")

    try:
        text = await (
            opencode_zen_client or OpenCodeZenClient()
        ).generate_teaching_explanation(
            question=request.question,
            context=request.context,
            explanation_depth=request.explanation_depth,
            explanation_style=request.explanation_style,
        )
        return _teaching_explanation_response(request, ProviderName.OPENCODE_ZEN, text)
    except OpenCodeZenError as exc:
        errors.append(f"opencode_zen: {exc}")

    raise OrchestrationError(
        "TEACHING_EXPLANATION failed on every provider: " + "; ".join(errors)
    )


def _teaching_explanation_response(
    request: TeachingExplanationRequest, provider: ProviderName, text: str
) -> AIResponse:
    return AIResponse(
        task_type=TaskType.TEACHING_EXPLANATION,
        provider=provider,
        content=text,
        citations=request.citations,
        metadata={},
    )


async def _run_notes_generation(
    request: NotesGenerationRequest,
    gemini_client: GeminiClient | None,
    opencode_zen_client: OpenCodeZenClient | None,
) -> AIResponse:
    errors: list[str] = []
    try:
        text = await (gemini_client or GeminiClient()).generate_notes(
            material_type=request.material_type,
            topic=request.topic,
            context=request.context,
        )
        provider = ProviderName.GEMINI
    except GeminiError as exc:
        errors.append(f"gemini: {exc}")
        material = request.material_type.replace("_", " ")
        framing = f"Create a {material} in Markdown about: {request.topic}"
        try:
            text = await (
                opencode_zen_client or OpenCodeZenClient()
            ).generate_teaching_explanation(question=framing, context=request.context)
            provider = ProviderName.OPENCODE_ZEN
        except OpenCodeZenError as fallback_exc:
            errors.append(f"opencode_zen: {fallback_exc}")
            raise OrchestrationError(
                "NOTES_GENERATION failed on every provider: " + "; ".join(errors)
            ) from fallback_exc
    return AIResponse(
        task_type=TaskType.NOTES_GENERATION,
        provider=provider,
        content=text,
        citations=request.citations,
        metadata={},
    )


async def _run_structured_note_generation(
    request: StructuredNoteGenerationRequest, gemini_client: GeminiClient | None
) -> AIResponse:
    """Gemini only, no fallback.

    Unlike every other Gemini-primary task type, this one doesn't fall back to OpenCode
    Zen on failure: OpenCode Zen has no structured-output API, and best-effort-parsing
    three different free-text shapes (mnemonics/timeline items vs a comparison-chart
    table) for a rare failure path isn't worth the fragility — a clean failure (retry the
    generation) beats a garbled fallback result for structured content a UI will try to
    render as a list/table.
    """
    try:
        raw_json = await (gemini_client or GeminiClient()).generate_structured_note(
            material_type=request.material_type,
            topic=request.topic,
            context=request.context,
        )
    except GeminiError as exc:
        raise OrchestrationError(f"STRUCTURED_NOTE_GENERATION failed: {exc}") from exc

    return AIResponse(
        task_type=TaskType.STRUCTURED_NOTE_GENERATION,
        provider=ProviderName.GEMINI,
        content=raw_json,
        citations=request.citations,
        metadata={},
    )


async def _run_flashcard_generation(
    request: FlashcardGenerationRequest,
    gemini_client: GeminiClient | None,
    opencode_zen_client: OpenCodeZenClient | None,
) -> AIResponse:
    errors: list[str] = []
    try:
        raw_json = await (gemini_client or GeminiClient()).generate_flashcards(
            topic=request.topic, context=request.context, count=request.count
        )
        items = TypeAdapter(list[FlashcardItem]).validate_json(raw_json)
        provider = ProviderName.GEMINI
    except (GeminiError, ValidationError) as exc:
        errors.append(f"gemini: {exc}")
        # OpenCode Zen has no structured-output API. Its Q:/A: text is best-effort parsed;
        # this degraded-quality state is currently visible only through AIResponse.provider.
        question = (
            f"Create {request.count} flashcards about {request.topic}. Output only repeated "
            "two-line pairs in the exact form `Q: question` then `A: answer`."
        )
        try:
            text = await (
                opencode_zen_client or OpenCodeZenClient()
            ).generate_teaching_explanation(question=question, context=request.context)
            items = _parse_fallback_flashcards(text)
            if not items:
                raise OpenCodeZenError(
                    "OpenCode Zen returned no parseable Q:/A: pairs."
                )
            provider = ProviderName.OPENCODE_ZEN
        except OpenCodeZenError as fallback_exc:
            errors.append(f"opencode_zen: {fallback_exc}")
            raise OrchestrationError(
                "FLASHCARD_GENERATION failed on every provider: " + "; ".join(errors)
            ) from fallback_exc
    return AIResponse(
        task_type=TaskType.FLASHCARD_GENERATION,
        provider=provider,
        content=json.dumps([item.model_dump() for item in items]),
        citations=request.citations,
        metadata={},
    )


def _validate_assertion_reason_items(items: list[QuestionItem]) -> None:
    """Hard-fail on any `assertion_reason` item whose `options`/`correct_answer` drift from
    `ASSERTION_REASON_OPTIONS`, the canonical 4-string answer set
    (`ai/orchestrator/schemas.py`).

    Grading is exact-string match (`_grade_objective` in
    `backend/app/services/quiz_attempt_service.py`) and the frontend only ever submits back
    one of the option strings it was shown
    (`frontend/src/components/quiz/questions/AssertionReasonQuestion.tsx`) -- the prompt
    instructs Gemini to reuse the canonical strings verbatim, but that's a request, not a
    guarantee. Without this check a noncanonical/mismatched item would still satisfy
    `QuestionItem`'s schema (`options: list[str] | None`, `correct_answer: str | None` are
    unconstrained) and pass through silently, becoming ungradeable-correct once persisted --
    nobody could ever answer it right. Comparison normalizes the same way
    `_grade_objective` does (trim + casefold) so a harmless whitespace/case difference isn't
    treated as drift (.claude/rules/ai.md "validate generated output against the expected
    schema"; ADR 0011's hard-failure-over-garbled-grade precedent, extended from grading to
    generation).
    """
    canonical_normalized = {
        option.strip().casefold() for option in ASSERTION_REASON_OPTIONS
    }
    for index, item in enumerate(items):
        if item.question_type != "assertion_reason":
            continue

        options = item.options or []
        options_normalized = {option.strip().casefold() for option in options}
        if (
            len(options) != len(ASSERTION_REASON_OPTIONS)
            or options_normalized != canonical_normalized
        ):
            raise OrchestrationError(
                f"QUIZ_GENERATION returned an assertion_reason question (index {index}) "
                f"whose options don't match the canonical 4-option set: {options!r}"
            )

        correct_answer = item.correct_answer
        if (
            correct_answer is None
            or correct_answer.strip().casefold() not in canonical_normalized
        ):
            raise OrchestrationError(
                f"QUIZ_GENERATION returned an assertion_reason question (index {index}) "
                f"whose correct_answer isn't one of its options: {correct_answer!r}"
            )


async def _run_quiz_generation(
    request: QuizGenerationRequest, gemini_client: GeminiClient | None
) -> AIResponse:
    """Gemini only, no fallback -- same reasoning as `_run_structured_note_generation`.

    OpenCode Zen has no structured-output API, and best-effort-parsing free text into 8
    different question shapes (mcq/true_false/fill_blank/matching/short_answer/
    long_answer/case_study/assertion_reason) for a rare failure path isn't worth the
    fragility -- a clean failure (retry the generation) beats a garbled quiz a UI would
    try to render.
    """
    try:
        raw_json = await (gemini_client or GeminiClient()).generate_quiz(
            topic=request.topic,
            context=request.context,
            question_types=request.question_types,
            count=request.count,
            difficulty=request.difficulty,
            difficulty_mix=request.difficulty_mix,
        )
        items = TypeAdapter(list[QuestionItem]).validate_json(raw_json)
    except GeminiError as exc:
        raise OrchestrationError(f"QUIZ_GENERATION failed: {exc}") from exc
    except ValidationError as exc:
        raise OrchestrationError(
            f"QUIZ_GENERATION returned an invalid quiz: {exc}"
        ) from exc

    _validate_assertion_reason_items(items)

    if request.difficulty_mix is not None:
        actual_mix = {level: 0 for level in ("easy", "medium", "hard")}
        for item in items:
            if item.difficulty not in actual_mix:
                raise OrchestrationError(
                    f"QUIZ_GENERATION returned unsupported difficulty: {item.difficulty!r}"
                )
            actual_mix[item.difficulty] += 1
        if actual_mix != request.difficulty_mix:
            raise OrchestrationError(
                "QUIZ_GENERATION did not honor the requested adaptive difficulty mix: "
                f"expected {request.difficulty_mix!r}, got {actual_mix!r}"
            )

    return AIResponse(
        task_type=TaskType.QUIZ_GENERATION,
        provider=ProviderName.GEMINI,
        content=json.dumps([item.model_dump() for item in items]),
        citations=request.citations,
        metadata={
            "adaptation_applied": str(request.difficulty_mix is not None).lower(),
        },
    )


async def _run_quiz_grading(
    request: QuizGradingRequest, gemini_client: GeminiClient | None
) -> AIResponse:
    """Gemini only, no fallback (ADR 0011) -- same reasoning as `_run_quiz_generation`.

    OpenCode Zen has no structured-output API, and best-effort-parsing free text into a
    batched list of per-question grades (score/is_correct/feedback/topic_tag, matched back
    by `question_id`) for a rare failure path isn't worth the fragility -- a clean failure
    (retry the grading call) beats silently-wrong scores a caller would persist as a
    student's grade.
    """
    if not request.items:
        return AIResponse(
            task_type=TaskType.QUIZ_GRADING,
            provider=ProviderName.GEMINI,
            content="[]",
            citations=[],
            metadata={},
        )

    try:
        raw_json = await (gemini_client or GeminiClient()).grade_quiz_answers(
            items=[
                {
                    "question_id": item.question_id,
                    "question_type": item.question_type,
                    "prompt": item.prompt,
                    "reference_answer": item.reference_answer,
                    "student_answer": item.student_answer,
                }
                for item in request.items
            ]
        )
        results = TypeAdapter(list[QuestionGradeResult]).validate_json(raw_json)
    except GeminiError as exc:
        raise OrchestrationError(f"QUIZ_GRADING failed: {exc}") from exc
    except ValidationError as exc:
        raise OrchestrationError(
            f"QUIZ_GRADING returned an invalid result: {exc}"
        ) from exc

    return AIResponse(
        task_type=TaskType.QUIZ_GRADING,
        provider=ProviderName.GEMINI,
        content=json.dumps([result.model_dump() for result in results]),
        citations=[],
        metadata={},
    )


async def _run_topic_image_search(
    request: TopicImageSearchRequest,
    wikimedia_client: WikimediaClient | None,
    openverse_client: OpenverseClient | None,
) -> AIResponse:
    """Wikimedia primary, Openverse fallback (ADR 0010) -- pure retrieval, no Gemini/
    OpenCode Zen involvement and no synthesis step at all: `content` is the raw
    `TopicImageResult`, JSON-serialized (`json.dumps(result.model_dump())`, same precedent
    as `FLASHCARD_GENERATION`'s single-item structured result).

    Design decision -- "no good match found" vs. a hard failure (ADR 0010's Tradeoffs
    section explicitly calls the empty case out as real UI to design for, not an edge case
    to ignore): this function distinguishes the two outcomes rather than collapsing them
    into one:
      - Both providers *fail* (network/auth/parse error) -> raises `OrchestrationError`,
        same as every other task type's provider-failure case -- caller shows an error
        state ("something went wrong, try again").
      - At least one provider *responds successfully* but neither has a usable result (a
        real, expected outcome for niche/newly-coined topics, not an error) ->
        returns an `AIResponse` with `metadata={"found": "false"}` and empty `content` --
        caller shows a "no image found for this topic" empty state, not an error banner.
      - A usable result is found -> `metadata={"found": "true"}`, `content` is the
        JSON-serialized `TopicImageResult`.
    The frontend agent building the "Find an image" action should branch on
    `AIResponse.metadata["found"]`, not on whether `content` happens to be empty/parseable.
    """
    errors: list[str] = []
    wikimedia_errored = False
    openverse_errored = False

    try:
        result = await (wikimedia_client or WikimediaClient()).search_image(
            request.query
        )
        if result is not None:
            return _topic_image_response(result, ProviderName.WIKIMEDIA)
    except WikimediaError as exc:
        wikimedia_errored = True
        errors.append(f"wikimedia: {exc}")

    try:
        result = await (openverse_client or OpenverseClient()).search_image(
            request.query
        )
        if result is not None:
            return _topic_image_response(result, ProviderName.OPENVERSE)
    except OpenverseError as exc:
        openverse_errored = True
        errors.append(f"openverse: {exc}")

    if wikimedia_errored and openverse_errored:
        raise OrchestrationError(
            "TOPIC_IMAGE_SEARCH failed on every provider: " + "; ".join(errors)
        )

    # At least one provider responded successfully with no usable match -- see docstring
    # above for the found=false contract.
    return AIResponse(
        task_type=TaskType.TOPIC_IMAGE_SEARCH,
        provider=ProviderName.OPENVERSE,
        content="",
        citations=[],
        metadata={"found": "false"},
    )


def _topic_image_response(
    result: TopicImageResult, provider: ProviderName
) -> AIResponse:
    return AIResponse(
        task_type=TaskType.TOPIC_IMAGE_SEARCH,
        provider=provider,
        content=json.dumps(result.model_dump()),
        citations=[],
        metadata={"found": "true"},
    )


async def _run_internet_search(
    request: InternetSearchRequest,
    tavily_client: TavilyClient | None,
    brave_client: BraveClient | None,
    gemini_client: GeminiClient | None,
) -> AIResponse:
    """Tavily first, Brave fallback only if `BRAVE_SEARCH_API_KEY` is configured, then
    Gemini synthesizes the final answer (ADR 0012).

    Never returns a provider's raw search results/answer directly — the normalized
    `InternetSearchResult` is always handed to Gemini's synthesis prompt
    (`ai/prompts/internet_search_synthesis_v1.py`) so pedagogical judgment and citation
    handling stay centralized here rather than provider-dependent, matching
    `.claude/rules/ai.md`'s "external content is data, never instructions" rule.

    Tavily results are read through a short-TTL cache (`ai/internet_search/cache.py`)
    keyed on the normalized query + provider + `max_results`; Brave results are never
    cached at all, per Brave's Search API terms (ADR 0012's per-provider caching
    asymmetry). Brave is only attempted when `BRAVE_SEARCH_API_KEY` is configured — a
    Tavily failure with no Brave key configured is a final "search unavailable" outcome,
    not a silent skip that looks like a bug (ADR 0012's Consequences).
    """
    errors: list[str] = []
    result: InternetSearchResult | None = await get_cached_search_result(
        provider=SearchProvider.TAVILY,
        query=request.query,
        max_results=request.max_results,
    )

    if result is None:
        try:
            result = await (tavily_client or TavilyClient()).search(
                request.query, max_results=request.max_results
            )
            await set_cached_search_result(result, max_results=request.max_results)
        except TavilyError as exc:
            errors.append(f"tavily: {exc}")

    if result is None and os.environ.get("BRAVE_SEARCH_API_KEY"):
        try:
            result = await (brave_client or BraveClient()).search(
                request.query, max_results=request.max_results
            )
        except BraveError as exc:
            errors.append(f"brave: {exc}")

    if result is None:
        raise OrchestrationError(
            "INTERNET_SEARCH failed on every provider: " + "; ".join(errors)
        )

    try:
        answer = await (
            gemini_client or GeminiClient()
        ).generate_internet_search_synthesis(
            question=request.query,
            results=[
                {"title": item.title, "url": item.url, "snippet": item.snippet}
                for item in result.results
            ],
        )
    except GeminiError as exc:
        raise OrchestrationError(f"INTERNET_SEARCH synthesis failed: {exc}") from exc

    return AIResponse(
        task_type=TaskType.INTERNET_SEARCH,
        provider=ProviderName.GEMINI,
        content=answer,
        citations=[
            Citation(source_id=item.url, excerpt=item.snippet)
            for item in result.results
        ],
        metadata={"search_provider": result.provider.value},
    )


async def _run_paper_search(
    request: PaperSearchRequest,
    arxiv_client: ArxivClient | None,
    semantic_scholar_client: SemanticScholarClient | None,
    gemini_client: GeminiClient | None,
) -> AIResponse:
    """arXiv first, Semantic Scholar fallback only if `SEMANTIC_SCHOLAR_API_KEY` is
    configured, then Gemini synthesizes the final answer (ADR 0013).

    Identical shape to `_run_internet_search` -- see that function's docstring for the
    shared reasoning (never returns a provider's raw paper metadata directly; the
    normalized `PaperSearchResult` is always handed to Gemini's synthesis prompt,
    `ai/prompts/paper_search_synthesis_v1.py`, so pedagogical judgment and citation
    handling stay centralized here rather than provider-dependent).

    Empty-result semantics deliberately match `_run_internet_search` exactly (ADR 0013): an
    arXiv call that succeeds with zero papers found is not treated as a failure and does
    not by itself trigger the Semantic Scholar fallback -- only a raised `ArxivError` does.
    The empty `PaperSearchResult` still flows straight into Gemini synthesis like any other
    success, same as a non-empty one.

    arXiv results are read through a 24h cache (`ai/paper_search/cache.py`) keyed on the
    normalized query + provider + `max_results`, per arXiv's own once-per-day-is-enough
    caching guidance; Semantic Scholar results are never cached at all, per its license
    terms (ADR 0013's per-provider caching asymmetry). Semantic Scholar is only attempted
    when `SEMANTIC_SCHOLAR_API_KEY` is configured -- an arXiv failure with no Semantic
    Scholar key configured is a final "search unavailable" outcome, not a silent skip
    (ADR 0013's Consequences, mirroring ADR 0012's for Brave).
    """
    errors: list[str] = []
    result: PaperSearchResult | None = await get_cached_paper_search_result(
        provider=PaperSearchProvider.ARXIV,
        query=request.query,
        max_results=request.max_results,
    )

    if result is None:
        try:
            result = await (arxiv_client or ArxivClient()).search(
                request.query, max_results=request.max_results
            )
            await set_cached_paper_search_result(
                result, max_results=request.max_results
            )
        except ArxivError as exc:
            errors.append(f"arxiv: {exc}")

    if result is None and os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        try:
            result = await (semantic_scholar_client or SemanticScholarClient()).search(
                request.query, max_results=request.max_results
            )
        except SemanticScholarError as exc:
            errors.append(f"semantic_scholar: {exc}")

    if result is None:
        raise OrchestrationError(
            "PAPER_SEARCH failed on every provider: " + "; ".join(errors)
        )

    try:
        answer = await (
            gemini_client or GeminiClient()
        ).generate_paper_search_synthesis(
            question=request.query,
            results=[
                {
                    "title": item.title,
                    "authors": list(item.authors),
                    "venue": item.venue,
                    "abstract": item.abstract,
                    "url": item.url,
                }
                for item in result.results
            ],
        )
    except GeminiError as exc:
        raise OrchestrationError(f"PAPER_SEARCH synthesis failed: {exc}") from exc

    return AIResponse(
        task_type=TaskType.PAPER_SEARCH,
        provider=ProviderName.GEMINI,
        content=answer,
        citations=[
            Citation(source_id=item.url, excerpt=item.abstract)
            for item in result.results
        ],
        metadata={"search_provider": result.provider.value},
    )


def _parse_fallback_flashcards(text: str) -> list[FlashcardItem]:
    items: list[FlashcardItem] = []
    front: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Q:"):
            front = line[2:].strip()
        elif line.startswith("A:") and front:
            back = line[2:].strip()
            if back:
                items.append(FlashcardItem(front=front, back=back))
            front = None
    return items
