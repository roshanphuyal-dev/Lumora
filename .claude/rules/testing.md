# Testing Rules

## Purpose
Enforcement checklist for `docs/TESTING.md`'s strategy — what a PR's test coverage must look like.

## Responsibilities
Ensure new logic is verified, bugs get regression coverage, and mocking stays limited to genuinely external dependencies.

## Coding Rules
- New backend business logic ships with `pytest` unit tests in the same PR.
- New frontend components with non-trivial logic ship with Vitest/RTL tests in the same PR.
- Integration tests touching the DB use real Postgres (Docker), never a mocked ORM session.

## Conventions
- Test files mirror the structure of the code they test (`backend/tests/` mirrors `backend/app/`).
- AI provider calls (Gemini/NotebookLM/OpenRouter/search) mocked/recorded in unit tests; a separate small smoke-test set makes real calls, run manually/scheduled — not on every PR.

## Best Practices
- A bug fix includes a regression test reproducing the original failure where feasible.
- UI changes are manually exercised in a running browser, not just type-checked, before being called done.

## Avoid
- Mocking the database.
- Skipping tests for AI orchestration/routing logic just because it "calls an external model" — test the routing decision logic directly, mock only the actual provider call.
- Claiming a UI feature works without having run it.

## Review Checklist
- [ ] New logic has tests in the same PR.
- [ ] Bug fixes include a regression test.
- [ ] No database mocking.
- [ ] AI provider calls mocked, but orchestration/routing logic itself is directly tested.
- [ ] Relevant suite (`docs/TESTING.md`) run and passing before requesting review.
