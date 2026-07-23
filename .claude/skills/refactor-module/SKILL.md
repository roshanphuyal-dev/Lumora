---
name: refactor-module
description: Refactor an existing module without changing its external behavior. Use when asked to refactor, clean up, or restructure existing code.
---

# Refactor Module

## Objective
Improve a module's internal structure/readability without changing observable behavior, per `AGENTS.md#development-philosophy`.

## Inputs
- The module/file(s) to refactor.
- The specific pain point motivating the refactor (if given) — refactors should solve a real problem, not speculative future needs.

## Outputs
- Restructured code with identical external behavior (same public API/contracts unless the refactor's explicit goal is to change them).
- Existing tests still passing, unmodified in intent (only updated if the refactor legitimately changes internal seams tests reach into).

## Expected Quality
- No behavior change unless explicitly scoped as part of the task.
- No unrelated scope creep — touch only what's needed for the stated refactor goal.
- Simpler/more consistent with existing patterns after, not just different.

## Completion Checklist
- [ ] All existing tests pass unchanged (or updated only where legitimately necessary).
- [ ] No behavior change outside what was explicitly requested.
- [ ] No unrelated files touched.
- [ ] Follows the domain's `.claude/rules/*.md` conventions.
