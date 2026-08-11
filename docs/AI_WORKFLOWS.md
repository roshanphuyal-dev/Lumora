# AI Workflows

## Purpose

Documents each concrete AI pipeline end-to-end — trigger, steps, models involved, output. `docs/AI.md` explains *why* the routing works the way it does; this doc shows *the actual sequence* for each feature.

## What Belongs Here

- One section per pipeline: trigger → steps → output.
- Which docs/rules each step depends on (linked, not repeated).

## What Never Belongs Here

- Routing rationale (`AI.md`).
- Prompt text (`PROMPTS.md`).
- Database schema for the entities involved (`DATABASE.md`).

## Structure

### 1. Upload Document → NotebookLM → Gemini → Notes
1. User uploads file → Document Processing (parse/OCR, `docs/ARCHITECTURE.md`).
2. File added as a Source to a Notebook → NotebookLM indexes it.
3. User requests "Generate Notes" → orchestrator asks NotebookLM for relevant grounded content + citations.
4. Gemini frames the retrieved content into structured notes (per `docs/PROMPTS.md` note-generation template).
5. Notes persisted (Generated Materials table, `docs/DATABASE.md`), cached for reuse.

### 2. Upload Document → Flashcards
1–2. Same as above (document indexed in Notebook).
3. NotebookLM generates flashcard-ready Q/A pairs grounded in source chunks.
4. Gemini refines phrasing/difficulty if requested (e.g. simplify, add mnemonics).
5. Flashcards persisted with source citations.

