# API

## Purpose

The contract reference for the FastAPI backend: endpoint groups, auth model, versioning policy, response conventions.

## What Belongs Here

- Endpoint groups and their responsibilities.
- Request/response conventions (pagination, error shape, status codes).
- Versioning policy.

## What Never Belongs Here

- Full OpenAPI spec — FastAPI generates this automatically at `/docs`; don't hand-maintain a duplicate.
- Business logic — this doc describes the contract, not the implementation.
- AI routing detail (`AI.md`).

## Structure

### Endpoint Groups
- **Auth API** — register, login, Google OAuth, token refresh, profile.
- **Document API** (`/api/v1/documents`, scoped to `uploaded_by` = authenticated user):
  - `POST /documents` — multipart upload (`file`, optional `subject_id`/`title`/`description`); writes bytes via `FileStorage` (`backend/app/core/storage.py`) and dispatches async parsing (Celery). Returns the created document (`parse_status=pending`).
  - `POST /documents/url` — link resource (JSON body: `url`, optional `title`/`description`/`subject_id`); no bytes uploaded — dispatches the same async parsing (Celery), which fetches `url` directly (`backend/app/parsers/url_parser.py`) instead of downloading from storage. Returns the created document (`parse_status=pending`).
  - `GET /documents` — paginated list (`limit`/`offset`, optional `subject_id` filter); list items omit `extracted_text`.
  - `GET /documents/{id}` — detail, including `parse_status` and `extracted_text`; also the parse-status poll target (no separate status endpoint).
  - `DELETE /documents/{id}`.
- **Notebook API** (`/api/v1/notebooks`, scoped to `owner_id` = authenticated user):
  - `POST /notebooks`, `GET /notebooks` (paginated; optional case-insensitive `search` across name and description), `GET /notebooks/{id}` (detail includes attached `sources`), `DELETE /notebooks/{id}`.
  - `POST /notebooks/{id}/sources` — attach a `document_id` as a source; requires the document's `parse_status == done` (409 otherwise); dispatches NotebookLM indexing (Celery) and returns the source with `indexing_status=pending`.
  - `DELETE /notebooks/{id}/sources/{source_id}` — detach a source.
  - `GET /notebooks/{id}/sources/{source_id}/chunks/{chunk_id}` — resolve a verified local citation to owner-scoped source metadata, page/slide locator, and bounded chunk text; returns 404 for any notebook/source/chunk ownership or relationship mismatch.
  - `POST /notebooks/{id}/ask` — plain (ungrounded) teaching-explanation question via the orchestration layer (Gemini, OpenCode Zen fallback, ADR 0008); returns `{content, provider}`. Single-turn, not persisted — superseded for multi-turn use by the Chat API below; kept for now as the simple one-shot path.
  - `POST /notebooks/{id}/search` — body `{query}`; internet search for current/external information not covered by the notebook's own sources (`TaskType.INTERNET_SEARCH`: Tavily primary, Brave fallback if configured, Gemini synthesizes the cited answer — ADR 0012). Returns `{content, provider, citations}`, same shape as `/ask`. Single-turn, not persisted. 502 if every search provider fails.
  - `POST /notebooks/{id}/paper-search` — body `{query}`; academic literature search (`TaskType.PAPER_SEARCH`: arXiv primary, Semantic Scholar fallback if configured, Gemini synthesizes the cited answer — ADR 0013). Returns `{content, provider, citations}`, same shape as `/search`. Single-turn, not persisted. 502 if every search provider fails. Superseded for chat use by the persisted `POST /notebooks/{id}/conversations/{conversation_id}/paper-search` below (same reasoning as `/search` vs. its conversation-scoped counterpart); kept for now as the stateless one-shot path.
  - `POST /notebooks/{id}/image-search` — body `{query}`; topic-relevant image lookup (`TaskType.TOPIC_IMAGE_SEARCH`: Wikimedia Commons primary, Openverse fallback — ADR 0010). Returns `{found: bool, image_url?, attribution?, license?, source_url?}` — `found=false` (all other fields `null`) is a real "no image for this topic" outcome, distinct from a 502 (every provider failed as a request).
