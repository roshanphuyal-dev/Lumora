"""add quiz adaptation metadata

Revision ID: a5c9d2e7f104
Revises: f6c3d9e8a102
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a5c9d2e7f104"
down_revision: str | None = "f6c3d9e8a102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quizzes",
        sa.Column("adaptation_applied", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "quizzes",
        sa.Column(
            "adaptive_difficulty_mix",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("quizzes", "adaptive_difficulty_mix")
    op.drop_column("quizzes", "adaptation_applied")
