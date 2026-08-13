import uuid
from datetime import datetime

from ai.orchestrator.schemas import QUESTION_TYPES, Citation
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.quiz import QuestionType, QuizDifficulty, QuizStatus


class QuizCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    topic: str = Field(default="", max_length=2000)
    question_types: list[str] = Field(default_factory=lambda: ["mcq"])
    question_count: int = Field(default=10, ge=1, le=50)
    difficulty: QuizDifficulty = QuizDifficulty.MIXED
    time_limit_seconds: int | None = Field(default=None, ge=1)
    include_web_search: bool = False

    @field_validator("question_types")
    @classmethod
    def _validate_question_types(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("question_types must not be empty")
        invalid = sorted(set(value) - set(QUESTION_TYPES))
        if invalid:
            raise ValueError(f"Unsupported question_types: {invalid}")
        return value


class QuestionRead(BaseModel):
    """Question shape for the pre-attempt/preview endpoint — never includes answer-key
    fields (`correct_answer`/`reference_answer`/`explanation`/`citation`) per the
    security boundary agreed for the "while taking a quiz" flow (Milestone 7).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    position: int
    question_type: QuestionType
    prompt: str
    type_data: dict
    difficulty: QuizDifficulty
    created_at: datetime
    updated_at: datetime


class QuestionReviewRead(BaseModel):
    """Full question shape including the answer key — used post-grading (Milestone 7+),
    not exposed while a quiz is being taken.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    position: int
    question_type: QuestionType
    prompt: str
    type_data: dict
    correct_answer: dict | list | str | None
    reference_answer: str | None
    explanation: str
    citation: Citation | None
    difficulty: QuizDifficulty
    created_at: datetime
    updated_at: datetime


class QuizRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    status: QuizStatus
    title: str
    topic: str | None
    question_types: list[str]
    question_count: int
    difficulty: QuizDifficulty
    time_limit_seconds: int | None
    include_web_search: bool
    error_message: str | None
    questions: list[QuestionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
