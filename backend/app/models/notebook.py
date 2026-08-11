import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat import Conversation
    from app.models.document import Document
    from app.models.flashcard import FlashcardSet
    from app.models.generated_material import GeneratedMaterial
    from app.models.note import Note
    from app.models.quiz import Quiz
    from app.models.weak_topic import WeakTopic


class NotebookSourceIndexStatus(enum.StrEnum):
    """NotebookLM indexing lifecycle for a source once attached to a notebook."""

    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class Notebook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A knowledge-base container grouping related document sources for RAG/NotebookLM."""

    __tablename__ = "notebooks"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Nullable: a notebook may be general-purpose and not scoped to one subject.
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nullable: populated lazily when the first source is attached and a remote
    # NotebookLM notebook is created on demand. Not indexed — only looked up by
    # notebook.id, never queried on directly.
    notebooklm_notebook_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sources: Mapped[list["NotebookSource"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    flashcard_sets: Mapped[list["FlashcardSet"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    generated_materials: Mapped[list["GeneratedMaterial"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )
    weak_topics: Mapped[list["WeakTopic"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )


class NotebookSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Join table: which documents belong to which notebook, and their NotebookLM index state."""

    __tablename__ = "notebook_sources"
    __table_args__ = (
        UniqueConstraint(
            "notebook_id", "document_id", name="uq_notebook_sources_notebook_document"
        ),
    )

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    indexing_status: Mapped[NotebookSourceIndexStatus] = mapped_column(
        SAEnum(
            NotebookSourceIndexStatus,
            name="notebook_source_index_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=NotebookSourceIndexStatus.PENDING,
        server_default=NotebookSourceIndexStatus.PENDING.value,
    )

    notebook: Mapped["Notebook"] = relationship(back_populates="sources")
    document: Mapped["Document"] = relationship(back_populates="notebook_sources")
