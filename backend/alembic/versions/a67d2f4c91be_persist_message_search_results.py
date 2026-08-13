"""persist message search results

Revision ID: a67d2f4c91be
Revises: efa782cf4ee7
Create Date: 2026-08-11 19:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a67d2f4c91be"
down_revision: str | None = "efa782cf4ee7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


message_kind = postgresql.ENUM("notebook", "web_search", name="message_kind", create_type=False)


def upgrade() -> None:
    message_kind.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "messages",
        sa.Column(
            "kind",
            message_kind,
            server_default="notebook",
            nullable=False,
        ),
    )
    op.add_column(
        "messages",
        sa.Column("image_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "image_result")
    op.drop_column("messages", "kind")
    message_kind.drop(op.get_bind(), checkfirst=True)
