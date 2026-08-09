# Decisions

## Purpose

Index of Architecture Decision Records (ADRs) and the process for writing one. Individual decisions live as separate files in `docs/adr/` — this file is the index and the "how," not the decisions themselves.

## What Belongs Here

- A table indexing every ADR (number, title, status).
- The process for proposing/writing a new ADR.

## What Never Belongs Here

- The actual decision content — that's `docs/adr/00NN-slug.md`. Don't let this file grow into a wall of decisions; that's exactly the failure mode the directory-of-files structure avoids.

## Process

1. Copy `docs/adr/0000-template.md` to `docs/adr/00NN-slug.md` (next available number).
2. Fill in Context / Decision / Alternatives / Tradeoffs / Consequences / Status.
3. Open a PR; ADR merges alongside (or ahead of) the code implementing the decision.
4. Add a row to the index below.
5. If a decision is later reversed, don't delete the old ADR — mark it `Superseded by 00NN` and add the new one.

## Index

| # | Title | Status |
|---|---|---|
| [0001](adr/0001-fastapi.md) | Why FastAPI | Accepted |
| [0002](adr/0002-react.md) | Why React | Accepted |
| [0003](adr/0003-postgres-supabase.md) | Why PostgreSQL + Supabase | Accepted |
| [0004](adr/0004-notebooklm.md) | Why NotebookLM | Accepted |
| [0005](adr/0005-gemini.md) | Why Gemini | Accepted |
| [0006](adr/0006-oracle-cloud.md) | Why Oracle Cloud | Accepted |
| [0007](adr/0007-rag.md) | Why RAG | Accepted |
| [0008](adr/0008-opencode-zen-fallback.md) | OpenCode Zen as Gemini Fallback | Accepted |

<!-- Add new rows here as ADRs are written. Keep this table the only content of substance in this file. -->

## Known Debt (not yet ADR-worthy)

Stopgaps introduced during implementation that are deliberate but temporary — tracked here so they aren't lost, promoted to a full ADR only if reversing them turns out to be contested:

- **NotebookLM `notebook create`/`source add` response shape still unconfirmed**: `ai/notebooklm/client.py`'s `ensure_remote_notebook`/`index_document` have now been live-smoke-tested against an authenticated `nlm` profile (indexing works end-to-end), but the CLI's own docs still don't pin down the exact `--json` response shape for those two commands, so `_extract_id`'s key-name matching stays defensive/best-effort. `query_notebook` (`nlm notebook query`), added for `TaskType.NOTEBOOK_QUERY`, is different — its response shape (`{"answer", "references": [{"source_id", "citation_number"}], ...}`) was confirmed against a live call, not guessed. Tighten `_extract_id` to a confirmed shape if/when `notebook create`/`source add`'s is pinned down the same way.
- **Tailwind v4, not a `tailwind.config.ts`**: `docs/UI_UX.md` and `docs/FEATURES.md` originally assumed Tailwind v3's JS config file. The frontend scaffold (`frontend/`) uses Tailwind v4, which is CSS-first — tokens live in `frontend/src/index.css` (`@theme`/`:root`), not a config file. Not ADR-worthy on its own (Tailwind's own recommended setup), but noted since it contradicts the earlier doc wording.
- **OpenCode Zen fallback unverified against a live key** (`ADR 0008`): `ai/opencode_zen/client.py`'s request/response shape follows OpenCode Zen's published docs, not a confirmed live call — no `OPENCODE_ZEN_API_KEY` was available in the environment this was built in. Needs a live smoke-test once a real key is exercised. (`GeminiClient`/`OpenCodeZenClient` read their API key via `os.environ.get(...)` directly since `ai/` is intentionally decoupled from `backend/app/core/config.py`'s `Settings` — `backend/app/core/config.py` now calls `load_dotenv()` at import time so `backend/.env` populates the real process environment for both, not just `Settings`.)
