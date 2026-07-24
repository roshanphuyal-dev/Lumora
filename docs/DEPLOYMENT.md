# Deployment

## Purpose

How the application gets built, shipped, and run in production — infra topology, CI/CD, environment configuration.

## What Belongs Here

- Infra topology (what runs where).
- CI/CD pipeline description.
- Environment/config management across environments.

## What Never Belongs Here

- Application-level security policy (`SECURITY.md`).
- Monitoring/alerting detail once live (`OBSERVABILITY.md`) — this doc covers *getting code running*, that one covers *watching it run*.

## Structure

### Infra Topology
Single Oracle Cloud Always Free VPS running Docker Compose: Nginx (reverse proxy + TLS termination) → FastAPI backend container + React static build served by Nginx + Redis container + Celery worker container(s). PostgreSQL hosted on Supabase (managed, not self-hosted).

### Environments
- **Local**: `docker compose up`, `.env` per service.
- **Production**: single VPS, `.env` populated from deployment secrets (never committed).
- No staging environment yet — `main` is deployable; consider adding a staging environment before the first real user cohort (record as ADR if/when added).

### Manual Deploy Prerequisites (not automatable via `.env`/secrets)
- **NotebookLM CLI auth**: `ai/notebooklm/client.py` shells out to the `nlm` CLI (`notebooklm-mcp-cli`). On any machine running the Celery worker (indexing dispatches from `backend/app/workers/notebook_tasks.py`), a human must:
  1. `uv tool install notebooklm-mcp-cli`
  2. `nlm login` — interactive, opens a browser, stores a cookie-based session for that machine's `nlm` profile.
  This is a deliberate one-time-per-machine manual step (`docs/DECISIONS.md#known-debt-not-yet-adr-worthy`), not an env var/secret — it can't be baked into the CI/CD pipeline as-is. Until it's done, NotebookLM indexing fails and notebook sources stay in `failed` status (`docs/AI.md#routing-logic`).
- **Supabase Storage config**: set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (plus optionally `SUPABASE_STORAGE_BUCKET`, defaults to `documents`) in the backend/worker `.env` for any real deployment. Without them, `get_file_storage()` (`backend/app/core/storage.py`) silently falls back to `LocalFileStorage` (disk-backed) — fine for local dev/tests, wrong for production (files wouldn't survive a container redeploy).

### CI/CD (GitHub Actions)
- On PR: lint + test (backend `ruff` + `pytest`, frontend `pnpm lint` + `pnpm test`).
- On merge to `main`: build Docker images, push to registry, SSH-deploy to the Oracle Cloud VPS, run Alembic migrations, restart services.
- Pipeline definitions live in `.github/workflows/` (not yet created — add when Phase 1 nears deployment).

### Release Process
See `CONTRIBUTING.md#release-process` for versioning/tagging; this doc covers what a release *does* once triggered (build → migrate → restart), that one covers *when/how it's cut*.

### Rollback
Redeploy the previous tagged image; if a migration is not backward-compatible, the migration's docstring (per `docs/DATABASE.md`) must specify the manual rollback steps.

<!-- TODO: write actual .github/workflows/ pipeline once Phase 1 nears deployment -->
<!-- TODO: document TLS/cert renewal (Nginx + Let's Encrypt) once configured -->
<!-- TODO: revisit single-VPS topology if load requires horizontal scaling -->
