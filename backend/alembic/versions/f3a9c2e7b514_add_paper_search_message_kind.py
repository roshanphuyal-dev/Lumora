"""add paper_search message kind

Revision ID: f3a9c2e7b514
Revises: b4e8c1a2d903
Create Date: 2026-08-13 12:30:00.000000

Adds a third `message_kind` enum value, `paper_search`, so paper-search
assistant messages persist to conversation history the same way
`web_search` messages already do (via the existing `content`/`citations`
columns -- no new structured column needed, unlike `image_result` which
is specific to image search).

Rollback note: Postgres has no `ALTER TYPE ... DROP VALUE`. Downgrade
rebuilds the enum without `paper_search` by renaming the old type,
creating a new one with just `notebook`/`web_search`, and altering the
column to the new type. Any row already persisted with
`kind = 'paper_search'` is remapped to `web_search` during that rebuild
-- this is a lossy downgrade (the row's `kind` no longer distinguishes
paper search from web search) though `content`/`citations`/`provider`
on the row are left untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3a9c2e7b514"
down_revision: str | None = "b4e8c1a2d903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE is transactional as of Postgres 12+, so this is
    # safe to run inside Alembic's default transactional-DDL wrapper -- the new
    # value just can't be *used* in the same transaction it's added in, and this
    # migration doesn't use it.
    op.execute("ALTER TYPE message_kind ADD VALUE IF NOT EXISTS 'paper_search'")


def downgrade() -> None:
    # No direct "remove enum value" in Postgres -- rebuild the type instead.
    op.execute("UPDATE messages SET kind = 'web_search' WHERE kind = 'paper_search'")
    op.execute("ALTER TYPE message_kind RENAME TO message_kind_old")
    message_kind_new = sa.Enum("notebook", "web_search", name="message_kind")
    message_kind_new.create(op.get_bind(), checkfirst=False)
    # The column default is typed against the old enum -- it must be dropped
    # before the type swap and re-added after, or Postgres refuses the ALTER
    # with "default for column ... cannot be cast automatically".
    op.execute("ALTER TABLE messages ALTER COLUMN kind DROP DEFAULT")
    op.execute(
        "ALTER TABLE messages ALTER COLUMN kind TYPE message_kind USING kind::text::message_kind"
    )
    op.execute("ALTER TABLE messages ALTER COLUMN kind SET DEFAULT 'notebook'")
    op.execute("DROP TYPE message_kind_old")
