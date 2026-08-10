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
  - `POST /notebooks/{id}/ask` — plain (ungrounded) teaching-explanation question via the orchestration layer (Gemini, OpenCode Zen fallback, ADR 0008); returns `{content, provider}`. Single-turn, not persisted — superseded for multi-turn use by the Chat API below; kept for now as the simple one-shot path.
- **Notebook Search API** — semantic search within a notebook.
- **Chat API** (`/api/v1/notebooks/{notebook_id}/conversations`, scoped to `user_id` = authenticated user; streaming + persistence architecture per ADR 0009):
  - `POST /notebooks/{id}/conversations` — create a conversation (optional `title`); returns `ConversationRead`.
  - `GET /notebooks/{id}/conversations` — list the user's conversations for the notebook, most recently updated first.
  - `GET /notebooks/{id}/conversations/{conversation_id}/messages` — full message history (`MessageRead[]`, includes `role`, `content`, `provider`, `citations`).
  - `POST /notebooks/{id}/conversations/{conversation_id}/messages/stream` — send a message; returns `text/event-stream` (SSE). Events: `start` (persisted user message + assistant message id), `delta` (incremental assistant content, one per provider chunk), `done` (final persisted assistant `MessageRead`), `error` (stream failed, nothing persisted for the assistant turn). Routes through the orchestration layer (`TaskType.CHAT_RESPONSE`, Gemini streaming with OpenCode Zen non-streaming fallback); grounds against NotebookLM when the notebook has an indexed source.
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
- **Quiz API** — generate, fetch, submit attempts.
- **Search API** — internet search proxy (Tavily/Brave), cached.
- **Image API** — image retrieval proxy (Wikimedia/Openverse/Unsplash), cached.
- **Progress API** — study stats, streaks, mastery.
- **Analytics API** — performance graphs, heatmaps.
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
