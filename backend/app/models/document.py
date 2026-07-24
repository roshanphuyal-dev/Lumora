import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import NotebookSource


class DocumentParseStatus(enum.StrEnum):
    """Lifecycle of extracting text from an uploaded file (see docs/AI_WORKFLOWS.md)."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An uploaded file (PDF/DOCX/PPTX/image/URL) plus its extracted text.

    Raw bytes are never stored here — `storage_path` points at Supabase Storage.
    """

    __tablename__ = "documents"

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
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
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

    notebook_sources: Mapped[list["NotebookSource"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
