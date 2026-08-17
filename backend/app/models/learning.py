import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import Notebook
    from app.models.quiz_attempt import QuizAttemptAnswer
    from app.models.user import User


class LearningEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable, structured evidence captured from one graded quiz answer."""

    __tablename__ = "learning_evidence"
    __table_args__ = (
        UniqueConstraint("attempt_answer_id", name="uq_learning_evidence_attempt_answer"),
        Index(
            "ix_learning_evidence_owner_notebook_topic_observed",
            "user_id",
            "notebook_id",
            "topic",
            "observed_at",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    attempt_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quiz_attempt_answers.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()
    notebook: Mapped["Notebook"] = relationship()
    attempt_answer: Mapped["QuizAttemptAnswer"] = relationship()


class TopicMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest persisted deterministic mastery snapshot for one notebook topic."""

    __tablename__ = "topic_masteries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "notebook_id", "topic", name="uq_topic_masteries_owner_notebook_topic"
        ),
        Index(
            "ix_topic_masteries_owner_notebook_mastery",
            "user_id",
            "notebook_id",
            "mastery_percent",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    mastery_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_weight: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    evidence_count: Mapped[int] = mapped_column(nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()
    notebook: Mapped["Notebook"] = relationship()


class StudyActivityType(enum.StrEnum):
    STUDY_SESSION = "study_session"
    MATERIAL_VIEWED = "material_viewed"
    MATERIAL_REVISED = "material_revised"
    QUIZ_COMPLETED = "quiz_completed"


class StudyActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One immutable, idempotent factual learning activity event."""

    __tablename__ = "study_activities"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds >= 0 AND duration_seconds <= 14400",
            name="ck_study_activities_duration_bounded",
        ),
        UniqueConstraint("user_id", "activity_key", name="uq_study_activities_user_key"),
        Index(
            "ix_study_activities_owner_notebook_occurred",
            "user_id",
            "notebook_id",
            "occurred_at",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    activity_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    user: Mapped["User"] = relationship()
    notebook: Mapped["Notebook"] = relationship()
