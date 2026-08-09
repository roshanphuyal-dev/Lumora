# AGENTS.md

Shared source of truth for **any** AI coding agent working in this repo — Claude Code, Cursor, Codex, Gemini CLI, Windsurf, or others. Tool-specific detail (Claude Code rules/skills/subagents) lives in `.claude/`; this file is the tool-agnostic contract every agent is expected to honor.

## Project Conventions

- Read `CLAUDE.md` (or this file, if your tool doesn't read `CLAUDE.md`) before making changes — it links to all deeper docs in `docs/`.
- Match existing patterns in the file/module you're touching before introducing a new one. If no pattern exists yet, check `docs/ARCHITECTURE.md` and `.claude/rules/` for the intended one.
- Domain vocabulary must match `docs/GLOSSARY.md` (Notebook vs Document vs Source vs Chunk vs Embedding, etc.).
- All AI-feature calls go through the orchestration layer described in `docs/AI.md` — never call a model provider directly from feature/business logic.
- All schema changes are migrations (`database/`), never manual DB edits.

## Development Philosophy

- Solve only the requested problem. No speculative abstractions, no unrequested refactors, no "while I'm here" scope creep — flag unrelated issues instead of fixing them inline.
- Simplest correct solution first. Prefer duplication over a premature abstraction for anything appearing fewer than ~3 times.
- Don't add error handling/validation for cases that can't occur given the caller's guarantees. Validate at system boundaries (user input, external API responses), trust internal contracts.
- No dead code, no commented-out code, no backwards-compatibility shims for code that has no external consumers yet.

## Expected Code Quality

- Backend: type-hinted Python, passes `ruff check` + `ruff format`, no bare `except:`, async I/O for anything touching the DB/network/model APIs.
- Frontend: typed TypeScript (no `any` without a comment justifying it), functional components, no prop-drilling past 2 levels (lift to context/query cache instead).
- Every public function/endpoint/component should be understandable from its name + types without needing a comment explaining "what" — comments are reserved for non-obvious "why."
- No hardcoded secrets, API keys, or credentials — ever, including in tests/fixtures.
- Never read `.env` files (only `.env.example`) — they hold real secrets, not just documentation of required keys.

## Review Expectations

- A change is reviewable if it does one thing: one feature, one fix, one refactor — not bundled.
- PR description states *why*, not just *what* (the diff already shows what).
- Reviewer (human or agent) checks: correctness, adherence to `.claude/rules/*.md` for the touched domain, test coverage for new logic, no unrelated file churn.
- See `.claude/agents/reviewer.md` for the detailed review checklist used by the Claude Code reviewer subagent — the same bar applies regardless of which agent authored the change.

## Documentation Expectations

- Code and its documentation change together, in the same PR — not as a follow-up.
- New architectural or dependency decisions get an ADR in `docs/adr/` (template: `docs/adr/0000-template.md`), indexed in `docs/DECISIONS.md`.
- User-facing changes get a `CHANGELOG.md` entry under `[Unreleased]`.
- Don't duplicate content across docs — link instead. If you find yourself repeating a paragraph, it belongs in one canonical doc, referenced from the others.

## Testing Expectations

- New logic ships with tests in the same PR (unit tests for backend/AI logic, component tests for frontend, see `docs/TESTING.md`).
- Don't mock what you can integration-test cheaply (e.g. a local Postgres via Docker) — mocks are for genuinely external/costly dependencies (Gemini, NotebookLM, search APIs).
- A bug fix includes a regression test reproducing the bug, where feasible.
- Run the relevant test suite before considering a task done (`docs/TESTING.md` has the commands); don't claim a UI change works without actually exercising it.

## Handoff Between Agents

Multiple agents/tools may touch this repo over time. To keep handoffs clean:
- Leave the repo in a working state (tests pass, no half-finished migrations) before ending a session.
- Note any deliberate incompleteness in the relevant `docs/` TODO or the PR description — don't leave silent gaps.
- If you disagree with a documented convention, propose the change in `docs/DECISIONS.md`/an ADR rather than silently diverging.
