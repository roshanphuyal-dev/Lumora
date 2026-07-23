---
name: review-pr
description: Review a pull request/diff against this repo's conventions (AGENTS.md, .claude/rules/*.md). Use when asked to review a PR, review a diff, or check a branch before merge.
---

# Review PR

## Objective
Review a change against `AGENTS.md#review-expectations` and the relevant `.claude/rules/*.md` checklists for the domains touched.

## Inputs
- A diff, branch, or PR reference.

## Outputs
- Findings list: correctness issues, convention violations, missing tests/docs, unrelated scope creep — each tied to a file/line.
- No praise, no scope creep into unrelated suggestions.

## Expected Quality
- Every finding is concrete (file:line + what's wrong + why it matters), not vague ("could be cleaner").
- Checks against the specific domain rule files for what's touched (backend.md/frontend.md/database.md/ai.md/security.md/testing.md/ui.md/git.md), not a generic pass.
- Confirms docs (`.claude/rules/documentation.md`) and tests (`.claude/rules/testing.md`) were updated alongside the code.

## Completion Checklist
- [ ] Checked for one-concern-per-PR (`.claude/rules/git.md`).
- [ ] Checked relevant domain rule file(s) for the files touched.
- [ ] Checked for missing tests on new logic.
- [ ] Checked for missing doc updates (`docs/*.md`, `CHANGELOG.md`).
- [ ] Checked for secrets/scope creep/unrelated changes.