- **Notebook Search API** — semantic search within a notebook.
- **Chat API** (`/api/v1/notebooks/{notebook_id}/conversations`, scoped to `user_id` = authenticated user; streaming + persistence architecture per ADR 0009):
  - `POST /notebooks/{id}/conversations` — create a conversation (optional `title`); returns `ConversationRead`.
  - `GET /notebooks/{id}/conversations` — list the user's conversations for the notebook, most recently updated first.
  - `GET /notebooks/{id}/conversations/{conversation_id}/messages` — full message history (`MessageRead[]`, includes `role`, `kind`, `content`, `provider`, `citations`, and nullable `image_result`). `kind` is `notebook`, `web_search`, or `paper_search`; the latter two identify external-link/citation-bearing search turns.
  - `POST /notebooks/{id}/conversations/{conversation_id}/messages/stream` — send a message; returns `text/event-stream` (SSE). Events: `start` (persisted user message + assistant message id), `delta` (incremental assistant content, one per provider chunk), `done` (final persisted assistant `MessageRead`), `error` (stream failed, nothing persisted for the assistant turn). Routes through the orchestration layer (`TaskType.CHAT_RESPONSE`, Gemini streaming with OpenCode Zen non-streaming fallback); grounds against NotebookLM when the notebook has an indexed source.
  - `POST /notebooks/{id}/conversations/{conversation_id}/search` — body `{query}`; runs the same internet-search orchestration as the stateless notebook route and persists a `kind=web_search` user/assistant pair. Returns `{user_message: MessageRead, assistant_message: MessageRead}`.
  - `POST /notebooks/{id}/conversations/{conversation_id}/paper-search` — body `{query}`; runs the same paper-search orchestration as the stateless notebook route and persists a `kind=paper_search` user/assistant pair. Returns `{user_message: MessageRead, assistant_message: MessageRead}` (reuses the `WebSearchCreate`/`WebSearchMessagePair` schemas — both are already field-generic, no web-specific naming).
  - `PUT /notebooks/{id}/conversations/{conversation_id}/messages/{message_id}/image` — body `{query}`; searches for an image and stores it on the existing assistant message. Returns the updated `MessageRead`; if no usable image is found, `image_result` remains `null`.
- **AI API** — explain, generate (routes to orchestration layer per `docs/AI.md`).
- **Notes API** (`/api/v1/notebooks/{notebook_id}/notes`, scoped to `user_id` = authenticated user; async generation, poll for status):
  - `POST /notebooks/{id}/notes` — body `{material_type: "note" | "study_guide", title?, topic?}`; creates the row (`status=pending`) and dispatches generation (Celery), returning immediately — generation itself isn't in the request/response cycle.
  - `GET /notebooks/{id}/notes` — paginated list (`limit`/`offset`), most recently created first.
  - `GET /notebooks/{id}/notes/{note_id}` — detail; the poll target (`status`: `pending` → `generating` → `done`/`failed`; `content`/`citations` populate once `done`).
  - `DELETE /notebooks/{id}/notes/{note_id}`.
- **Flashcards API** (`/api/v1/notebooks/{notebook_id}/flashcard-sets`, same scoping/async-poll shape as the Notes API):
  - `POST /notebooks/{id}/flashcard-sets` — body `{title?, topic?, count?}` (`count` defaults to 12); creates the set (`status=pending`) and dispatches generation.
  - `GET /notebooks/{id}/flashcard-sets` — paginated list.
  - `GET /notebooks/{id}/flashcard-sets/{set_id}` — detail including nested `flashcards` (empty until `status=done`); the poll target.
  - `DELETE /notebooks/{id}/flashcard-sets/{set_id}`.
- **Studio API** (`/api/v1/notebooks/{notebook_id}/studio`, scoped to `user_id`; async generation, poll for status; NotebookLM-only, no ungrounded fallback — 409 if the notebook has no indexed source):
  - `POST /notebooks/{id}/studio` — body `{artifact_type: "audio"|"report"|"slides"|"infographic"|"mindmap"|"data_table", title?, format?, length?, focus?, language?, prompt?, orientation?, detail?, description?}` (which fields apply depends on `artifact_type`; `description` is required for `data_table`, 422 otherwise); creates the row (`status=pending`) and dispatches generation.
  - `GET /notebooks/{id}/studio` — paginated list.
  - `GET /notebooks/{id}/studio/{material_id}` — detail; the poll target. `content` (Markdown/JSON) populates for `report`/`mindmap`; `has_download` flips true for the other four once `done` — never exposes the internal storage path.
  - `GET /notebooks/{id}/studio/{material_id}/download` — streams the generated file (audio/slides/infographic/data_table only) with `Content-Disposition: attachment`, auth-scoped.
  - `DELETE /notebooks/{id}/studio/{material_id}`.
