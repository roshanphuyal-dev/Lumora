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
- **Document API** — upload, parse status, metadata, delete.
- **Notebook API** — create/list/delete notebooks, manage sources.
- **Notebook Search API** — semantic search within a notebook.
- **AI API** — chat, explain, generate (routes to orchestration layer per `docs/AI.md`).
- **Quiz API** — generate, fetch, submit attempts.
- **Notes API** / **Study Guide API** — generate/fetch generated materials.
- **Search API** — internet search proxy (Tavily/Brave), cached.
- **Image API** — image retrieval proxy (Wikimedia/Openverse/Unsplash), cached.
- **Progress API** — study stats, streaks, mastery.
- **Analytics API** — performance graphs, heatmaps.
- **Chat API** — AI chat history/threads.
- **Export API** — Overleaf/LaTeX/PDF/DOCX/Markdown export.

### Conventions
- REST-ish resource naming (`/notebooks/{id}/sources`), plural nouns.
- Auth: JWT bearer token on all routes except `/auth/*` register/login.
- Errors: consistent JSON shape `{ "detail": str, "code": str }`; standard HTTP status codes (400 validation, 401 auth, 403 authorization, 404 not found, 429 rate limit, 500 server).
- Pagination: cursor or `limit`/`offset` query params on all list endpoints — pick one convention and apply it uniformly (decide at Phase 1 implementation, record as ADR if contested).
- Long-running AI generation (quiz/notes/audio) returns a job ID + status endpoint rather than blocking the request, backed by Celery.

### Versioning Policy
- Prefix all routes with `/api/v1/`.
- Breaking changes bump the version prefix (`/api/v2/`); additive changes (new optional field, new endpoint) don't require a bump.
- Deprecated versions stay live for a documented grace period (TBD once there's a first external consumer).

<!-- TODO: finalize pagination convention at Phase 1 implementation -->
<!-- TODO: link generated OpenAPI docs URL once backend is deployed -->
