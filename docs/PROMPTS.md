# Prompts

## Purpose

The catalogue of actual prompt templates used across the AI pipelines — the concrete text/structure, not the routing logic that decides when to use them.

## What Belongs Here

- Named prompt templates, their variables, and their intended model target.
- Structured-output schemas (JSON shape) expected from a given prompt.
- Prompt engineering standards (how templates should be written/versioned).

## What Never Belongs Here

- Routing logic (`AI.md`).
- Pipeline sequencing (`AI_WORKFLOWS.md`).
- Cost tactics (`TOKEN_OPTIMIZATION.md`) — link instead of repeating "minimize few-shot examples" here.

## Structure

### Prompt Engineering Standards
- Every prompt template lives in `ai/prompts/` as versioned, named files — this doc indexes them, it doesn't duplicate their full text once the codebase exists.
- Prefer structured output (JSON schema / function calling) over free-text parsing.
- Keep system prompts stable and cacheable; vary only the user/context portion per request.
- Templates take named variables, never string-concatenated ad hoc — makes them testable and reusable across features.
- Version prompts (`v1`, `v2`, ...) when changing behavior materially, so regressions are traceable.

### Template Index (fill in as implemented)

| Template | Target Model | Used By | Output Shape |
|---|---|---|---|
| `note_generation` | Gemini | Notes/Study Guide workflow | structured markdown |
| `flashcard_generation` | Gemini + NotebookLM | Flashcards workflow | JSON list `{front, back, source_citation}` |
| `quiz_generation` | Gemini | Quiz workflow | JSON list of question objects |
| `quiz_grading` | Gemini | Evaluation workflow | JSON `{score, mistakes[], feedback}` |
| `chat_response` | Gemini | AI Chat workflow | markdown + citations |
| `formatting_pass` | DeepSeek/Qwen | any cheap-tier reformat step | markdown/JSON |

<!-- TODO: fill in exact prompt text once ai/prompts/ is implemented -->
<!-- TODO: add versioning changelog per template once iterated on -->
