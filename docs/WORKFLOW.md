# Development Workflow

## Purpose

The day-to-day mechanics of how work moves from idea to merged code — branching, review, and the human/agent collaboration loop specific to this repo. Complements `CONTRIBUTING.md` (which is the contributor-facing quick reference); this doc is the fuller explanation.

## What Belongs Here

- Branching/PR mechanics in detail.
- How human + AI-agent collaboration is expected to work in this repo.
- Definition of done for a unit of work.

## What Never Belongs Here

- Release/versioning policy detail already covered in `CONTRIBUTING.md#release-process` — link, don't repeat.
- Testing strategy (`TESTING.md`).

## Structure

### Branching
Trunk-based (`CONTRIBUTING.md#branching-strategy`): `main` always deployable, short-lived `feat/`/`fix/`/`docs/`/`chore/` branches, squash-merge PRs.

### Working with AI Coding Agents
- Any agent (Claude Code or otherwise) starts a non-trivial task by reading `CLAUDE.md`/`AGENTS.md` and the relevant `docs/*.md` for the area being touched — not by guessing conventions from a single file.
- Architecture-level, multi-file, or new-dependency work gets a plan presented for approval before implementation (see global engineering practice already in effect for this repo's Claude Code sessions).
- Localized work (bug fixes, docs updates, formatting, tests, established patterns) proceeds directly without a planning pause.
- Agent-authored changes follow the same review bar as human-authored ones — no lower scrutiny because "an AI wrote it."

### Definition of Done
A unit of work is done when: it does one thing, has tests (`docs/TESTING.md`), updates the docs it affects, updates `CHANGELOG.md` if user-facing, and passes lint/tests locally before review.

### Handling Disagreement with Documented Convention
Propose the change via ADR (`docs/DECISIONS.md`) rather than silently diverging — conventions in this repo are meant to be living, not fixed in stone, but changes should be traceable.

<!-- TODO: add async/sync collaboration norms once a second contributor joins -->
