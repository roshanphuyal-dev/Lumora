"""add study activity telemetry

Revision ID: b7e2f4a6c801
Revises: a5c9d2e7f104
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2f4a6c801"
down_revision: str | None = "a5c9d2e7f104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "study_activities",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notebook_id", sa.UUID(), nullable=False),
        sa.Column("activity_key", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_seconds >= 0 AND duration_seconds <= 14400",
            name="ck_study_activities_duration_bounded",
        ),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_key", name="uq_study_activities_user_key"),
    )
    op.create_index("ix_study_activities_user_id", "study_activities", ["user_id"])
    op.create_index("ix_study_activities_notebook_id", "study_activities", ["notebook_id"])
    op.create_index(
        "ix_study_activities_owner_notebook_occurred",
        "study_activities",
        ["user_id", "notebook_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_study_activities_owner_notebook_occurred", table_name="study_activities")
    op.drop_index("ix_study_activities_notebook_id", table_name="study_activities")
    op.drop_index("ix_study_activities_user_id", table_name="study_activities")
    op.drop_table("study_activities")
