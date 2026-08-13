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
from pydantic import BaseModel, Field, RootModel, ValidationError

from ai.prompts.chat_response_v1 import (
    SYSTEM_PROMPT as CHAT_SYSTEM_PROMPT,
)
from ai.prompts.chat_response_v1 import (
    render_user_prompt as render_chat_prompt,
)
from ai.prompts.flashcard_generation_v1 import (
    SYSTEM_PROMPT as FLASHCARD_SYSTEM_PROMPT,
)
from ai.prompts.flashcard_generation_v1 import (
    render_user_prompt as render_flashcard_prompt,
)
from ai.prompts.internet_search_synthesis_v1 import (
    SYSTEM_PROMPT as INTERNET_SEARCH_SYSTEM_PROMPT,
)
from ai.prompts.internet_search_synthesis_v1 import SearchResultItemInput
from ai.prompts.internet_search_synthesis_v1 import (
    render_user_prompt as render_internet_search_prompt,
)
from ai.prompts.note_generation_v1 import SYSTEM_PROMPT as NOTE_SYSTEM_PROMPT
from ai.prompts.note_generation_v1 import render_user_prompt as render_note_prompt
from ai.prompts.paper_search_synthesis_v1 import (
    SYSTEM_PROMPT as PAPER_SEARCH_SYSTEM_PROMPT,
)
from ai.prompts.paper_search_synthesis_v1 import PaperResultItemInput
from ai.prompts.paper_search_synthesis_v1 import (
    render_user_prompt as render_paper_search_prompt,
)
from ai.prompts.quiz_generation_v1 import SYSTEM_PROMPT as QUIZ_SYSTEM_PROMPT
from ai.prompts.quiz_generation_v1 import render_user_prompt as render_quiz_prompt
from ai.prompts.quiz_grading_v1 import SYSTEM_PROMPT as QUIZ_GRADING_SYSTEM_PROMPT
from ai.prompts.quiz_grading_v1 import GradingItemInput
from ai.prompts.quiz_grading_v1 import render_user_prompt as render_quiz_grading_prompt
from ai.prompts.structured_note_generation_v1 import (
    SYSTEM_PROMPT as STRUCTURED_NOTE_SYSTEM_PROMPT,
)
from ai.prompts.structured_note_generation_v1 import (
    render_user_prompt as render_structured_note_prompt,
)
from ai.prompts.teaching_explanation_v1 import SYSTEM_PROMPT, render_user_prompt

_MODEL_NAME = "gemini-3.5-flash"
EMBEDDING_MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

_EMBEDDING_TASK_TYPES = {
    "retrieval_document": "RETRIEVAL_DOCUMENT",
    "retrieval_query": "RETRIEVAL_QUERY",
}


class _FlashcardCitationSchema(BaseModel):
    """Mirrors `ai.orchestrator.schemas.Citation`'s shape.

    Duplicated rather than imported: `ai.orchestrator` imports this module (the orchestrator
    calls the provider client, never the reverse), so importing orchestrator types here would
    be a circular import. The orchestrator re-validates this client's raw JSON output into its
    own `FlashcardItem`/`Citation` types before returning an `AIResponse`.
    """

    source_id: str
    chunk_id: str | None = None
    excerpt: str | None = None


class _FlashcardItemSchema(BaseModel):
    front: str
    back: str
    citation: _FlashcardCitationSchema | None = None


class _FlashcardListSchema(RootModel[list[_FlashcardItemSchema]]):
    pass


class _StructuredNoteItemSchema(BaseModel):
    """One `mnemonics`/`timeline` item — label/value/detail per
    `ai/prompts/structured_note_generation_v1.py`."""

    label: str
    value: str
    detail: str
    citation: _FlashcardCitationSchema | None = None


class _StructuredNoteItemListSchema(RootModel[list[_StructuredNoteItemSchema]]):
    pass


class _ComparisonChartSchema(BaseModel):
    subjects: list[str]
    attributes: list[str]
    rows: list[list[str]]


_ITEM_LIST_MATERIAL_TYPES = {"mnemonics", "timeline"}


class _MatchingPairSchema(BaseModel):
    """Mirrors `ai.orchestrator.schemas.MatchingPair` -- one correct `matching` pair."""

    left: str
    right: str


