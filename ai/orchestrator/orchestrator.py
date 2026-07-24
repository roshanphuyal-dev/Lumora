"""The AI Orchestration Layer (docs/AI.md#ai-architecture).

This is the *only* place feature code talks to a model provider. It receives a
`task_type` + a request, decides which provider handles it per the Routing Logic order
in `docs/AI.md#routing-logic`, and returns a normalized `AIResponse`
(`ai/orchestrator/schemas.py`). Feature code (backend services, Celery tasks, etc.)
imports `run_task` from this module and never imports a provider SDK directly
(.claude/rules/ai.md).

Phase 1 routing implemented here:
  - `TaskType.DOCUMENT_INDEX`        -> NotebookLM (Routing Logic step 1, docs/AI.md)
  - `TaskType.TEACHING_EXPLANATION`  -> Gemini      (Routing Logic step 2, docs/AI.md)

Later phases add more task types and routing branches (search fallback, OpenRouter
degraded-quality fallback, etc.) per the same table — extend `run_task`, don't scatter
routing decisions into callers.
"""

from __future__ import annotations

from ai.gemini.client import GeminiClient, GeminiError
from ai.notebooklm.client import NotebookLMClient, NotebookLMError
from ai.orchestrator.schemas import (
    AIResponse,
    DocumentIndexRequest,
    ProviderName,
    TeachingExplanationRequest,
)
from ai.orchestrator.task_types import TaskType

TaskRequest = DocumentIndexRequest | TeachingExplanationRequest


class OrchestrationError(RuntimeError):
    """Raised when a `task_type` can't be routed, or the routed provider call fails."""


async def run_task(
    task_type: TaskType,
    request: TaskRequest,
    *,
    gemini_client: GeminiClient | None = None,
    notebooklm_client: NotebookLMClient | None = None,
) -> AIResponse:
    """Route `request` to the provider `task_type` maps to and return a normalized response.

    `gemini_client`/`notebooklm_client` are optional seams for tests — feature code should
    leave them unset and let the orchestrator construct the real provider client.
    """
    if task_type is TaskType.DOCUMENT_INDEX:
        if not isinstance(request, DocumentIndexRequest):
            raise OrchestrationError("DOCUMENT_INDEX requires a DocumentIndexRequest.")
        return await _run_document_index(request, notebooklm_client)

    if task_type is TaskType.TEACHING_EXPLANATION:
        if not isinstance(request, TeachingExplanationRequest):
            raise OrchestrationError("TEACHING_EXPLANATION requires a TeachingExplanationRequest.")
        return await _run_teaching_explanation(request, gemini_client)

    raise OrchestrationError(f"No routing rule for task_type={task_type!r}.")


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


async def _run_teaching_explanation(
    request: TeachingExplanationRequest, client: GeminiClient | None
) -> AIResponse:
    try:
        text = await (client or GeminiClient()).generate_teaching_explanation(
            question=request.question, context=request.context
        )
    except GeminiError as exc:
        raise OrchestrationError(str(exc)) from exc

    return AIResponse(
        task_type=TaskType.TEACHING_EXPLANATION,
        provider=ProviderName.GEMINI,
        content=text,
        citations=request.citations,
        metadata={},
    )
