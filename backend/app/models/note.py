import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notebook import Notebook


class NoteMaterialType(enum.StrEnum):
    NOTE = "note"
    STUDY_GUIDE = "study_guide"
    # Markdown, same as NOTE/STUDY_GUIDE -- content only, no content_json.
    CHEAT_SHEET = "cheat_sheet"
    FORMULA_SHEET = "formula_sheet"
    # Structured JSON via Gemini's response_schema mode -- content_json only, content
    # stays null. MNEMONICS/TIMELINE share a list[{label,value,detail,citation}] shape;
    # COMPARISON_CHART is a {subjects,attributes,rows} table (see
    # ai/gemini/client.py's local schemas -- ai/ doesn't import backend model enums).
    MNEMONICS = "mnemonics"
    TIMELINE = "timeline"
    COMPARISON_CHART = "comparison_chart"


class NoteStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class Note(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notes"

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
    material_type: Mapped[NoteMaterialType] = mapped_column(
        SAEnum(
            NoteMaterialType,
            name="note_material_type",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[NoteStatus] = mapped_column(
        SAEnum(
            NoteStatus,
            name="note_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=NoteStatus.PENDING,
        server_default=NoteStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Populated instead of `content` for MNEMONICS/TIMELINE (a JSON list) and
    # COMPARISON_CHART (a single JSON object) -- null for every markdown material_type.
    content_json: Mapped[list[dict] | dict | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped["Notebook"] = relationship(back_populates="notes")