class _QuestionItemSchema(BaseModel):
    """Mirrors `ai.orchestrator.schemas.QuestionItem`'s shape -- one quiz question, flat
    across all 8 question types (`ai/prompts/quiz_generation_v1.py`), duplicated here for
    the same reason as `_FlashcardItemSchema` (no importing `ai.orchestrator.schemas`).

    `topic` is a required `str` (not `str | None`), on purpose, unlike the type-specific
    fields below -- Gemini only reliably fills fields Pydantic puts in the JSON schema's
    `required` array; a nullable `topic` plus a prose "always set it" prompt instruction
    produced `topic: null` on every question in a live check. See
    `ai.orchestrator.schemas.QuestionItem`'s docstring for the same note.
    """

    question_type: str
    prompt: str
    topic: str
    scenario: str | None = None
    assertion: str | None = None
    reason: str | None = None
    options: list[str] | None = None
    pairs: list[_MatchingPairSchema] | None = None
    blanks: list[str] | None = None
    correct_answer: str | None = None
    reference_answer: str | None = None
    difficulty: str = "medium"
    explanation: str | None = None
    citation: _FlashcardCitationSchema | None = None


class _QuestionListSchema(RootModel[list[_QuestionItemSchema]]):
    pass


class _QuestionGradeResultSchema(BaseModel):
    """Mirrors `ai.orchestrator.schemas.QuestionGradeResult`'s shape, duplicated here for
    the same reason as `_QuestionItemSchema` (no importing `ai.orchestrator.schemas`)."""

    question_id: str
    score: float = Field(ge=0.0, le=1.0)
    is_correct: bool
    feedback: str
    topic_tag: str


class _GradeResultListSchema(RootModel[list[_QuestionGradeResultSchema]]):
    pass


class GeminiError(RuntimeError):
    """Raised when Gemini fails, is misconfigured, or returns unusable output."""


