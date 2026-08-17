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
3. User requests "Generate Notes" → NotebookLM is queried first for relevant grounded content + citations. If it is unavailable or returns inadequate grounding and `RAG_ENABLED` is on, owner-scoped local hybrid retrieval supplies verified context and citations; if neither path succeeds, generation remains explicitly ungrounded.
4. Gemini frames the retrieved content into structured notes (per `docs/PROMPTS.md` note-generation template).
5. Notes persisted (Generated Materials table, `docs/DATABASE.md`), cached for reuse.

### 2. Upload Document → Flashcards
1–2. Same as above (document indexed in Notebook).
3. NotebookLM supplies grounded source context first. If it is unavailable or inadequate and `RAG_ENABLED` is on, owner-scoped local hybrid retrieval supplies verified context and citations; if neither path succeeds, generation remains explicitly ungrounded.
4. Gemini refines phrasing/difficulty if requested (e.g. simplify, add mnemonics).
5. Flashcards persisted with source citations.

### 3. Upload Document → Quiz
1–2. Same as above.
3. The generation grounding service requests relevant context from NotebookLM first; when it is unavailable or inadequate and `RAG_ENABLED` is on, owner-scoped local hybrid retrieval supplies verified context and citations. If the quiz was created with `include_web_search=true` (`backend/app/models/quiz.py`), a second, independent `TaskType.INTERNET_SEARCH` retrieval also runs and appends current web information; a search failure never fails generation (`app/workers/quiz_tasks.py`).
4. **Implemented (generation only):** Gemini generates the requested mix of the 8 supported question types (`mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason`/`short_answer`/`long_answer`/`case_study`) via structured output (`TaskType.QUIZ_GENERATION`, `ai/orchestrator/orchestrator.py`, `docs/PROMPTS.md`'s `quiz_generation` template) — one flat JSON shape per question (`ai/orchestrator/schemas.py:QuestionItem`) discriminated by `question_type`, carrying `correct_answer` (objective types) or `reference_answer` (free-text types), a `difficulty` tag per item, a `topic` tag per item, and a per-item citation. Behind `PERSONALIZATION_ENABLED`, a newly generated `mixed` quiz with topic evidence uses ADR 0014's mastery band to request exact easy/medium/hard counts; the orchestrator rejects a response that drifts from those counts. Insufficient evidence keeps the normal mixed request and the persisted quiz reports `adaptation_applied=false`. Existing quizzes and active attempts are never regenerated or mutated. No OpenCode Zen fallback.
5. **Implemented:** Quiz + Questions persistence (`docs/DATABASE.md`) and backend wiring (Milestone 3, `docs/API.md`'s Quiz API). Quiz attempt/submission/grading (workflow 6 below) is separate backend wiring, also implemented (Milestone 7).

### 4. User Question → RAG → NotebookLM → Gemini (AI Chat)
1. User asks a question in a notebook-scoped chat.
2. **Implemented:** if the notebook has at least one `indexed` source, the orchestrator asks NotebookLM directly (`TaskType.NOTEBOOK_QUERY`) for a grounded answer + citations across all its sources.
3. **Implemented (Phase 4 Milestone 2 backend):** NotebookLM remains first. When it is unavailable or returns an answer without citations, the backend embeds the query and runs owner/notebook-scoped pgvector cosine and PostgreSQL full-text searches, merges them with reciprocal-rank fusion, and supplies at most eight verified chunks within a 16,000-character context budget. If both paths fail or return nothing, the existing ungrounded response path remains.
4. Gemini synthesizes a teaching-framed answer using verified grounding and bounded persisted conversation history, with citations carried through. With `PERSONALIZATION_ENABLED`, only explicit or accepted explanation preferences affect the prompt. A notebook with no usable grounding falls back to the existing ungrounded response path.
5. The user and assistant turns are persisted to the notebook conversation, including provider, kind, citations, and any attached image. Chat content is not stored as long-term learner memory; structured graded-answer evidence is the mastery source.

### 5. Internet Search → Gemini
**Implemented, end-to-end:** `TaskType.INTERNET_SEARCH` (ADR 0012, `docs/adr/0012-internet-search-integration.md`), `POST /notebooks/{id}/search` (`docs/API.md`), and a "Search the web" toggle on the Ask tab (`frontend/src/components/notebook/AskNotebookSection.tsx`).
1. Student checks "Search the web" and asks a question needing current/external information (not covered by notebook sources) — see routing step 4 in `docs/AI.md`.
2. Tavily executed first (`ai/internet_search/tavily_client.py`), read through a 10-minute Redis cache (`ai/internet_search/cache.py`) keyed on the normalized query + provider + `max_results`. On a Tavily failure, Brave (`ai/internet_search/brave_client.py`) is tried only if `BRAVE_SEARCH_API_KEY` is configured — never cached, per Brave's Search API terms (`docs/TOKEN_OPTIMIZATION.md`'s per-provider caching asymmetry). Both providers' raw responses are normalized into a provider-neutral `InternetSearchResult` (`ai/internet_search/schemas.py`) before leaving the client.
3. Gemini synthesizes an answer from the normalized results (`ai/orchestrator/orchestrator.py:_run_internet_search`, `docs/PROMPTS.md`'s `internet_search_synthesis` template), citing external sources inline by URL — a provider's own "answer" mode is never used, keeping citation handling centralized. Citations are built from each result's URL/snippet (`AIResponse.citations`), clearly distinguished from notebook-grounded citations by their `source_id` being a URL rather than a NotebookLM source id.

### 6. Quiz Submission → Evaluation → Progress Tracking
1. **Implemented:** user starts a quiz attempt (`QuizAttempt`, `backend/app/models/quiz_attempt.py`) via the Quiz Attempts API (`docs/API.md`), autosaves answers, then submits.
2. **Implemented:** on submit, the attempt's questions split by grading path (ADR 0011) — `mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason` are graded deterministically in plain Python, no AI call (`backend/app/services/quiz_attempt_service.py`). `short_answer`/`long_answer`/`case_study` questions are graded in a single batched Gemini call (`TaskType.QUIZ_GRADING`, `ai/orchestrator/orchestrator.py`, `docs/PROMPTS.md`'s `quiz_grading` template) covering every free-text question in the attempt — never one call per question (`.claude/rules/performance.md`) — dispatched via `app/workers/quiz_grading_tasks.py`; skipped entirely for all-objective quizzes. Returns one `QuestionGradeResult` per question (`score` 0.0–1.0, `is_correct`, `feedback`, `topic_tag`), matched back to its question by `question_id`. No OpenCode Zen fallback, same precedent as `QUIZ_GENERATION` (ADR 0011).
3. **Implemented:** both grading paths' results persist into `QuizAttemptAnswer` (`score`/`is_correct`/`ai_feedback`/`topic_tag`) — deterministic grading sets `topic_tag` from `Question.topic` (populated at generation time, `ai/orchestrator/schemas.py:QuestionItem.topic`), AI grading sets it directly from `QuestionGradeResult.topic_tag` — the attempt's overall `score`/`max_score` is computed, and every low-scoring `topic_tag` aggregates into `weak_topics.missed_count` (`backend/app/models/weak_topic.py`) — a running tally per `(user, notebook, topic)`, not a per-attempt snapshot (`docs/AI.md#memory--personalization`, ADR 0011).
4. **Implemented:** grading writes immutable per-answer learning evidence, recalculates recency/difficulty-weighted topic mastery, and records an idempotent `quiz_completed` study activity. The analytics service derives score trends, bounded study time, UTC-date streaks, heatmap days, and factual revision history (`docs/DATABASE.md`).
5. **Implemented:** deterministic improvement recommendations, mastery/progress analytics, activity heatmap, streak, and revision history are surfaced on the dashboard. Recommendation action, priority, topic, URL, and rationale remain backend-authoritative.

### 7. (Reserved) Study Plan Generation
<!-- TODO: document once Phase 4 adaptive study planning is implemented -->

### 8. (Reserved) Audio Overview Generation
<!-- TODO: document NotebookLM audio pipeline once implemented -->

### 9. Paper Search → Gemini
**Implemented, end-to-end:** `TaskType.PAPER_SEARCH` (ADR 0013, `docs/adr/0013-paper-search-integration.md`), a stateless `POST /notebooks/{id}/paper-search` and a persisted, conversation-scoped `POST /notebooks/{id}/conversations/{conversation_id}/paper-search` (`docs/API.md`), and a "Papers" option in the Ask tab's Notebook/Web/Papers radio group (`frontend/src/components/notebook/AskNotebookSection.tsx`).
1. Student selects "Papers" and asks a question needing academic-literature grounding — see `docs/AI.md`'s `TaskType.PAPER_SEARCH` routing entry.
2. arXiv executed first (`ai/paper_search/arxiv_client.py`), read through a 24-hour Redis cache (`ai/paper_search/cache.py`) keyed on the normalized query + provider + `max_results` (arXiv's own once-per-day-is-enough guidance). On an arXiv failure, Semantic Scholar (`ai/paper_search/semantic_scholar_client.py`) is tried only if `SEMANTIC_SCHOLAR_API_KEY` is configured — never cached, pending resolution of its non-commercial default license (`docs/SECURITY.md`). An arXiv call that succeeds with zero papers is not a failure and does not trigger the fallback — same empty-result semantics as `_run_internet_search`. Both providers' raw responses normalize into a provider-neutral `PaperSearchResult` (`ai/paper_search/schemas.py`) before leaving the client.
3. Gemini synthesizes an answer from the normalized results (`ai/orchestrator/orchestrator.py:_run_paper_search`, `docs/PROMPTS.md`'s `paper_search_synthesis` template), citing papers inline by URL — a provider's own summary is never used, keeping citation handling centralized. Citations are built from each result's URL/abstract (`AIResponse.citations`).
4. **Implemented:** the conversation-scoped route persists a `kind=paper_search` user/assistant message pair (`docs/DATABASE.md`), so results survive reload — rendered in `ChatMessage.tsx` with a distinct icon/label/citation-block treatment from `web_search`.

<!-- Add new workflows above this line as features ship. Keep one numbered section per pipeline. -->
