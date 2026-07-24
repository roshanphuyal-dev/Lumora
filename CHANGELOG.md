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

### Changed
- _nothing yet_

### Fixed
- _nothing yet_