### 3. Upload Document → Quiz
1–2. Same as above.
3. Orchestrator requests relevant chunks from NotebookLM for the target topic/scope (`TaskType.NOTEBOOK_QUERY`, same retrieval step as workflows 1/2).
4. **Implemented (generation only):** Gemini generates the requested mix of the 8 supported question types (`mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason`/`short_answer`/`long_answer`/`case_study`) via structured output (`TaskType.QUIZ_GENERATION`, `ai/orchestrator/orchestrator.py`, `docs/PROMPTS.md`'s `quiz_generation` template) — one flat JSON shape per question (`ai/orchestrator/schemas.py:QuestionItem`) discriminated by `question_type`, carrying `correct_answer` (objective types) or `reference_answer` (free-text types), a `difficulty` tag per item, a `topic` tag per item (feeds weak-topic tagging for objective types, `docs/adr/0011-quiz-evaluation-scoring-design.md`), and a per-item `citation` back to source chunks. `assertion_reason` items are additionally schema-validated post-generation (`_validate_assertion_reason_items`) against the canonical 4-option answer set before being returned. No OpenCode Zen fallback, same precedent as `STRUCTURED_NOTE_GENERATION` (`docs/AI.md#routing-logic`). "Grounded distractors" for `mcq` are instructed via the prompt, not separately verified against source chunks.
5. **Implemented:** Quiz + Questions persistence (`docs/DATABASE.md`) and backend wiring (Milestone 3, `docs/API.md`'s Quiz API). Quiz attempt/submission/grading (workflow 6 below) is separate backend wiring, also implemented (Milestone 7).

### 4. User Question → RAG → NotebookLM → Gemini (AI Chat)
1. User asks a question in a notebook-scoped chat.
2. **Implemented (partial):** if the notebook has at least one `indexed` source, the orchestrator asks NotebookLM directly (`TaskType.NOTEBOOK_QUERY`) for a grounded answer + citations across all its sources — this is NotebookLM's own retrieval, not yet the `pgvector` top-k chunk retrieval described below.
3. **Not yet implemented:** orchestrator embeds the question and retrieves top-k chunks from `pgvector` scoped to the notebook (full RAG pipeline, `docs/ROADMAP.md` Phase 4); today NotebookLM's own cross-source reasoning covers this instead.
4. Gemini synthesizes a teaching-framed answer using NotebookLM's retrieved answer as context (+ conversation history once persisted), with citations carried through. A notebook with no indexed sources yet, or a failed NotebookLM call, falls back to a plain ungrounded Gemini call.
5. **Not yet implemented:** response persisted to AI Chats; contributes to memory/personalization signal if it reveals a knowledge gap.

### 5. Internet Search → Gemini
**Implemented, end-to-end:** `TaskType.INTERNET_SEARCH` (ADR 0012, `docs/adr/0012-internet-search-integration.md`), `POST /notebooks/{id}/search` (`docs/API.md`), and a "Search the web" toggle on the Ask tab (`frontend/src/components/notebook/AskNotebookSection.tsx`).
1. Student checks "Search the web" and asks a question needing current/external information (not covered by notebook sources) — see routing step 4 in `docs/AI.md`.
2. Tavily executed first (`ai/internet_search/tavily_client.py`), read through a 10-minute Redis cache (`ai/internet_search/cache.py`) keyed on the normalized query + provider + `max_results`. On a Tavily failure, Brave (`ai/internet_search/brave_client.py`) is tried only if `BRAVE_SEARCH_API_KEY` is configured — never cached, per Brave's Search API terms (`docs/TOKEN_OPTIMIZATION.md`'s per-provider caching asymmetry). Both providers' raw responses are normalized into a provider-neutral `InternetSearchResult` (`ai/internet_search/schemas.py`) before leaving the client.
3. Gemini synthesizes an answer from the normalized results (`ai/orchestrator/orchestrator.py:_run_internet_search`, `docs/PROMPTS.md`'s `internet_search_synthesis` template), citing external sources inline by URL — a provider's own "answer" mode is never used, keeping citation handling centralized. Citations are built from each result's URL/snippet (`AIResponse.citations`), clearly distinguished from notebook-grounded citations by their `source_id` being a URL rather than a NotebookLM source id.

### 6. Quiz Submission → Evaluation → Progress Tracking
1. **Implemented:** user starts a quiz attempt (`QuizAttempt`, `backend/app/models/quiz_attempt.py`) via the Quiz Attempts API (`docs/API.md`), autosaves answers, then submits.
2. **Implemented:** on submit, the attempt's questions split by grading path (ADR 0011) — `mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason` are graded deterministically in plain Python, no AI call (`backend/app/services/quiz_attempt_service.py`). `short_answer`/`long_answer`/`case_study` questions are graded in a single batched Gemini call (`TaskType.QUIZ_GRADING`, `ai/orchestrator/orchestrator.py`, `docs/PROMPTS.md`'s `quiz_grading` template) covering every free-text question in the attempt — never one call per question (`.claude/rules/performance.md`) — dispatched via `app/workers/quiz_grading_tasks.py`; skipped entirely for all-objective quizzes. Returns one `QuestionGradeResult` per question (`score` 0.0–1.0, `is_correct`, `feedback`, `topic_tag`), matched back to its question by `question_id`. No OpenCode Zen fallback, same precedent as `QUIZ_GENERATION` (ADR 0011).
3. **Implemented:** both grading paths' results persist into `QuizAttemptAnswer` (`score`/`is_correct`/`ai_feedback`/`topic_tag`) — deterministic grading sets `topic_tag` from `Question.topic` (populated at generation time, `ai/orchestrator/schemas.py:QuestionItem.topic`), AI grading sets it directly from `QuestionGradeResult.topic_tag` — the attempt's overall `score`/`max_score` is computed, and every low-scoring `topic_tag` aggregates into `weak_topics.missed_count` (`backend/app/models/weak_topic.py`) — a running tally per `(user, notebook, topic)`, not a per-attempt snapshot (`docs/AI.md#memory--personalization`, ADR 0011).
4. **Not yet implemented:** Progress/Analytics tables updated (streak, mastery, accuracy trend, `docs/DATABASE.md`).
5. **Not yet implemented:** Personalized improvement plan/recommendations surfaced on the dashboard.

### 7. (Reserved) Study Plan Generation
<!-- TODO: document once Phase 4 adaptive study planning is implemented -->

### 8. (Reserved) Audio Overview Generation
<!-- TODO: document NotebookLM audio pipeline once implemented -->

<!-- Add new workflows above this line as features ship. Keep one numbered section per pipeline. -->
