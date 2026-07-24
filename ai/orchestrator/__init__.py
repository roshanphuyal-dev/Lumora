"""AI Orchestration Layer entrypoint (docs/AI.md#ai-architecture).

Routing lives here and only here: feature code declares a `TaskType`, calls `run_task`,
and gets back a normalized `AIResponse` — it never picks a provider/model directly
(.claude/rules/ai.md). See `orchestrator.py` for the routing implementation.
"""

from ai.orchestrator.orchestrator import OrchestrationError, run_task
from ai.orchestrator.schemas import (
    AIResponse,
    Citation,
    DocumentIndexRequest,
    ProviderName,
    TeachingExplanationRequest,
)
from ai.orchestrator.task_types import TaskType

__all__ = [
    "AIResponse",
    "Citation",
    "DocumentIndexRequest",
    "OrchestrationError",
    "ProviderName",
    "TaskType",
    "TeachingExplanationRequest",
    "run_task",
]
