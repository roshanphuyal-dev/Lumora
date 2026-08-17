import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class LearningPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Student-confirmed, user-scoped tutoring preferences."""

    __tablename__ = "learning_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_learning_preferences_user"),
        CheckConstraint(
            "explanation_depth IS NULL OR explanation_depth IN ('concise', 'balanced', 'detailed')",
            name="ck_learning_preferences_explanation_depth",
        ),
        CheckConstraint(
            "explanation_style IS NULL OR explanation_style IN "
            "('direct', 'step_by_step', 'socratic', 'example_driven')",
            name="ck_learning_preferences_explanation_style",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    explanation_depth: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_style: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship()


class LearningPreferenceSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explainable deterministic suggestion that has no effect until accepted."""

    __tablename__ = "learning_preference_suggestions"
    __table_args__ = (
        CheckConstraint(
            "preference_key IN ('explanation_depth', 'explanation_style')",
            name="ck_learning_preference_suggestions_key",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_learning_preference_suggestions_status",
        ),
        UniqueConstraint(
            "user_id",
            "preference_key",
            "suggested_value",
            "signal_type",
            name="uq_learning_preference_suggestions_signal",
        ),
        Index(
            "ix_learning_preference_suggestions_owner_status_created",
            "user_id",
            "status",
            "created_at",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    preference_key: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_value: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)

    user: Mapped["User"] = relationship()
