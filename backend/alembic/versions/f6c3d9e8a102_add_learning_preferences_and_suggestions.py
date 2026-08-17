"""add learning preferences and suggestions

Revision ID: f6c3d9e8a102
Revises: e4b8a1c2d3f4
Create Date: 2026-08-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6c3d9e8a102"
down_revision: str | None = "e4b8a1c2d3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("explanation_depth", sa.Text(), nullable=True),
        sa.Column("explanation_style", sa.Text(), nullable=True),
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
            "explanation_depth IS NULL OR explanation_depth IN ('concise', 'balanced', 'detailed')",
            name="ck_learning_preferences_explanation_depth",
        ),
        sa.CheckConstraint(
            "explanation_style IS NULL OR explanation_style IN "
            "('direct', 'step_by_step', 'socratic', 'example_driven')",
            name="ck_learning_preferences_explanation_style",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_learning_preferences_user"),
    )
    op.create_table(
        "learning_preference_suggestions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("preference_key", sa.Text(), nullable=False),
        sa.Column("suggested_value", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
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
            "preference_key IN ('explanation_depth', 'explanation_style')",
            name="ck_learning_preference_suggestions_key",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_learning_preference_suggestions_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "preference_key",
            "suggested_value",
            "signal_type",
            name="uq_learning_preference_suggestions_signal",
        ),
    )
    op.create_index(
        "ix_learning_preference_suggestions_owner_status_created",
        "learning_preference_suggestions",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learning_preference_suggestions_owner_status_created",
        table_name="learning_preference_suggestions",
    )
    op.drop_table("learning_preference_suggestions")
    op.drop_table("learning_preferences")
