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
- **Quiz API** — generate, fetch, submit attempts.
- **Notes API** / **Study Guide API** — generate/fetch generated materials.
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
