"""The AI Orchestration Layer (docs/AI.md#ai-architecture).

This is the *only* place feature code talks to a model provider. It receives a
`task_type` + a request, decides which provider handles it per the Routing Logic order
in `docs/AI.md#routing-logic`, and returns a normalized `AIResponse`
(`ai/orchestrator/schemas.py`). Feature code (backend services, Celery tasks, etc.)
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
from collections.abc import AsyncIterator

from pydantic import TypeAdapter, ValidationError

from ai.gemini.client import GeminiClient, GeminiError
from ai.notebooklm.client import NotebookLMClient, NotebookLMError
from ai.opencode_zen.client import OpenCodeZenClient, OpenCodeZenError
from ai.orchestrator.schemas import (
    AIResponse,
    AIStreamChunk,
    ChatResponseRequest,
    Citation,
    DocumentIndexRequest,
    FlashcardGenerationRequest,
    FlashcardItem,
    NotebookQueryRequest,
    NotesGenerationRequest,
    ProviderName,
    StructuredNoteGenerationRequest,
    StudioArtifactCreateRequest,
    TeachingExplanationRequest,
)
from ai.orchestrator.task_types import TaskType

TaskRequest = (
    DocumentIndexRequest
    | NotebookQueryRequest
    | TeachingExplanationRequest
    | ChatResponseRequest
    | NotesGenerationRequest
    | FlashcardGenerationRequest
    | StructuredNoteGenerationRequest
    | StudioArtifactCreateRequest
)


class OrchestrationError(RuntimeError):
    """Raised when a `task_type` can't be routed, or the routed provider call fails."""


async def run_task(
    task_type: TaskType,
    request: TaskRequest,
    *,
    gemini_client: GeminiClient | None = None,
    notebooklm_client: NotebookLMClient | None = None,
    opencode_zen_client: OpenCodeZenClient | None = None,
) -> AIResponse:
    """Route `request` to the provider `task_type` maps to and return a normalized response.

    `gemini_client`/`notebooklm_client`/`opencode_zen_client` are optional seams for tests —
    feature code should leave them unset and let the orchestrator construct the real
    provider client.
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
            raise OrchestrationError("TEACHING_EXPLANATION requires a TeachingExplanationRequest.")
        return await _run_teaching_explanation(request, gemini_client, opencode_zen_client)

    if task_type is TaskType.NOTES_GENERATION:
        if not isinstance(request, NotesGenerationRequest):
            raise OrchestrationError("NOTES_GENERATION requires a NotesGenerationRequest.")
        return await _run_notes_generation(request, gemini_client, opencode_zen_client)

    if task_type is TaskType.FLASHCARD_GENERATION:
        if not isinstance(request, FlashcardGenerationRequest):
            raise OrchestrationError("FLASHCARD_GENERATION requires a FlashcardGenerationRequest.")
        return await _run_flashcard_generation(request, gemini_client, opencode_zen_client)

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

    raise OrchestrationError(f"No routing rule for task_type={task_type!r}.")


async def stream_task(
    task_type: TaskType,
    request: ChatResponseRequest,
    *,
    gemini_client: GeminiClient | None = None,
    opencode_zen_client: OpenCodeZenClient | None = None,
) -> AsyncIterator[AIStreamChunk]:
    """Route a streaming task without exposing provider clients to feature code."""
    if task_type is not TaskType.CHAT_RESPONSE or not isinstance(request, ChatResponseRequest):
        raise OrchestrationError("CHAT_RESPONSE streaming requires a ChatResponseRequest.")

    emitted = False
    try:
        async for content in (gemini_client or GeminiClient()).stream_chat_response(
            question=request.question,
            context=request.context,
            history=request.history,
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
    fallback_context = "\n\n".join(part for part in (request.history, request.context) if part)
    try:
        content = await (opencode_zen_client or OpenCodeZenClient()).generate_teaching_explanation(
            question=request.question,
            context=fallback_context,
        )
    except OpenCodeZenError as exc:
        raise OrchestrationError(f"CHAT_RESPONSE failed on every provider: {exc}") from exc
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
        citations=[Citation(source_id=c.notebooklm_source_id) for c in result.citations],
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
            question=request.question, context=request.context
        )
        return _teaching_explanation_response(request, ProviderName.GEMINI, text)
    except GeminiError as exc:
        errors.append(f"gemini: {exc}")

    try:
        text = await (opencode_zen_client or OpenCodeZenClient()).generate_teaching_explanation(
            question=request.question, context=request.context
        )
        return _teaching_explanation_response(request, ProviderName.OPENCODE_ZEN, text)
    except OpenCodeZenError as exc:
        errors.append(f"opencode_zen: {exc}")

    raise OrchestrationError("TEACHING_EXPLANATION failed on every provider: " + "; ".join(errors))


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
            text = await (opencode_zen_client or OpenCodeZenClient()).generate_teaching_explanation(
                question=framing, context=request.context
            )
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
            text = await (opencode_zen_client or OpenCodeZenClient()).generate_teaching_explanation(
                question=question, context=request.context
            )
            items = _parse_fallback_flashcards(text)
            if not items:
                raise OpenCodeZenError("OpenCode Zen returned no parseable Q:/A: pairs.")
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