- **Quiz API** (`/api/v1/notebooks/{notebook_id}/quizzes`, same scoping/async-poll shape as the Notes/Flashcards APIs; generation only):
  - `POST /notebooks/{id}/quizzes` — body `{title?, topic?, question_types?, question_count?, difficulty?, time_limit_seconds?, include_web_search?}` (`question_types` a non-empty subset of `mcq`/`true_false`/`fill_blank`/`matching`/`short_answer`/`long_answer`/`case_study`, defaults to `["mcq"]`; `question_count` defaults to 10; `difficulty` one of `easy`/`medium`/`hard`/`mixed`, defaults to `mixed`; `include_web_search` defaults to `false` — opts generation into grounding with `TaskType.INTERNET_SEARCH` results, see `app/workers/quiz_tasks.py`); creates the quiz (`status=pending`) and dispatches generation.
  - `GET /notebooks/{id}/quizzes` — paginated list.
  - `GET /notebooks/{id}/quizzes/{quiz_id}` — detail including nested `questions` (empty until `status=done`); the poll target. The quiz includes `adaptation_applied` and nullable `adaptive_difficulty_mix` (`{easy, medium, hard}` counts). Questions are returned in the answer-key-free `QuestionRead` shape (no `correct_answer`/`reference_answer`/`explanation`/`citation`) — this is a pre-attempt/preview view.
  - `DELETE /notebooks/{id}/quizzes/{quiz_id}`.
- **Quiz Attempts API** (`/api/v1/notebooks/{notebook_id}/quizzes/{quiz_id}/attempts`, scoped to `user_id` = authenticated user; deterministic + AI-dispatched grading per ADR 0011):
  - `POST /notebooks/{id}/quizzes/{quiz_id}/attempts` — no request body; 409 if the quiz isn't `status=done` or has no questions. Randomizes `question_order`, snapshots the quiz's `time_limit_seconds`, creates the attempt (`status=in_progress`), returns it in the `QuizAttemptRead` shape (answer-key-free — see below). Multiple concurrent/repeat attempts per quiz are allowed; each is independent.
  - `PATCH /notebooks/{id}/quizzes/{quiz_id}/attempts/{attempt_id}` — autosave, one question per call: body `{question_id, answer}` (`answer` shape depends on `question_type`, documented on `QuizAttemptAnswerPatch`). 409 if the attempt isn't `in_progress`, 404 if `question_id` isn't part of this attempt, 409 if the attempt's time limit has already elapsed (autosave rejects past the deadline rather than auto-submitting — see `quiz_attempt_service.autosave_answer` for the rationale; the client is expected to call `submit` itself). Returns the updated `QuizAttemptRead`.
  - `POST /notebooks/{id}/quizzes/{quiz_id}/attempts/{attempt_id}/submit` — 409 if the attempt isn't `in_progress` (submitting is allowed even past the time limit — a late submit still finalizes whatever was autosaved). Grades every `mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason` answer deterministically in Python (exact/set match, 1.0/0.0, no partial credit) immediately. If the quiz has any `short_answer`/`long_answer`/`case_study` questions, status becomes `grading` and a Celery task (`app/workers/quiz_grading_tasks.py`) grades them via one batched `TaskType.QUIZ_GRADING` call, then flips status to `graded`; if the quiz is all-objective, scoring finishes synchronously and status goes straight to `graded` (no AI call). Returns the attempt in whichever shape matches its (possibly still `grading`) status.
  - `GET /notebooks/{id}/quizzes/{quiz_id}/attempts/{attempt_id}` — the poll target. **Security boundary**: while `status` is `in_progress`/`submitted`/`grading`, returns `QuizAttemptRead` (questions in the answer-key-free `QuestionRead` shape — no `correct_answer`/`reference_answer`/`explanation`/`citation` anywhere in the response). Only once `status=graded` does it return `QuizAttemptReviewRead` (questions in `QuestionReviewRead`, paired with the student's `QuizAttemptAnswer` — `student_answer`/`is_correct`/`score`/`ai_feedback`/`topic_tag` — plus the attempt's total `score`/`max_score`).
  - `GET /notebooks/{id}/quizzes/{quiz_id}/attempts` — paginated list of the user's attempts for this quiz, lightweight `QuizAttemptSummary` shape (no nested questions).
  - A graded attempt's missed questions (deterministic or AI-graded, wherever `topic_tag` is set) increment `weak_topics.missed_count` for `(user_id, notebook_id, topic)` — feeds adaptive tutoring (`docs/AI.md#memory--personalization`), not itself exposed via this API group yet.
