"""Request/response schemas for the orchestration layer.

`AIResponse` is the normalized shape every `run_task` call returns, regardless of which
provider handled it — feature code should never need to branch on provider to read a
response. Citation metadata is always present (possibly empty) so it survives every
pipeline stage per `.claude/rules/ai.md`.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from ai.orchestrator.task_types import TaskType


class ProviderName(enum.StrEnum):
    """Which provider actually produced an `AIResponse`.

    Informational only (logging/debugging) — feature code should not branch on this.
    """

    NOTEBOOKLM = "notebooklm"
    GEMINI = "gemini"
    OPENCODE_ZEN = "opencode_zen"


class Citation(BaseModel):
    """A source/chunk reference backing a grounded response (.claude/rules/ai.md)."""

    source_id: str
    chunk_id: str | None = None
    excerpt: str | None = None


class AIResponse(BaseModel):
    """Normalized response shape returned by every `ai.orchestrator.run_task` call."""

    task_type: TaskType
    provider: ProviderName
    content: str
    citations: list[Citation] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentIndexRequest(BaseModel):
    """Input for `TaskType.DOCUMENT_INDEX` — one already-uploaded local file to index.

    `notebooklm_notebook_id` is the remote NotebookLM notebook to index into. Resolving
    it (creating a remote notebook on first use) is a notebook-level concern, not a
    per-document one — callers must resolve it via
    `ai.notebooklm.client.NotebookLMClient.ensure_remote_notebook` before building this
    request, not as part of `run_task`.

    `file_path` must be a local filesystem path, not raw bytes/text — see
    `ai/notebooklm/client.py:NotebookLMClient.index_document` for why (the `nlm` CLI
    uploads via `--file <path>`, it has no bytes/stdin mode). Callers holding only
    document bytes (e.g. from `FileStorage.download`) must write them to a temp file
    first.
    """

    document_id: str
    notebooklm_notebook_id: str
    file_path: str


class TeachingExplanationRequest(BaseModel):
    """Input for `TaskType.TEACHING_EXPLANATION`.

    A student question plus optional grounded context (e.g. chunks previously
    retrieved from NotebookLM).
    """

    question: str
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)
