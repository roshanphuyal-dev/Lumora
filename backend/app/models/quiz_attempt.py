import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.quiz import Question, Quiz


class QuizAttemptStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADING = "grading"
    GRADED = "graded"
    ABANDONED = "abandoned"


class QuizAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One student's attempt at a `Quiz`, from start through grading.

    Autosave lands in `answers` (scratch, keyed by `question_id`) while the attempt is
    in progress; on submit, finalized per-question results move into `QuizAttemptAnswer`
    rows instead.
    """

    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[QuizAttemptStatus] = mapped_column(
        SAEnum(
            QuizAttemptStatus,
            name="quiz_attempt_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=QuizAttemptStatus.IN_PROGRESS,
        server_default=QuizAttemptStatus.IN_PROGRESS.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Snapshot of quizzes.time_limit_seconds at attempt-start time, so a later edit to
    # the quiz doesn't retroactively change the clock on an attempt already in progress.
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Snapshot of randomized question id order, so question order stays stable for the
    # duration of the attempt regardless of later quiz edits.
    question_order: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Scratch autosave, keyed by question_id -- pre-submit answers only. Finalized
    # per-question results live in QuizAttemptAnswer once graded.
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")
    attempt_answers: Mapped[list["QuizAttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class QuizAttemptAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Finalized per-question result within a `QuizAttempt`, populated once graded."""

    __tablename__ = "quiz_attempt_answers"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_answer: Mapped[dict | list | str] = mapped_column(JSONB, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0, server_default="0")
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For weak-topic detection -- free-text tag, not an FK, since a question may span
    # topics that don't map 1:1 to any single taxonomy entry.
    topic_tag: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempt: Mapped[QuizAttempt] = relationship(back_populates="attempt_answers")
    question: Mapped["Question"] = relationship(back_populates="attempt_answers")
