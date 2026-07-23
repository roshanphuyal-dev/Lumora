# Contributing

## Local Setup

See [`README.md`](README.md#installation). TL;DR: `uv sync` (backend), `pnpm install` (frontend), or `docker compose up` for everything.

## Branching Strategy

Trunk-based development:
- `main` is always deployable.
- Work happens on short-lived branches: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`.
- Branch from `main`, open a PR back into `main`, squash-merge once approved and green.
- No long-lived `develop`/environment branches — deploys are tagged releases off `main` (see `docs/DEPLOYMENT.md`).

## Commit Convention

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`. Scope is optional: `feat(quiz): add adaptive difficulty selection`.

## Release Process

- Tag releases on `main` with SemVer (`v0.1.0`).
- Every release updates `CHANGELOG.md`: move `[Unreleased]` entries under the new version header with today's date.
- Deployment pipeline detail: `docs/DEPLOYMENT.md`.

## Pull Request Process

1. One concern per PR (one feature, one fix, one refactor — not bundled).
2. PR description explains *why*; the diff already shows *what*.
3. Update relevant `docs/*.md` and `CHANGELOG.md` in the same PR as the code change.
4. Ensure tests pass locally (`docs/TESTING.md` for commands) before requesting review.
5. Address review feedback with new commits; don't force-push during active review.

## Dependency Policy

- Backend: add via `uv add <package>`, commit the resulting lockfile change. Justify new runtime dependencies in the PR description (what it replaces or enables).
- Frontend: add via `pnpm add <package>`, commit `pnpm-lock.yaml`. Prefer existing stack primitives (shadcn/ui, TanStack Query, Framer Motion) over new UI libraries.
- Avoid dependencies that duplicate something already in `docs/TECH_STACK.md` — propose an ADR (`docs/adr/`) if you believe a stack choice should change.
- Pin major versions; review `CHANGELOG.md`/release notes of a dependency before bumping a major version.

## Code Review Expectations

See [`AGENTS.md`](AGENTS.md#review-expectations) and `.claude/agents/reviewer.md` for the full checklist.

## Documentation Expectations

See [`AGENTS.md`](AGENTS.md#documentation-expectations). Docs are not optional follow-up work — they ship with the code they describe.
