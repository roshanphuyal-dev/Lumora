"""OpenCode Zen provider client (ADR 0008).

The only place OpenCode Zen's API is called (.claude/rules/ai.md) — nothing outside `ai/`
should call it directly. Used as the orchestrator's fallback for `TaskType.TEACHING_EXPLANATION`
when Gemini is unavailable/rate-limited/quota-exhausted (`ai/orchestrator/orchestrator.py`),
and vice versa.

OpenCode Zen (https://opencode.ai/docs/zen/) exposes an OpenAI-compatible chat completions
endpoint with a roster of free models. `deepseek-v4-flash-free` is used here as a fast,
general-purpose default — swap `_MODEL_NAME` if a different free model fits better.

Per OpenCode Zen's docs, free-tier models may have collected data used to improve the
model during their free period; some free models explicitly warn against personal/
confidential data. Treat this the same as any other AI provider under
`docs/SECURITY.md#ai-specific-risks` — reference material stays data, never instructions
(enforced by the shared prompt template below, not re-implemented here).
"""

from __future__ import annotations

import os

import httpx

from ai.prompts.teaching_explanation_v2 import SYSTEM_PROMPT, render_user_prompt

_API_URL = "https://opencode.ai/zen/v1/chat/completions"
_MODEL_NAME = "deepseek-v4-flash-free"
_TIMEOUT_SECONDS = 30.0


class OpenCodeZenError(RuntimeError):
    """Raised when the OpenCode Zen API call fails, is misconfigured, or returns no usable text."""


class OpenCodeZenClient:
    """Thin wrapper around OpenCode Zen's OpenAI-compatible chat completions API."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("OPENCODE_ZEN_API_KEY")
        if not resolved_key:
            raise OpenCodeZenError(
                "OPENCODE_ZEN_API_KEY is not configured (see backend/.env.example)."
            )
        self._api_key = resolved_key

    async def generate_teaching_explanation(
        self,
        question: str,
        context: str = "",
        *,
        explanation_depth: str | None = None,
        explanation_style: str | None = None,
    ) -> str:
        """Ask an OpenCode Zen free model to explain `question`, optionally grounded in `context`.

        Uses the same named prompt template as `ai.gemini.client.GeminiClient` (`ai/prompts/
        teaching_explanation_v1.py`) so both providers answer to an identical system prompt/
        contract — feature code shouldn't see a difference beyond which provider is stamped
        on the response (`ai/orchestrator/schemas.py:ProviderName`).
        """
        user_prompt = render_user_prompt(
            question=question,
            context=context,
            explanation_depth=explanation_depth,
            explanation_style=explanation_style,
        )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.post(
                    _API_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": _MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 - normalize every provider error to OpenCodeZenError
            raise OpenCodeZenError(f"OpenCode Zen generation failed: {exc}") from exc

        text = _extract_text(payload)
        if not text:
            raise OpenCodeZenError(f"OpenCode Zen returned no usable text: {payload!r}")
        return text


def _extract_text(payload: dict) -> str | None:
    """Pull the assistant message content out of an OpenAI-compatible chat completion response."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) and content else None
