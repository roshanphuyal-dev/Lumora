# ADR 0008: OpenCode Zen as Gemini Fallback

## Status
Accepted

## Context
`TaskType.TEACHING_EXPLANATION` routed to Gemini only, with no fallback (`docs/AI.md#routing-logic` step 5 was documented but never built). For local/free-tier development, Gemini's free-tier daily quota can be exhausted or the API can be rate-limited/unavailable, leaving the orchestrator with no way to answer a teaching-explanation request. `docs/AI.md`'s original plan named OpenRouter (DeepSeek/Qwen) as the fallback, but that integration was never built either.

## Decision
Add `ai/opencode_zen/client.py` (`OpenCodeZenClient`) wrapping OpenCode Zen's free-tier, OpenAI-compatible chat completions API (`https://opencode.ai/zen/v1/chat/completions`, default model `deepseek-v4-flash-free`). `ai/orchestrator/orchestrator.py`'s `_run_teaching_explanation` tries Gemini first; on any `GeminiError` (network failure, rate limit, quota exhausted — not currently distinguished) it falls back to OpenCode Zen, and vice versa if OpenCode Zen fails after being tried. Both providers share the same versioned prompt template (`ai/prompts/teaching_explanation_v1.py`) so answers are governed by an identical system prompt/contract regardless of which one responds.

## Alternatives Considered
- **Build the previously-planned OpenRouter fallback instead** — was the original plan (`ADR 0005`), but OpenRouter requires its own paid/API-key setup; OpenCode Zen's free tier was already available (`OPENCODE_ZEN_API_KEY` provisioned) and needed no additional account/billing setup for local dev.
- **Retry Gemini with backoff instead of switching providers** — doesn't help when the failure is a same-day quota exhaustion (retrying won't succeed until the quota resets), which is the primary failure mode this ADR targets for local/free-tier use.

## Tradeoffs
- OpenCode Zen's free models are explicitly time-limited ("available for a limited time while teams collect feedback" per their docs) and may use collected data to improve the model during the free period — acceptable for local dev, needs revisiting (a paid tier or different fallback) before handling real student data in production (`.claude/rules/ai.md` data-retention requirement).
- Two providers with different quality/latency profiles can now answer the same task type — `AIResponse.provider` surfaces which one actually responded, but no quality-degradation flag is surfaced to the caller yet.
- Adds a second HTTP-based provider dependency (`httpx`, new in `ai/pyproject.toml`) alongside the `google-genai` SDK.

## Consequences
`TaskType.TEACHING_EXPLANATION` requests only fail outright if *both* Gemini and OpenCode Zen fail. Future task types needing the same resilience should follow the same ordered-fallback pattern in their own orchestrator branch, rather than generalizing to an n-provider chain prematurely (only one task type needs this today).
