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

<!-- Add new rows here as ADRs are written. Keep this table the only content of substance in this file. -->

## Known Debt (not yet ADR-worthy)

Stopgaps introduced during implementation that are deliberate but temporary — tracked here so they aren't lost, promoted to a full ADR only if reversing them turns out to be contested:

- **NotebookLM integration unverified against the live CLI**: `ai/notebooklm/client.py` now shells out to the real `nlm` CLI (`notebooklm-mcp-cli`) instead of a stub — see `docs/AI.md#routing-logic` and `docs/DEPLOYMENT.md` for the manual `nlm login` prerequisite. No `nlm` binary or authenticated profile has been available in any environment this was built/reviewed in, and the CLI's own docs don't pin down the exact `--json` response shape for `notebook create`/`source add`, so `_extract_id`'s key-name matching is defensive/best-effort rather than confirmed. Needs a live smoke-test the first time someone runs `nlm login` and indexes a real document; tighten `_extract_id` to the confirmed shape once that happens.
