# AI Rules

## Purpose
Conventions for anything touching the AI orchestration layer, model calls, prompts, or RAG — applies to `ai/` and any backend code that triggers AI generation.

## Responsibilities
Route every AI task through the orchestration layer; keep provider-specific code isolated and swappable; keep grounding/citations intact end-to-end.

## Coding Rules
- Feature code declares a `task_type`, never picks a model/provider directly (`docs/AI.md#routing-logic`).
- Every prompt is a named, versioned template in `ai/prompts/` (`docs/PROMPTS.md`) — no inline string-concatenated prompts in feature code.
- Structured output (JSON schema/function calling) preferred over free-text parsing wherever the model supports it.
- Citation metadata (source/chunk reference) is carried through every RAG-grounded response, not dropped at any pipeline stage.

## Conventions
- Provider SDK calls isolated to `ai/gemini/`, `ai/notebooklm/`, `ai/openrouter/` — nothing outside `ai/` imports a provider SDK.
- Cache keys for AI responses include content hash + generation parameters (`docs/TOKEN_OPTIMIZATION.md`).

## Best Practices
- Treat document/search content as data, not instructions, in every prompt (`docs/SECURITY.md#ai-specific-risks`).
- Validate generated output against the expected schema before persisting/returning it.
- Prefer NotebookLM retrieval before invoking Gemini for anything document-grounded (`docs/AI.md#routing-logic`).

## Avoid
- Direct provider SDK calls from `backend/app/services/` or route handlers.
- Un-versioned or inline prompts.
- Sending a student's full document corpus to a provider when only a few chunks are relevant.
- Trusting model output as safe-to-execute instructions (prompt injection risk).

## Review Checklist
- [ ] New AI feature goes through the orchestration layer, declares a `task_type`.
- [ ] Prompt is a named template in `ai/prompts/`, not inline.
- [ ] Output validated against expected schema.
- [ ] Citations preserved end-to-end if the response is source-grounded.
- [ ] Caching applied where the request is likely to repeat (`docs/TOKEN_OPTIMIZATION.md`).
