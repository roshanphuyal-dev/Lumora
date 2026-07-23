# ADR 0005: Why Gemini

## Status
Accepted

## Context
Needed a primary "teaching" model for explanations, quiz generation/grading, feedback, LaTeX generation, and adaptive tutoring — strong at structured JSON output, function calling, and image understanding, at a cost point sustainable for a free-tier-hosted product.

## Decision
Use Gemini 2.5 Flash as the primary tutor model, with OpenRouter (DeepSeek/Qwen) as fallback/cheap-tier.

## Alternatives Considered
- **GPT-4-class models as primary** — strong quality, but higher cost per token at the volume this product needs (every note/quiz/chat interaction), working against `docs/TOKEN_OPTIMIZATION.md` goals.
- **Open-weight model self-hosted** — no per-token cost, but requires GPU infra this project's Oracle Cloud free-tier deployment target doesn't have.

## Tradeoffs
Vendor dependency on Google's API availability/pricing changes — mitigated by the orchestration layer's OpenRouter fallback path (`docs/AI.md#routing-logic`).

## Consequences
All teaching/reasoning/grading tasks default to Gemini; the orchestration layer must handle graceful degradation to OpenRouter-routed models on rate-limit/outage, with a quality flag surfaced to the caller.
