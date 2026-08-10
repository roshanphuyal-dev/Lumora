"""add cheat sheet formula sheet mnemonics timeline comparison chart note types

Revision ID: 5d81c8fe607b
Revises: ec638c027c98
Create Date: 2026-08-10 21:01:59.434736

Rollback note: Postgres has no `ALTER TYPE ... DROP VALUE` -- there is no built-in way to
remove a native enum value once added. `downgrade()` drops `content_json` but the five
`note_material_type` values added here stay in the type permanently; this is a Postgres
limitation, not an oversight (.claude/rules/database.md's destructive-migration rollback
note requirement, applied honestly rather than faked).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d81c8fe607b"
down_revision: str | None = "ec638c027c98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_MATERIAL_TYPES = ("cheat_sheet", "formula_sheet", "mnemonics", "timeline", "comparison_chart")


def upgrade() -> None:
    for value in _NEW_MATERIAL_TYPES:
        op.execute(f"ALTER TYPE note_material_type ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column(
        "notes", sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notes", "content_json")
    # Enum values intentionally not removed -- see module docstring.
