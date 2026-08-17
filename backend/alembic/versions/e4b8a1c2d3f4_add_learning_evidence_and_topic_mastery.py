"""add learning evidence and topic mastery

Revision ID: e4b8a1c2d3f4
Revises: c7d41e8a2f90
Create Date: 2026-08-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4b8a1c2d3f4"
down_revision: str | None = "c7d41e8a2f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_evidence",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notebook_id", sa.UUID(), nullable=False),
        sa.Column("attempt_answer_id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["attempt_answer_id"], ["quiz_attempt_answers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_answer_id", name="uq_learning_evidence_attempt_answer"),
    )
    op.create_index("ix_learning_evidence_user_id", "learning_evidence", ["user_id"])
    op.create_index("ix_learning_evidence_notebook_id", "learning_evidence", ["notebook_id"])
    op.create_index(
        "ix_learning_evidence_owner_notebook_topic_observed",
        "learning_evidence",
        ["user_id", "notebook_id", "topic", "observed_at"],
    )
    op.create_table(
        "topic_masteries",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notebook_id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("mastery_percent", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("evidence_weight", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "notebook_id", "topic", name="uq_topic_masteries_owner_notebook_topic"
        ),
    )
    op.create_index("ix_topic_masteries_user_id", "topic_masteries", ["user_id"])
    op.create_index("ix_topic_masteries_notebook_id", "topic_masteries", ["notebook_id"])
    op.create_index(
        "ix_topic_masteries_owner_notebook_mastery",
        "topic_masteries",
        ["user_id", "notebook_id", "mastery_percent"],
    )


def downgrade() -> None:
    op.drop_index("ix_topic_masteries_owner_notebook_mastery", table_name="topic_masteries")
    op.drop_index("ix_topic_masteries_notebook_id", table_name="topic_masteries")
    op.drop_index("ix_topic_masteries_user_id", table_name="topic_masteries")
    op.drop_table("topic_masteries")
    op.drop_index(
        "ix_learning_evidence_owner_notebook_topic_observed", table_name="learning_evidence"
    )
    op.drop_index("ix_learning_evidence_notebook_id", table_name="learning_evidence")
    op.drop_index("ix_learning_evidence_user_id", table_name="learning_evidence")
    op.drop_table("learning_evidence")
