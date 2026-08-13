import enum
import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class SectionLocatorKind(enum.StrEnum):
    """Human-facing locator represented by a parser-preserved section ordinal."""

    PAGE = "page"
    SLIDE = "slide"
    GENERIC = "generic"


class DocumentSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A parser-preserved natural document unit such as a PDF page or PPTX slide."""

    __tablename__ = "document_sections"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_sections_document_ordinal"),
        CheckConstraint("ordinal > 0", name="ck_document_sections_ordinal_positive"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    locator_kind: Mapped[SectionLocatorKind] = mapped_column(
        SAEnum(
            SectionLocatorKind,
            name="section_locator_kind",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SectionLocatorKind.GENERIC,
        server_default=SectionLocatorKind.GENERIC.value,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="sections")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="section")


class Chunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A retrieval-sized unit of document text with an optional natural-section locator."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_chunks_document_ordinal"),
        Index("ix_chunks_document_content_hash", "document_id", "content_hash"),
        CheckConstraint("ordinal > 0", name="ck_chunks_ordinal_positive"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    section: Mapped[DocumentSection | None] = relationship(back_populates="chunks")
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )


class Embedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned 768-dimensional retrieval embedding for one chunk."""

    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id", "model", "dimensions", name="uq_embeddings_chunk_model_dimensions"
        ),
        CheckConstraint("dimensions = 768", name="ck_embeddings_dimensions_768"),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vector: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=768, server_default="768"
    )

    chunk: Mapped[Chunk] = relationship(back_populates="embeddings")
