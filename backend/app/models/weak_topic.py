import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import Notebook
    from app.models.user import User


class WeakTopic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A detected weak area for a student within a notebook, tallied from
    `QuizAttemptAnswer.topic_tag` misses.

    Deliberately minimal -- broader progress/analytics tracking is a separate later
    roadmap item, not this table's concern.
    """

    __tablename__ = "weak_topics"
    __table_args__ = (
        # Composite index for the hot-path lookup: this user's weak topics in this
        # notebook (WHERE user_id = ... AND notebook_id = ...).
        Index("ix_weak_topics_user_id_notebook_id", "user_id", "notebook_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    missed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="weak_topics")
    notebook: Mapped["Notebook"] = relationship(back_populates="weak_topics")