- Internet search, paper search, and topic-image lookup are implemented as `POST /notebooks/{id}/search`, `POST /notebooks/{id}/paper-search`, and `POST /notebooks/{id}/image-search` under the Notebook API above, not standalone groups.
- **Progress API** (default-off behind `PERSONALIZATION_ENABLED`, notebook- and owner-scoped):
  - `GET /notebooks/{id}/progress` — graded-attempt count, evidence-backed answered-question count, aggregate quiz score, and tracked/low-mastery topic counts.
  - `GET /notebooks/{id}/mastery` — paginated weakest-first topic mastery with confidence, decayed evidence weight/count, and calculation time. Values use live recency decay from graded-answer evidence.
- **Analytics API** (default-off behind `PERSONALIZATION_ENABLED`):
  - `GET /notebooks/{id}/analytics/quiz-performance` — paginated graded-attempt score history plus daily aggregates for the returned window.
  - `POST /notebooks/{id}/activities` — idempotently record a client study event. Body: `{activity_key, activity_type, duration_seconds, occurred_at, resource_type?, resource_id?}`; client activity types are `study_session`, `material_viewed`, and `material_revised`, duration is bounded to four hours, timestamps require a timezone and a seven-day backfill window, and resource fields must be supplied together. `quiz_completed` is system-authored during grading.
  - `GET /notebooks/{id}/analytics/activity?days=90` — notebook study-time totals, current/longest UTC-date streaks, active-day count, and daily heatmap entries. `days` is bounded to 1–366.
  - `GET /users/me/analytics/activity?days=90` — the same deterministic activity rollup across notebooks owned by the authenticated user.
  - `GET /notebooks/{id}/revision-history` — paginated factual material-viewed/material-revised/quiz-completed events, newest first.
- **Personalization API** (default-off behind `PERSONALIZATION_ENABLED`):
  - `GET/PATCH /users/me/learning-preferences` — read or explicitly set user-scoped explanation depth/style.
  - `GET /users/me/learning-preference-suggestions` and `POST .../refresh` — list pending suggestions or derive them from deterministic learning signals; pending suggestions do not affect tutoring prompts.
  - `POST /users/me/learning-preference-suggestions/{suggestion_id}/accept|reject` — resolve a suggestion; only acceptance writes the preference.
  - `GET /notebooks/{id}/recommendations` — owner-scoped actions selected and prioritized deterministically from mastery. Action, priority, topic, URL, and rationale are backend-authoritative.
- **Export API** — Overleaf/LaTeX/PDF/DOCX/Markdown export.

### Conventions
- REST-ish resource naming (`/notebooks/{id}/sources`), plural nouns.
- Auth: JWT bearer token on all routes except `/auth/*` register/login.
- Errors: consistent JSON shape `{ "detail": str, "code": str }`; standard HTTP status codes (400 validation, 401 auth, 403 authorization, 404 not found, 429 rate limit, 500 server).
- Pagination: `limit`/`offset` query params on all list endpoints (default `limit=20`, max `100`), response shape `{ "items": [...], "total": int, "limit": int, "offset": int }`.
- Long-running AI generation (quiz/notes/audio) returns a job ID + status endpoint rather than blocking the request, backed by Celery.

### Versioning Policy
- Prefix all routes with `/api/v1/`.
- Breaking changes bump the version prefix (`/api/v2/`); additive changes (new optional field, new endpoint) don't require a bump.
- Deprecated versions stay live for a documented grace period (TBD once there's a first external consumer).

<!-- TODO: link generated OpenAPI docs URL once backend is deployed -->
