import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.quiz_attempt import QuizAttemptStatus
from app.schemas.quiz import QuestionRead, QuestionReviewRead


class QuizAttemptStart(BaseModel):
    """Request body for `POST .../attempts` — deliberately empty.

    Starting an attempt needs nothing beyond the `quiz_id` path param (question order is
    randomized server-side, `time_limit_seconds` is snapshotted from the quiz). Kept as a
    named schema anyway, matching every other resource's `*Create` schema, so a future
    per-attempt option (e.g. an explicit shuffle toggle) has a place to land without an
    endpoint signature change. Not wired into the route as a required `Body(...)` — the
    endpoint takes no request body at all (see `app/api/v1/quiz_attempts.py`).
    """

    model_config = ConfigDict(extra="forbid")


class QuizAttemptAnswerPatch(BaseModel):
    """Autosave body for `PATCH .../attempts/{attempt_id}` — one question per call.

    Single-question shape chosen over a batched `{answers: {question_id: answer}}` body:
    the frontend autosave flow is a debounced per-field save (save the question just
    blurred/settled), so a single-question PATCH maps directly to that trigger without the
    client needing to track and re-send the whole in-progress answer set on every debounce
    tick.

    `answer` shape depends on `question_type` (mirrors `QuizAttemptAnswer.student_answer`,
    validated loosely here and checked deterministically at grading time):
    - `mcq` / `true_false` / `assertion_reason`: `str` (selected option/choice text).
    - `fill_blank`: `list[str]`, one entry per blank in prompt order (falls back to a bare
      `str` if the question has no discrete blanks).
    - `matching`: `list[{"left": str, "right": str}]`, the student's proposed pairing.
    - `short_answer` / `long_answer` / `case_study`: `str` free text.
    """

    question_id: uuid.UUID
    answer: dict | list | str


class QuizAttemptRead(BaseModel):
    """In-progress/submitted/grading attempt shape — answer-key-free.

    Built from `QuestionRead` (no `correct_answer`/`reference_answer`/`explanation`/
    `citation` fields exist on that schema at all), never from `QuestionReviewRead`. See
    `app.services.quiz_attempt_service.get_attempt` for the full boundary rationale.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    status: QuizAttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    time_limit_seconds: int | None
    question_order: list[uuid.UUID]
    answers: dict
    questions: list[QuestionRead]
    created_at: datetime
    updated_at: datetime


class QuizAttemptSummary(BaseModel):
    """Lightweight per-attempt shape for the list endpoint — metadata only, no nested
    questions (avoids re-fetching/serializing every question for every attempt in a list).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    status: QuizAttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    graded_at: datetime | None
    score: Decimal | None
    max_score: Decimal | None


class QuizAttemptAnswerReview(BaseModel):
    """The student's finalized per-question result, paired with the question's answer key
    in `QuizAttemptReviewRead.questions` — post-grading only.
    """

    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID
    student_answer: dict | list | str
    is_correct: bool | None
    score: Decimal
    ai_feedback: str | None
    topic_tag: str | None


class QuestionWithReview(BaseModel):
    """One question's answer key paired with the student's result for it."""

    question: QuestionReviewRead
    answer: QuizAttemptAnswerReview


class QuizAttemptReviewRead(BaseModel):
    """Post-grading attempt shape — includes the answer key (`QuestionReviewRead`) and
    per-question feedback. Only ever returned once `status == GRADED` — see
    `app.services.quiz_attempt_service.get_attempt`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    status: QuizAttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    graded_at: datetime | None
    time_limit_seconds: int | None
    score: Decimal | None
    max_score: Decimal | None
    questions: list[QuestionWithReview]
    created_at: datetime
    updated_at: datetime
