import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import NotebookSource
    from app.models.rag import Chunk, DocumentSection


class DocumentParseStatus(enum.StrEnum):
    """Lifecycle of extracting text from an uploaded file (see docs/AI_WORKFLOWS.md)."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class DocumentRagStatus(enum.StrEnum):
    """Lifecycle of local chunking and embedding, separate from NotebookLM indexing."""

    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An uploaded file (PDF/DOCX/PPTX/image) or a linked URL, plus its extracted text.

    Raw bytes are never stored here — `storage_path` points at Supabase Storage.
    A Document is either file-backed (`storage_path` set, `source_url` null) or
    link-backed (`source_url` set, `storage_path` null) — never both, enforced by
    `ck_documents_exactly_one_of_storage_path_source_url`.
    """

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(storage_path IS NOT NULL) != (source_url IS NOT NULL)",
            name="ck_documents_exactly_one_of_storage_path_source_url",
        ),
    )

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Nullable: a document can be uploaded before being filed under a subject,
    # and should survive a subject delete rather than being force-deleted with it.
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable: null for link-backed documents (see class docstring).
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Nullable: set only for link-backed documents.
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Optional resource metadata — display title/description distinct from filename.
    # Nullable: falls back to `filename` in the API/UI when unset.
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[DocumentParseStatus] = mapped_column(
        SAEnum(
            DocumentParseStatus,
            name="document_parse_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentParseStatus.PENDING,
        server_default=DocumentParseStatus.PENDING.value,
    )
    # Nullable until parsing completes (or forever, if parsing fails).
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_status: Mapped[DocumentRagStatus] = mapped_column(
        SAEnum(
            DocumentRagStatus,
            name="document_rag_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentRagStatus.PENDING,
        server_default=DocumentRagStatus.PENDING.value,
    )

    notebook_sources: Mapped[list["NotebookSource"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    sections: Mapped[list["DocumentSection"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentSection.ordinal"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.ordinal"
    )
