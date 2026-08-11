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

    # Document-grounded question against a notebook's indexed sources → NotebookLM
    # (Routing Logic step 1, docs/AI.md) — retrieval only, not teaching framing.
    NOTEBOOK_QUERY = "notebook_query"

    # Teaching, explanation, pedagogical judgment → Gemini (Routing Logic step 2, docs/AI.md).
    TEACHING_EXPLANATION = "teaching_explanation"

    # Multi-turn notebook chat -> Gemini token stream, with OpenCode Zen fallback
    # only if Gemini fails before emitting its first token.
    CHAT_RESPONSE = "chat_response"

    # Notes/study guide/cheat sheet/formula sheet generation, grounded in NotebookLM
    # retrieval -> Gemini structures the retrieved content into markdown (Routing Logic
    # step 1 + 2, docs/AI.md).
    NOTES_GENERATION = "notes_generation"

    # Mnemonics/timeline/comparison-chart generation -> Gemini structured output (JSON,
    # not markdown) grounded in NotebookLM retrieval. Kept as its own task type rather than
    # folded into NOTES_GENERATION since the output shape (and Gemini response_schema) is
    # fundamentally different from markdown.
    STRUCTURED_NOTE_GENERATION = "structured_note_generation"

    # Flashcard set generation, grounded in NotebookLM retrieval -> Gemini structures the
    # retrieved content into a JSON front/back/citation list (Routing Logic step 1 + 2).
    FLASHCARD_GENERATION = "flashcard_generation"

    # NotebookLM Studio artifact generation (audio/report/slides/infographic/mindmap/
    # data_table) -> NotebookLM only, no Gemini synthesis step and no fallback (nothing
    # else can do this). Only the generation-trigger call goes through the orchestrator;
    # the resulting poll/download steps are direct NotebookLMClient calls in the Celery
    # task (app/workers/studio_tasks.py), same precedent as ensure_remote_notebook in
    # app/workers/notebook_tasks.py -- bookkeeping/retrieval on an already-triggered job,
    # not a new "AI does something" call.
    STUDIO_ARTIFACT_CREATE = "studio_artifact_create"

    # Quiz question set generation, grounded in NotebookLM retrieval -> Gemini structures
    # the retrieved content into a JSON list of question objects across the 7 supported
    # question types (mcq/true_false/fill_blank/matching/short_answer/long_answer/
    # case_study) (Routing Logic step 1 + 2, docs/AI.md). Structured output only, same
    # no-fallback precedent as STRUCTURED_NOTE_GENERATION -- best-effort free-text-parsing
    # 7 different question shapes isn't worth the fragility. Grading (`QUIZ_GRADING`) is a
    # separate, later task type -- not implemented here.
    QUIZ_GENERATION = "quiz_generation"

    # Topic-relevant image retrieval -> Wikimedia Commons primary, Openverse fallback
    # (ADR 0010, docs/adr/0010-topic-image-retrieval.md). Pure retrieval, no LLM synthesis
    # step and no Gemini/OpenCode Zen involvement at all -- a student's topic/question text
    # (not the full answer) is looked up against a keyless/low-friction-key image search
    # provider and the raw result (image_url/attribution/license/source_url) is returned
    # as-is.
    TOPIC_IMAGE_SEARCH = "topic_image_search"

    # Free-text quiz answer grading -> Gemini structured output, one batched call per quiz
    # attempt covering every short_answer/long_answer/case_study question in it (never one
    # call per question -- .claude/rules/performance.md's no-AI-call-in-a-loop rule).
    # Objective types (mcq/true_false/fill_blank/matching) are graded deterministically in
    # plain Python with no AI call at all (Milestone 7, backend layer) and never reach this
    # task type. No fallback, same precedent as QUIZ_GENERATION/STRUCTURED_NOTE_GENERATION --
    # batched multi-question structured grading output is too fragile to best-effort-parse
    # as free text (ADR 0011).
    QUIZ_GRADING = "quiz_grading"

    # Current-events/external-fact-dependent question -> Tavily search first, Brave as an
    # optional fallback only if BRAVE_SEARCH_API_KEY is configured, then Gemini synthesizes
    # a cited student-facing answer from the normalized results (Routing Logic step 4,
    # docs/AI.md#routing-logic; ADR 0012). Never a provider "answer" mode passed straight
    # through -- pedagogical judgment and citation handling stay centralized in the
    # orchestration layer, same reasoning as NOTEBOOK_QUERY feeding TEACHING_EXPLANATION.
    INTERNET_SEARCH = "internet_search"
