# Starting Lumora Locally

How to bring up the full stack for manual testing. One-time setup once, then a normal
startup sequence you'll repeat every session.

## Prerequisites

- Python 3.12+, [`uv`](https://github.com/astral-sh/uv)
- Node 20+, `pnpm` (`corepack enable && corepack prepare pnpm@latest --activate` if you don't have it)
- Docker (Postgres + Redis run in containers)
- `tesseract-ocr` installed system-wide (image OCR parsing)
- Optional, only needed for real NotebookLM indexing: the `nlm` CLI (`uv tool install notebooklm-mcp-cli`), authenticated once via `nlm login`

## One-time setup

```bash
# Backend env
cd backend
cp .env.example .env
# Fill in .env yourself:
#   DATABASE_URL / REDIS_URL — leave as the .env.example defaults if you use the
#     docker-compose.yml below unchanged (postgres on 5432, redis on 6380 — see
#     "Why redis is on 6380" below)
#   JWT_SECRET_KEY           — any random string (openssl rand -hex 32)
#   GEMINI_API_KEY           — optional; needed for the notebook "Ask a question" feature
#   OPENCODE_ZEN_API_KEY     — optional; fallback for the same feature if Gemini fails/is unset
#   GOOGLE_CLIENT_ID         — optional; Google login isn't wired in the frontend yet anyway
# Everything else can stay blank for local dev (Supabase Storage falls back to local disk).

uv sync
```

```bash
# Frontend env
cd frontend
cp .env.example .env   # VITE_API_BASE_URL defaults to http://localhost:8000/api/v1, fine as-is
pnpm install
```

## Every-day startup (4 terminals)

**1. Infra (Postgres + Redis)**
```bash
cd docker
docker compose up -d
```
First run only, then whenever the schema changes:
```bash
cd backend && uv run alembic upgrade head
```

**2. Backend API**
```bash
cd backend
uv run uvicorn app.main:app --reload
```
→ http://localhost:8000 (interactive API docs at `/docs`)

**3. Celery worker** (document parsing + NotebookLM indexing — nothing you upload will ever
finish "Pending" without this running)
```bash
cd backend
uv run celery -A app.workers.celery_app worker --loglevel=info
```

**4. Frontend**
```bash
cd frontend
pnpm dev
```
→ http://localhost:5173 — open this and test through the actual UI: register, upload a
PDF/DOCX/PPTX/image, watch it parse, ask it a question, delete it.

## Test account (skip registering every time)

```bash
cd backend
uv run python scripts/seed_test_user.py
```
Creates (or confirms) a fixed account: `test@lumora.dev` / `testpass123`. Safe to run
repeatedly — idempotent, reports "already exists" instead of erroring on a second run.

## Notes

- **"Can't reach the server..." on register/login?** The frontend can't reach the backend at
  all — it's not running, on the wrong port, or CORS-blocked. Check the backend terminal
  from step 2 above; `curl http://localhost:8000/health` should return `{"status":"ok"}`.
- **Why redis is on 6380, not 6379**: another local Redis (`ids_redis`, unrelated to this
  project) was already holding 6379 on this machine. `docker/docker-compose.yml` maps
  `6380:6379`. If you don't have that conflict, you can change it back to `6379:6379` and
  update `REDIS_URL` in `backend/.env` to match — just keep both in sync.
- **CORS is locked to `http://localhost:5173`** (`backend/app/core/config.py`). If Vite
  picks a different port (it will if 5173 is already in use — check for a stray `vite`
  process before assuming something's broken), free 5173 or add the new origin to
  `CORS_ORIGINS` in `backend/.env`.
- **The backend needs the Celery worker to actually be running**, not just started once —
  restart both together after pulling backend changes. `uv run uvicorn ... --reload`
  hot-reloads on code changes; the Celery worker does not, restart it manually after
  changes to `app/workers/`, `app/services/`, or `ai/`.
- **"Ask a question" needs a real API key.** With neither `GEMINI_API_KEY` nor
  `OPENCODE_ZEN_API_KEY` set, it fails fast with a clear error — that's expected, not a bug.
- **NotebookLM indexing needs `nlm login`** run once on this machine. Without it, sources
  attach fine but show `Failed` in the notebook detail page's Sources list — also expected,
  not a bug (`docs/DECISIONS.md#known-debt-not-yet-adr-worthy`).
- Full command reference: `CLAUDE.md`. Deeper setup detail (Supabase, Google OAuth, OpenCode
  Zen signup): earlier project conversation / `docs/SECURITY.md` / `docs/DEPLOYMENT.md`.
