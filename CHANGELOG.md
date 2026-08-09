# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project documentation and Claude Code workspace scaffold (`docs/`, `.claude/`, `AGENTS.md`, `CONTRIBUTING.md`).
- Backend scaffold (FastAPI + SQLAlchemy async + Alembic) with `users`, `courses`, `subjects` tables and their first migration.
- Auth API: register, login, Google ID-token login, refresh — JWT access + refresh token pair.
- Courses API: create/list courses and subjects, scoped to the authenticated user, `limit`/`offset` pagination.
- Local dev Postgres via `docker/docker-compose.yml`.
- `documents`, `notebooks`, `notebook_sources` tables and their migration.
- Document API: upload (multipart, dispatches async parsing), paginated list, detail (parse status + extracted text poll target), delete — scoped to the uploading user.
- Document parsing pipeline: PDF/PPTX/DOCX/image-OCR parsers (`backend/app/parsers/`) run via a Celery task, with a local-disk `FileStorage` stopgap ahead of real Supabase Storage wiring.
- Notebook API: CRUD plus attach/detach document sources, dispatching NotebookLM indexing via Celery — scoped to the owning user.
- AI orchestration layer (`ai/orchestrator/`): `task_type`-based routing for `document_index` (→ NotebookLM) and `teaching_explanation` (→ Gemini 2.5 Flash, live via `google-genai`).
- `redis` service added to `docker/docker-compose.yml` (Celery broker).
- Real Supabase Storage integration (`backend/app/core/storage.py`: `SupabaseFileStorage`, via `supabase-py`) — `get_file_storage()` uses it when `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are set, otherwise falls back to the local-disk `FileStorage` stopgap (dev/test default).
- Real NotebookLM CLI integration (`ai/notebooklm/client.py`) replacing the always-fails stub: shells out to the `nlm` CLI (`notebooklm-mcp-cli`) to create/reuse a notebook's remote NotebookLM id and upload/index source documents. Requires a one-time interactive `nlm login` per machine running the Celery worker (`docs/DEPLOYMENT.md`); not yet verified against a live authenticated `nlm` profile (`docs/DECISIONS.md#known-debt-not-yet-adr-worthy`).
- `notebooks.notebooklm_notebook_id` column + migration, caching the remote NotebookLM notebook id per `Notebook`.
- OpenCode Zen provider client (`ai/opencode_zen/client.py`) and Gemini <-> OpenCode Zen fallback for `TaskType.TEACHING_EXPLANATION` (`ai/orchestrator/orchestrator.py`) — if Gemini is unavailable, rate-limited, or its daily quota is exhausted, the orchestrator falls back to a free OpenCode Zen model, and vice versa (ADR 0008).
- Frontend scaffold (`frontend/`): Vite + React + TypeScript, Tailwind CSS v4, shadcn/ui (new-york style), React Router, TanStack Query, Framer Motion, React Hook Form. Design tokens (emerald accent, zinc neutral, Source Serif 4 + Inter, dark mode) wired per `docs/UI_UX.md`.
- Dashboard shell (`frontend/src/pages/DashboardPage.tsx`, `frontend/src/components/layout/AppShell.tsx`): sidebar app-shell, honest Phase-1-scoped empty states (upload CTA, empty notebooks list), and a quiet "coming soon" ledger for weak-topics/progress/streaks sections that have no real backend yet. `DESIGN.md` records the resulting design system.
- Auth pages (`frontend/src/pages/LoginPage.tsx`, `RegisterPage.tsx`): email/password login and registration (register auto-logs-in), wired to the real `/api/v1/auth` endpoints. Token storage (`frontend/src/lib/token-storage.ts`), an `AuthProvider`/`useAuth` context, and a `RequireAuth` route guard that redirects unauthenticated visits to `/login` — the dashboard route is now actually protected instead of always rendering. Google login rendered as a disabled "Soon" control (`GOOGLE_CLIENT_ID` isn't configured yet, per `docs/SECURITY.md`).
- Dashboard's "Your notebooks" section (`frontend/src/components/dashboard/NotebooksSection.tsx`) now fetches real data from `GET /api/v1/notebooks` (TanStack Query, `frontend/src/hooks/use-notebooks.ts`) with explicit loading/error/empty/populated states — verified end-to-end against a running backend, including a real created notebook rendering in the list.

### Changed
- _nothing yet_

### Fixed
- `backend/app/core/config.py` now calls `load_dotenv()` at import time so `backend/.env` populates the real process environment, not just the `Settings` pydantic model — `ai/gemini/client.py` and `ai/opencode_zen/client.py` read their API keys via `os.environ.get(...)` directly and previously wouldn't see them unless exported in the shell.
- `test_storage.py`'s Supabase-credential tests no longer depend on the developer's real `backend/.env` having no `SUPABASE_*` values set — they now monkeypatch `get_settings` to an explicit unconfigured stub.
- Celery worker: `documents.parse_document`/`notebooks.index_source` tasks failed with `NoReferencedTableError` on `documents.subject_id` — the worker process only imports the model modules its task functions directly touch, so SQLAlchemy's mapper registry never saw `Subject` and couldn't resolve the cross-table FK. `app/workers/celery_app.py` now imports every model module at startup (same pattern as `backend/tests/conftest.py`).
- Celery worker: running a second DB-touching task in the same worker process raised `RuntimeError: Future attached to a different loop` — each task wraps its work in its own `asyncio.run()`, but both tasks shared the app-wide pooled `engine`, and asyncpg connections are bound to the event loop that created them. Added a separate `celery_session_maker` (`app/db/session.py`, `NullPool`) so no DB connection ever crosses a loop boundary; `document_tasks.py`/`notebook_tasks.py` now use it instead of the FastAPI-request-scoped session maker.
