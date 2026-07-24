"""The `task_type` vocabulary feature code declares (docs/AI.md#routing-logic).

Feature code never picks a provider/model directly — it picks one of these and hands it
to `ai.orchestrator.run_task`. Extend this enum only as new phases actually need a new
task type; don't pre-build the full eventual roster speculatively.
"""

import enum


class TaskType(enum.StrEnum):
    """Phase 1 scope only (`docs/ROADMAP.md`): document indexing + basic teaching calls."""

    # Document-grounded / indexing → NotebookLM (Routing Logic step 1, docs/AI.md).
    DOCUMENT_INDEX = "document_index"

    # Teaching, explanation, pedagogical judgment → Gemini (Routing Logic step 2, docs/AI.md).
    TEACHING_EXPLANATION = "teaching_explanation"
