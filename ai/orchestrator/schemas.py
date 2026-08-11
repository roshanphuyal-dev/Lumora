"""Request/response schemas for the orchestration layer.

`AIResponse` is the normalized shape every `run_task` call returns, regardless of which
provider handled it — feature code should never need to branch on provider to read a
response. Citation metadata is always present (possibly empty) so it survives every
pipeline stage per `.claude/rules/ai.md`.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from ai.orchestrator.task_types import TaskType


class ProviderName(enum.StrEnum):
    """Which provider actually produced an `AIResponse`.

    Informational only (logging/debugging) — feature code should not branch on this.
    """

    NOTEBOOKLM = "notebooklm"
    GEMINI = "gemini"
    OPENCODE_ZEN = "opencode_zen"
    WIKIMEDIA = "wikimedia"
    OPENVERSE = "openverse"


class Citation(BaseModel):
    """A source/chunk reference backing a grounded response (.claude/rules/ai.md)."""

    source_id: str
    chunk_id: str | None = None
    excerpt: str | None = None


class AIResponse(BaseModel):
    """Normalized response shape returned by every `ai.orchestrator.run_task` call."""

    task_type: TaskType
    provider: ProviderName
    content: str
    citations: list[Citation] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentIndexRequest(BaseModel):
    """Input for `TaskType.DOCUMENT_INDEX` — one already-uploaded local file to index.

    `notebooklm_notebook_id` is the remote NotebookLM notebook to index into. Resolving
    it (creating a remote notebook on first use) is a notebook-level concern, not a
    per-document one — callers must resolve it via
    `ai.notebooklm.client.NotebookLMClient.ensure_remote_notebook` before building this
    request, not as part of `run_task`.

    `file_path` must be a local filesystem path, not raw bytes/text — see
    `ai/notebooklm/client.py:NotebookLMClient.index_document` for why (the `nlm` CLI
    uploads via `--file <path>`, it has no bytes/stdin mode). Callers holding only
    document bytes (e.g. from `FileStorage.download`) must write them to a temp file
    first.
    """

    document_id: str
    notebooklm_notebook_id: str
    file_path: str


class NotebookQueryRequest(BaseModel):
    """Input for `TaskType.NOTEBOOK_QUERY` — ask a question against a notebook's already-
    indexed sources. Retrieval only; hand the result to `TEACHING_EXPLANATION` as `context`
    for teaching-framed phrasing (`docs/AI.md#routing-logic` step 1).
    """

    notebooklm_notebook_id: str
    question: str


class TeachingExplanationRequest(BaseModel):
    """Input for `TaskType.TEACHING_EXPLANATION`.

    A student question plus optional grounded context (e.g. chunks previously
    retrieved from NotebookLM).
    """

    question: str
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)


class ChatResponseRequest(BaseModel):
    """Latest question plus bounded history and optional NotebookLM grounding."""

    question: str
    context: str = ""
    history: str = ""
    citations: list[Citation] = Field(default_factory=list)


class AIStreamChunk(BaseModel):
    """One normalized text fragment from a streaming orchestration task."""

    content: str
    provider: ProviderName


class NotesGenerationRequest(BaseModel):
    """Input for `TaskType.NOTES_GENERATION` — grounded NotebookLM content to structure.

    `material_type` is `"note"` or `"study_guide"` (`app.models.note.NoteMaterialType`,
    kept as a plain `str` here so `ai/` doesn't import backend model enums).
    """

    material_type: str
    topic: str = ""
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)


class FlashcardItem(BaseModel):
    """One generated flashcard — the structured-output contract Gemini must satisfy."""

    front: str
    back: str
    citation: Citation | None = None


class FlashcardGenerationRequest(BaseModel):
    """Input for `TaskType.FLASHCARD_GENERATION` — grounded NotebookLM content to turn
    into a flashcard set.
    """

    topic: str = ""
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)
    count: int = 12


class StructuredNoteGenerationRequest(BaseModel):
    """Input for `TaskType.STRUCTURED_NOTE_GENERATION` — grounded content to turn into a
    non-Markdown study aid: "mnemonics"/"timeline" (a JSON list) or "comparison_chart" (a
    single JSON table). `material_type` is an `app.models.note.NoteMaterialType` value,
    kept as `str` for the same reason as `NotesGenerationRequest.material_type`.
    """

    material_type: str
    topic: str = ""
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)


QUESTION_TYPES = (
    "mcq",
    "true_false",
    "fill_blank",
    "matching",
    "short_answer",
    "long_answer",
    "case_study",
    "assertion_reason",
)
"""The 8 supported quiz question shapes (`docs/AI_WORKFLOWS.md#3`).

Kept as a plain tuple of `str`, not an enum, for the same reason as
`NotesGenerationRequest.material_type` -- `ai/` doesn't import backend model enums, and a
future `app.models.question.QuestionType` (Milestone 1, DB schema) validates independently
at the API layer.
"""

_OBJECTIVE_QUESTION_TYPES = {"mcq", "true_false", "fill_blank", "matching", "assertion_reason"}
"""Question types answered via `QuestionItem.correct_answer` (single verifiable answer)."""

ASSERTION_REASON_OPTIONS: tuple[str, str, str, str] = (
    "Both Assertion and Reason are true, and Reason is the correct explanation of Assertion.",
    "Both Assertion and Reason are true, but Reason is NOT the correct explanation of Assertion.",
    "Assertion is true, but Reason is false.",
    "Assertion is false, but Reason is true.",
)
"""The 4 canonical `assertion_reason` answer-option strings -- copied verbatim from
`frontend/src/components/quiz/questions/AssertionReasonQuestion.tsx`'s `DEFAULT_OPTIONS`
(the frontend's rendered fallback whenever a question's `type_data.options` is absent),
which makes this tuple the AI-side source of truth for that string set.

Grading is exact-string match (`_grade_objective` in
`backend/app/services/quiz_attempt_service.py`) and the frontend only ever submits back one
of these option strings as the student's answer, so a generated `assertion_reason` item
whose `options`/`correct_answer` drift from this tuple would silently become
ungradeable-correct if ever persisted. `ai/prompts/quiz_generation_v1.py` repeats these same
4 strings as literal prompt text (its `SYSTEM_PROMPT` is a static string, not templated, so
it can't reference this constant directly -- keep them in sync by hand);
`ai/orchestrator/orchestrator.py:_run_quiz_generation` enforces it for real, rejecting any
generated item that doesn't match before returning (`.claude/rules/ai.md`'s "validate
generated output against the expected schema" + ADR 0011's hard-failure-over-garbled-grade
precedent, extended from grading to generation)."""

_FREE_TEXT_QUESTION_TYPES = {"short_answer", "long_answer", "case_study"}
"""Question types answered via `QuestionItem.reference_answer` (open-ended, graded against
a model answer rather than exact-matched -- Milestone 6, `QUIZ_GRADING`)."""


class MatchingPair(BaseModel):
    """One correct left/right correspondence for a `matching` question.

    A `matching` `QuestionItem.pairs` list holds every correct pair in order; a UI is
    expected to shuffle the `right` side before presenting it to the student.
    """

    left: str
    right: str


class QuestionItem(BaseModel):
    """One generated quiz question — the structured-output contract Gemini must satisfy.

    A single flat shape covers all 8 `QUESTION_TYPES`, discriminated by `question_type`;
    only the fields relevant to that type are populated, the rest stay `None` (same
    flat-optional-fields approach as `ai/gemini/client.py`'s structured-note item schema).

    - `mcq`: `options` (answer choices) + `correct_answer` (must equal one option's text).
    - `true_false`: `correct_answer` is `"true"` or `"false"`.
    - `fill_blank`: `prompt` contains blank markers (e.g. `"_____"`); `blanks` holds the
      correct answer for each blank in order; `correct_answer` mirrors that as one
      " | "-joined string for display/logging convenience.
    - `matching`: `pairs` holds every correct left/right correspondence; `correct_answer`
      mirrors it as one "left=right, ..." joined string for the same convenience reason.
    - `short_answer` / `long_answer`: `reference_answer` is the expected/model answer,
      graded against a rubric rather than exact-matched (Milestone 6).
    - `case_study`: `scenario` is the case description the student reads first; `prompt`
      is the question posed about it; `reference_answer` is the expected/model answer.
    - `assertion_reason`: `assertion` and `reason` are the two statements presented to the
      student; `options` is the 4 canonical assertion-reason relationship strings (reused
      from `mcq`, not a dedicated field, so grading logic doesn't need a type-specific
      branch) and `correct_answer` must exactly equal one of them --
      `frontend/src/components/quiz/questions/AssertionReasonQuestion.tsx`'s
      `DEFAULT_OPTIONS` is the canonical source for the exact 4 strings; a mismatch here
      silently breaks exact-string grading (`_grade_objective`).

    `topic` is the specific sub-topic this question tests (e.g. "photosynthesis", "Newton's
    second law"), same spirit as `QuestionGradeResult.topic_tag` on the grading side --
    always populated, regardless of `question_type`. Unlike the type-specific fields above,
    it's a required `str`, not `str | None`, on purpose: Gemini's structured-output mode
    reliably fills fields listed in the JSON schema's `required` array, but treats
    nullable/optional fields as skippable even when the prompt says "always set it" --
    a prose instruction on a nullable field was tried first and produced `topic: null` on
    every question (0/8 in a live check), so the field itself now carries the constraint.
    """

    question_type: str
    prompt: str
    topic: str
    scenario: str | None = None
    assertion: str | None = None
    reason: str | None = None
    options: list[str] | None = None
    pairs: list[MatchingPair] | None = None
    blanks: list[str] | None = None
    correct_answer: str | None = None
    reference_answer: str | None = None
    difficulty: str = "medium"
    explanation: str | None = None
    citation: Citation | None = None


class QuizGenerationRequest(BaseModel):
    """Input for `TaskType.QUIZ_GENERATION` — grounded NotebookLM content to turn into a
    quiz question set.

    `question_types` is a subset of `QUESTION_TYPES` (plain `list[str]`, same
    backend-enum-decoupling reason as `material_type` elsewhere in this module).
    `difficulty` is `"easy"`/`"medium"`/`"hard"`/`"mixed"` — `"mixed"` lets Gemini
    distribute difficulty across the generated set itself, tagging each `QuestionItem`
    individually.
    """

    topic: str = ""
    context: str = ""
    citations: list[Citation] = Field(default_factory=list)
    question_types: list[str] = Field(default_factory=lambda: ["mcq"])
    count: int = 10
    difficulty: str = "mixed"


class GradingItem(BaseModel):
    """One free-text question to grade, part of a batched `QuizGradingRequest`.

    `question_type` is one of `_FREE_TEXT_QUESTION_TYPES` ("short_answer"/"long_answer"/
    "case_study") -- kept as a plain `str`, same backend-enum-decoupling reason as
    `QuestionItem.question_type`. `question_id` is opaque to this module (the caller's
    `app.models.quiz.Question.id`), threaded through unchanged so the grading result can be
    matched back to the right question -- `ai/` never imports backend models.
    """

    question_id: str
    question_type: str
    prompt: str
    reference_answer: str
    student_answer: str


class QuizGradingRequest(BaseModel):
    """Input for `TaskType.QUIZ_GRADING` -- every free-text question in one quiz attempt,
    graded in a single batched Gemini call (`.claude/rules/performance.md`'s no-AI-call-
    in-a-loop rule, ADR 0011). Callers assemble `items` from all of an attempt's
    short_answer/long_answer/case_study questions plus the student's submitted answers;
    objective-type questions never appear here (Milestone 7 grades those deterministically,
    no AI call).
    """

    items: list[GradingItem]


class QuestionGradeResult(BaseModel):
    """One graded free-text question -- the structured-output contract Gemini must satisfy.

    `score` is a 0.0-1.0 fractional value (partial credit for long-form answers) -- the same
    scale convention Milestone 7's deterministic grading is expected to use for objective
    types (1.0 = fully correct, 0.0 = fully incorrect, no partial credit there), so a
    caller can average both uniformly into an attempt-level score. `is_correct` is set
    directly by the grading call rather than derived client-side from a hardcoded
    threshold; the prompt instructs it to align with `score >= 0.5` ("more right than
    wrong") but is a holistic judgment call for borderline partial-credit answers, not a
    strict cutoff -- documented here so Milestone 7 doesn't need to re-derive it. `feedback`
    is constructive, specific text shown to the student. `topic_tag` is the specific
    sub-topic this question tests (e.g. "photosynthesis", "Newton's second law"), used to
    aggregate `weak_topics.missed_count` for low-scoring questions (ADR 0011) -- always
    populated, even for a fully-correct answer, so aggregation logic doesn't need a
    separate "was this missed" branch.
    """

    question_id: str
    score: float = Field(ge=0.0, le=1.0)
    is_correct: bool
    feedback: str
    topic_tag: str


class TopicImageResult(BaseModel):
    """One retrieved topic-relevant image — the structured-output contract
    `TaskType.TOPIC_IMAGE_SEARCH` returns (ADR 0010, `ai/image_search/client.py`).

    All four fields are required, not optional (ADR 0010 line 18): `attribution`/`license`
    aren't cosmetic extras here — both Wikimedia Commons and Openverse content carries
    CC-family licenses that require attribution display wherever the image is shown, so a
    result missing either isn't a usable result (`ai/image_search/client.py` skips any
    provider hit it can't populate both fields for, treating it the same as "no match"
    rather than fabricating a placeholder).
    """

    image_url: str
    attribution: str
    license: str
    source_url: str


class TopicImageSearchRequest(BaseModel):
    """Input for `TaskType.TOPIC_IMAGE_SEARCH` — a topic/question string, not full answer
    text (ADR 0010) — e.g. "the simplex method", not a paragraph explaining it.
    """

    query: str


class StudioArtifactCreateRequest(BaseModel):
    """Input for `TaskType.STUDIO_ARTIFACT_CREATE`.

    `artifact_type` is a `app.models.generated_material.MaterialArtifactType` value, kept
    as a plain `str` here for the same reason as `NotesGenerationRequest.material_type`
    (`ai/` doesn't import backend model enums). `options` is passed through to
    `ai.notebooklm.client.NotebookLMClient.create_studio_artifact` verbatim.
    """

    artifact_type: str
    notebooklm_notebook_id: str
    options: dict[str, str | int] = Field(default_factory=dict)


class InternetSearchRequest(BaseModel):
    """Input for `TaskType.INTERNET_SEARCH` — a student question needing current/external
    information not covered by a notebook's indexed sources (ADR 0012, Routing Logic step
    4, `docs/AI.md#routing-logic`).

    No `citations` field, unlike most other request types here: citations are derived from
    the search results themselves (`ai/orchestrator/orchestrator.py:_run_internet_search`
    builds them from `InternetSearchItem.url`), not supplied by the caller.
    """

    query: str
    max_results: int = 5
