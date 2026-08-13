import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import Notebook
    from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer


class QuizStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class QuizDifficulty(enum.StrEnum):
    """Shared by `Quiz.difficulty` (requested target) and `Question.difficulty`
    (actual per-question difficulty, which may vary within a MIXED quiz)."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QuestionType(enum.StrEnum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"
    ASSERTION_REASON = "assertion_reason"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    CASE_STUDY = "case_study"


class Quiz(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A generated quiz, with async generation status (same shape as `Note`/`FlashcardSet`).

    Engine/attempt tracking lives in `QuizAttempt`/`QuizAttemptAnswer` (see
    `app.models.quiz_attempt`) -- this table only covers the generated quiz definition.
    """

    __tablename__ = "quizzes"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[QuizStatus] = mapped_column(
        SAEnum(
            QuizStatus,
            name="quiz_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=QuizStatus.PENDING,
        server_default=QuizStatus.PENDING.value,
    )
    # Requested question type strings (subset of QuestionType values), validated at the
    # API/Pydantic layer -- kept generic here so mix-of-types requests don't need a schema
    # change.
    question_types: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[QuizDifficulty] = mapped_column(
        SAEnum(
            QuizDifficulty,
            name="quiz_difficulty",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Opt-in set at quiz-creation time; read by the generation worker
    # (app.workers.quiz_tasks) to decide whether to ground question generation with
    # TaskType.INTERNET_SEARCH results. Persisted (not request-time-only) because
    # generation is deferred to Celery, which only receives quiz_id and re-reads
    # params off this row.
    include_web_search: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped["Notebook"] = relationship(back_populates="quizzes")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="Question.position",
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single question within a `Quiz`, ordered by `position`."""

    __tablename__ = "questions"
    __table_args__ = (
        # Composite index for the hot-path access pattern: fetch a quiz's questions
        # ordered by position (WHERE quiz_id = ... ORDER BY position).
        Index("ix_questions_quiz_id_position", "quiz_id", "position"),
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(
            QuestionType,
            name="question_type",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Shape varies per question_type (options/pairs/blanks/...), validated at the
    # API/Pydantic layer, not the DB layer -- same pattern as
    # GeneratedMaterial.options/Note.content_json.
    type_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Objective types only (mcq/true_false/fill_blank/matching/assertion_reason).
    correct_answer: Mapped[dict | list | str | None] = mapped_column(JSONB, nullable=True)
    # Free-text types only (short_answer/long_answer/case_study).
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # Weak-topic-tagging: populated at generation time (QUIZ_GENERATION prompt) for
    # all question types. Nullable because existing rows predate this column and
    # backfill is not guaranteed; grading (quiz_attempt_service) falls back to None
    # for objective types when absent. See docs/adr/0011, decision #3.
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[QuizDifficulty] = mapped_column(
        SAEnum(
            QuizDifficulty,
            name="quiz_difficulty",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Source chunk reference (source_id/chunk_id/excerpt), per .claude/rules/ai.md
    # citation-preservation rule -- same shape as Flashcard.citation.
    citation: Mapped[dict[str, str | None] | None] = mapped_column(JSONB, nullable=True)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    attempt_answers: Mapped[list["QuizAttemptAnswer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