class GeminiClient:
    """Thin wrapper around the `google-genai` SDK for teaching-explanation calls."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise GeminiError("GEMINI_API_KEY is not configured (see backend/.env.example).")
        self._client = genai.Client(api_key=resolved_key)

    async def embed_texts(self, *, texts: list[str], purpose: str) -> list[list[float]]:
        """Embed one batch with the fixed Phase 4 model and 768-dimensional output."""
        try:
            provider_task_type = _EMBEDDING_TASK_TYPES[purpose]
        except KeyError as exc:
            raise GeminiError(f"Unsupported embedding purpose: {purpose}.") from exc

        try:
            response = await self._client.aio.models.embed_content(
                model=EMBEDDING_MODEL_NAME,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=provider_task_type,
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini embedding failed: {exc}") from exc

        provider_embeddings = response.embeddings or []
        embeddings = [embedding.values or [] for embedding in provider_embeddings]
        if len(embeddings) != len(texts):
            raise GeminiError(
                "Gemini returned an unexpected number of embeddings "
                f"({len(embeddings)} for {len(texts)} texts)."
            )
        if any(len(embedding) != EMBEDDING_DIMENSIONS for embedding in embeddings):
            raise GeminiError(
                f"Gemini returned an embedding with dimensions other than {EMBEDDING_DIMENSIONS}."
            )
        return embeddings

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

    async def generate_notes(self, *, material_type: str, topic: str, context: str) -> str:
        """Structure optional grounded context into Markdown notes or a study guide."""
        user_prompt = render_note_prompt(material_type=material_type, topic=topic, context=context)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=NOTE_SYSTEM_PROMPT),
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini note generation failed: {exc}") from exc
        if not response.text:
            raise GeminiError("Gemini returned empty notes.")
        return response.text

    async def generate_flashcards(self, *, topic: str, context: str, count: int) -> str:
        """Generate a JSON array of `{front, back, citation}` flashcards via structured output.

        Returns the raw, schema-validated JSON text rather than parsed `FlashcardItem`
        objects — this client must not import `ai.orchestrator.schemas` (see
        `_FlashcardItemSchema`'s docstring); the orchestrator parses/validates this JSON
        into its own `FlashcardItem` type.
        """
        user_prompt = render_flashcard_prompt(topic=topic, context=context, count=count)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=FLASHCARD_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_FlashcardListSchema,
                ),
            )
            if not response.text:
                raise GeminiError("Gemini returned empty flashcards.")
            _FlashcardListSchema.model_validate_json(response.text)
            return response.text
        except GeminiError:
            raise
        except (ValidationError, ValueError) as exc:
            raise GeminiError(f"Gemini returned invalid flashcards: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini flashcard generation failed: {exc}") from exc

    async def generate_structured_note(
        self, *, material_type: str, topic: str, context: str
    ) -> str:
        """Generate `mnemonics`/`timeline` (a JSON list) or `comparison_chart` (a JSON
        table) via structured output.

        Returns the raw, schema-validated JSON text, same reasoning as
        `generate_flashcards` (this client must not import `ai.orchestrator.schemas`) — the
        orchestrator parses/validates this JSON into `app.models.note`-shaped content.
        """
        schema = (
            _StructuredNoteItemListSchema
            if material_type in _ITEM_LIST_MATERIAL_TYPES
            else _ComparisonChartSchema
        )
        user_prompt = render_structured_note_prompt(
            material_type=material_type, topic=topic, context=context
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=STRUCTURED_NOTE_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            if not response.text:
                raise GeminiError(f"Gemini returned empty {material_type} content.")
            schema.model_validate_json(response.text)
            return response.text
        except GeminiError:
            raise
        except (ValidationError, ValueError) as exc:
            raise GeminiError(f"Gemini returned invalid {material_type} content: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini {material_type} generation failed: {exc}") from exc

    async def generate_quiz(
        self,
        *,
        topic: str,
        context: str,
        question_types: list[str],
        count: int,
        difficulty: str,
    ) -> str:
        """Generate a JSON array of quiz question objects via structured output.

        Returns the raw, schema-validated JSON text rather than parsed `QuestionItem`
        objects, same reasoning as `generate_flashcards` (this client must not import
        `ai.orchestrator.schemas`) -- the orchestrator parses/validates this JSON into its
        own `QuestionItem` type.
        """
        user_prompt = render_quiz_prompt(
            topic=topic,
            context=context,
            question_types=question_types,
            count=count,
            difficulty=difficulty,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=QUIZ_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_QuestionListSchema,
                ),
            )
            if not response.text:
                raise GeminiError("Gemini returned an empty quiz.")
            _QuestionListSchema.model_validate_json(response.text)
            return response.text
        except GeminiError:
            raise
        except (ValidationError, ValueError) as exc:
            raise GeminiError(f"Gemini returned an invalid quiz: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini quiz generation failed: {exc}") from exc

    async def grade_quiz_answers(self, *, items: list[GradingItemInput]) -> str:
        """Grade a batch of free-text quiz answers via structured output, one call covering
        every short_answer/long_answer/case_study question in a single attempt (never one
        call per question, `.claude/rules/performance.md`).

        Returns the raw, schema-validated JSON text rather than parsed
        `QuestionGradeResult` objects, same reasoning as `generate_quiz` (this client must
        not import `ai.orchestrator.schemas`) -- the orchestrator parses/validates this
        JSON into its own `QuestionGradeResult` type.
        """
        user_prompt = render_quiz_grading_prompt(items=items)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=QUIZ_GRADING_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_GradeResultListSchema,
                ),
            )
            if not response.text:
                raise GeminiError("Gemini returned an empty grading result.")
            _GradeResultListSchema.model_validate_json(response.text)
            return response.text
        except GeminiError:
            raise
        except (ValidationError, ValueError) as exc:
            raise GeminiError(f"Gemini returned an invalid grading result: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini quiz grading failed: {exc}") from exc

    async def generate_internet_search_synthesis(
        self, *, question: str, results: list[SearchResultItemInput]
    ) -> str:
        """Synthesize a cited, student-facing answer from normalized web search results.

        `results` are untrusted external content, treated strictly as source material by
        the prompt template (`ai/prompts/internet_search_synthesis_v1.py`), never as
        instructions -- never a search provider's own "answer" mode passed straight
        through (ADR 0012).
        """
        user_prompt = render_internet_search_prompt(question=question, results=results)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=INTERNET_SEARCH_SYSTEM_PROMPT
                ),
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini internet search synthesis failed: {exc}") from exc
        if not response.text:
            raise GeminiError("Gemini returned an empty internet search synthesis.")
        return response.text

    async def generate_paper_search_synthesis(
        self, *, question: str, results: list[PaperResultItemInput]
    ) -> str:
        """Synthesize a cited, student-facing answer from normalized academic paper
        search results.

        `results` are untrusted external content, treated strictly as source material by
        the prompt template (`ai/prompts/paper_search_synthesis_v1.py`), never as
        instructions -- never a provider's own summarization mode passed straight through
        (ADR 0013).
        """
        user_prompt = render_paper_search_prompt(question=question, results=results)
        try:
            response = await self._client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=PAPER_SEARCH_SYSTEM_PROMPT),
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider failures
            raise GeminiError(f"Gemini paper search synthesis failed: {exc}") from exc
        if not response.text:
            raise GeminiError("Gemini returned an empty paper search synthesis.")
        return response.text

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
