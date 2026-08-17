"""add chunk full-text search vector

Revision ID: c7d41e8a2f90
Revises: f3a9c2e7b514
Create Date: 2026-08-13 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c7d41e8a2f90"
down_revision: str | None = "f3a9c2e7b514"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chunks_search_vector_gin",
        "chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_search_vector_gin", table_name="chunks", postgresql_using="gin")
    op.drop_column("chunks", "search_vector")
