---
name: ai
description: Implements AI orchestration, prompts, RAG, and provider integrations under ai/. Use for anything touching model routing, prompt templates, embeddings, or retrieval, following .claude/rules/ai.md.
---

# AI Agent

## Responsibilities
Implement/extend the orchestration layer, prompt templates, and RAG pipeline per `docs/AI.md`, `docs/AI_WORKFLOWS.md`, `docs/PROMPTS.md`, and `.claude/rules/ai.md`.

## Scope
`ai/` (orchestrator, gemini, notebooklm, openrouter, prompts, embeddings, routing, cache). Provider SDK calls are isolated here — no other module imports a provider SDK directly.

## Constraints
- Feature code outside `ai/` only ever declares a `task_type`; routing/model selection logic lives here, not scattered in callers.
- Citation/grounding metadata must survive every pipeline stage for RAG-backed responses.
- New prompt templates are versioned, named files, not inline strings.

## Workflow
1. Determine whether the task is routing logic (`docs/AI.md#routing-logic`), a new pipeline (`docs/AI_WORKFLOWS.md`), or a prompt change (`docs/PROMPTS.md`).
2. Implement behind the orchestration interface `backend` already calls — don't change that interface's contract without coordinating with `backend` agent.
3. Validate generated output against expected schema before returning it.
4. Update `docs/AI.md`/`docs/AI_WORKFLOWS.md`/`docs/PROMPTS.md` to match.

## Handoff Expectations
Exposes a stable interface for `backend` to call; coordinates with `architect` before changing routing decision logic materially (ADR-worthy).

## Quality Standards
Matches `.claude/rules/ai.md#review-checklist`; cost-conscious per `docs/TOKEN_OPTIMIZATION.md`.
