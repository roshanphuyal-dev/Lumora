import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import Notebook


class FlashcardSetStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class FlashcardSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flashcard_sets"

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
    status: Mapped[FlashcardSetStatus] = mapped_column(
        SAEnum(
            FlashcardSetStatus,
            name="flashcard_set_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=FlashcardSetStatus.PENDING,
        server_default=FlashcardSetStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped["Notebook"] = relationship(back_populates="flashcard_sets")
    flashcards: Mapped[list["Flashcard"]] = relationship(
        back_populates="flashcard_set",
        cascade="all, delete-orphan",
        order_by="Flashcard.position",
    )


class Flashcard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flashcards"

    flashcard_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flashcard_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[dict[str, str | None] | None] = mapped_column(JSONB, nullable=True)

    flashcard_set: Mapped[FlashcardSet] = relationship(back_populates="flashcards")
