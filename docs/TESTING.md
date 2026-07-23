# Testing

## Purpose

The testing strategy reference: what gets tested, how, and with what tools — so "is this covered" and "how do I run the tests" always have one answer.

## What Belongs Here

- Test types and tools per layer.
- Coverage expectations.
- Commands to run each suite.

## What Never Belongs Here

- CI pipeline wiring (`DEPLOYMENT.md`).
- Feature acceptance criteria (`FEATURES.md`).

## Structure

### Backend
- Unit tests: `pytest`, colocated in `backend/tests/` mirroring `backend/app/` structure.
- Integration tests: real Postgres (Docker, not sqlite-in-memory) for anything touching the DB — don't mock the database (mocked-DB tests have historically diverged from real migration behavior in similar stacks; catch schema issues for real).
- AI provider calls (Gemini/NotebookLM/OpenRouter/search APIs): mocked/recorded (VCR-style) in unit tests — these are the genuinely external/costly dependencies worth mocking. A small set of real-call smoke tests should run separately (manually or on a schedule), not on every PR, to avoid burning API budget.
- Run: `cd backend && uv run pytest`

### Frontend
- Component tests: Vitest + React Testing Library.
- E2E: Playwright for critical golden paths (upload → notebook → generate notes; quiz attempt → submission → score) once those flows exist.
- Run: `cd frontend && pnpm test` (unit/component), `pnpm test:e2e` (once configured).

### Coverage Expectations
- New business logic (backend services, AI orchestration, quiz grading) ships with unit tests in the same PR.
- Bug fixes include a regression test reproducing the bug where feasible.
- UI changes are manually exercised in a running browser before being marked done (per global engineering practice) — type checks and unit tests verify correctness, not that a feature actually works end-to-end.
- No hard coverage percentage gate yet; revisit once the codebase has enough surface area to make one meaningful.

### What NOT to Mock
- The database (use real Postgres via Docker).
- Internal orchestration logic (test it directly, not through a mocked interface).
Mock only genuinely external, costly, or non-deterministic dependencies: third-party AI providers, search APIs, image APIs.

<!-- TODO: add Playwright golden-path suite once Phase 1 UI exists -->
<!-- TODO: decide on VCR-style cassette tool for AI provider tests once backend AI calls are implemented -->
