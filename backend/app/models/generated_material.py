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


class MaterialArtifactType(enum.StrEnum):
    """NotebookLM Studio artifact types (docs/AI_WORKFLOWS.md, ADR 0004).

    `nlm`'s own `--json` output uses inconsistent per-type naming (e.g.
    `mind_map`, `slide_deck`, `data_table` vs plain `report`/`infographic`) --
    these members are Lumora's own stable vocabulary; `ai/notebooklm/client.py`
    maps them to the CLI's actual subcommand/type names.
    """

    AUDIO = "audio"
    REPORT = "report"
    SLIDES = "slides"
    INFOGRAPHIC = "infographic"
    MINDMAP = "mindmap"
    DATA_TABLE = "data_table"


class MaterialStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class GeneratedMaterial(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A NotebookLM Studio artifact (audio/report/slides/infographic/mindmap/data table).

    The `generated_materials` catch-all table reserved in docs/DATABASE.md for study
    materials without a dedicated table -- unlike `notes`/`flashcard_sets`, which are
    Gemini-authored and get their own tables, these six types are 100% NotebookLM-authored
    (no Gemini synthesis step) and share one lifecycle closely enough to not warrant six
    near-identical tables.

    Text-shaped results (`report`'s markdown, `mindmap`'s JSON) are stored directly in
    `content`. Binary results (`audio` mp3, `infographic` png, `slides` pdf, `data_table`
    csv) are downloaded from NotebookLM and re-uploaded into this app's own `FileStorage`
    (`app/core/storage.py`) -- never left pointing at a NotebookLM-hosted URL -- with the
    resulting path in `storage_path`.
    """

    __tablename__ = "generated_materials"

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
    artifact_type: Mapped[MaterialArtifactType] = mapped_column(
        SAEnum(
            MaterialArtifactType,
            name="material_artifact_type",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[MaterialStatus] = mapped_column(
        SAEnum(
            MaterialStatus,
            name="material_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=MaterialStatus.PENDING,
        server_default=MaterialStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Type-specific generation options (format/length/orientation/detail/description/...),
    # validated at the API layer (app/schemas/generated_material.py) -- kept generic here
    # so this table doesn't need a migration every time NotebookLM adds a new option.
    options: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    notebooklm_artifact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped["Notebook"] = relationship(back_populates="generated_materials")
