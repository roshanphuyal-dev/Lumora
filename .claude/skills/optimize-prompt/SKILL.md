---
name: optimize-prompt
description: Optimize an existing AI prompt template for cost/quality per docs/TOKEN_OPTIMIZATION.md and docs/PROMPTS.md. Use when asked to optimize, tighten, or reduce cost of a prompt.
---

# Optimize Prompt

## Objective
Reduce token cost and/or improve reliability of an existing prompt template in `ai/prompts/`, per `docs/TOKEN_OPTIMIZATION.md#prompt-optimization` and `docs/PROMPTS.md#prompt-engineering-standards`.

## Inputs
- The template name/file to optimize.
- Whether the goal is cost, quality, or both (they can trade off).

## Outputs
- Updated template: fewer/no unnecessary few-shot examples, structured output preferred over free text, redundant context stripped, reusable fragments extracted where applicable.
- Version bump on the template (`docs/PROMPTS.md#prompt-engineering-standards`) if behavior changes materially.

## Expected Quality
- Output schema/contract unchanged unless the task explicitly includes changing it.
- Measurable reduction in prompt token count or clearer justification for why length was necessary.
- No loss of grounding/citation behavior for RAG-dependent templates.

## Completion Checklist
- [ ] Template still produces output matching its documented schema (`docs/PROMPTS.md#template-index`).
- [ ] Few-shot examples minimized to what's actually needed.
- [ ] Version bumped if behavior changed.
- [ ] `docs/PROMPTS.md` template index updated if the output shape changed.
