"""Gemini provider client (ADR 0005).

The only place `google.genai` is imported (.claude/rules/ai.md) — nothing outside `ai/`
should import it directly. Wraps Gemini 3.5 Flash for the orchestrator's
`TaskType.TEACHING_EXPLANATION` task; the orchestrator (`ai/orchestrator/`) is the only
intended caller.

Model ID history: `gemini-2.5-flash` was retired for new/unused API keys ahead of its
official Oct 2026 shutdown date (Google returns 404 NOT_FOUND with "no longer available
to new users"). Confirmed live against `generativelanguage.googleapis.com` on 2026-08-10
that `gemini-3.5-flash` is the current stable flash-tier model that still serves this
project's key — see `docs/AI.md#model-roster--responsibilities`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from ai.prompts.chat_response_v1 import (
    SYSTEM_PROMPT as CHAT_SYSTEM_PROMPT,
)
from ai.prompts.chat_response_v1 import (
    render_user_prompt as render_chat_prompt,
)
from ai.prompts.teaching_explanation_v1 import SYSTEM_PROMPT, render_user_prompt

_MODEL_NAME = "gemini-3.5-flash"


class GeminiError(RuntimeError):
    """Raised when the Gemini API call fails, is misconfigured, or returns no usable text."""


class GeminiClient:
    """Thin wrapper around the `google-genai` SDK for teaching-explanation calls."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise GeminiError("GEMINI_API_KEY is not configured (see backend/.env.example).")
        self._client = genai.Client(api_key=resolved_key)

    async def generate_teaching_explanation(self, question: str, context: str = "") -> str:
        """Ask Gemini to explain `question`, optionally grounded in `context`.

        `context` is treated strictly as reference data by the prompt template
        (`ai/prompts/teaching_explanation_v1.py`), never as instructions.
        """
        user_prompt = render_user_prompt(question=question, context=context)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
        except Exception as exc:  # noqa: BLE001 - normalize every provider error to GeminiError
            raise GeminiError(f"Gemini generation failed: {exc}") from exc

        text = response.text
        if not text:
            raise GeminiError("Gemini returned an empty response.")
        return text

    async def stream_chat_response(
        self, *, question: str, context: str = "", history: str = ""
    ) -> AsyncIterator[str]:
        """Stream a multi-turn chat answer as provider-generated text fragments."""
        user_prompt = render_chat_prompt(question=question, context=context, history=history)
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT),
            )
            async for response in stream:
                if response.text:
                    yield response.text
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini streaming generation failed: {exc}") from exc
