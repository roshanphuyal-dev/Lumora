"""add RAG foundation tables

Revision ID: b4e8c1a2d903
Revises: a7146e33121d
Create Date: 2026-08-13 12:00:00.000000

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b4e8c1a2d903"
down_revision: str | None = "a7146e33121d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    document_rag_status = postgresql.ENUM(
        "pending", "indexing", "indexed", "failed", name="document_rag_status", create_type=False
    )
    document_rag_status.create(op.get_bind(), checkfirst=True)
    section_locator_kind = postgresql.ENUM(
        "page", "slide", "generic", name="section_locator_kind", create_type=False
    )
    section_locator_kind.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "documents",
        sa.Column(
            "rag_status",
            document_rag_status,
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "notebook_sources", sa.Column("notebooklm_source_id", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_notebook_sources_notebooklm_source_id",
        "notebook_sources",
        ["notebooklm_source_id"],
        unique=False,
    )

    op.create_table(
        "document_sections",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "locator_kind",
            section_locator_kind,
            server_default="generic",
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint("ordinal > 0", name="ck_document_sections_ordinal_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "ordinal", name="uq_document_sections_document_ordinal"),
    )
    op.create_index(
        "ix_document_sections_document_id", "document_sections", ["document_id"], unique=False
    )

    op.create_table(
        "chunks",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint("ordinal > 0", name="ck_chunks_ordinal_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["document_sections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "ordinal", name="uq_chunks_document_ordinal"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"], unique=False)
    op.create_index(
        "ix_chunks_document_content_hash",
        "chunks",
        ["document_id", "content_hash"],
        unique=False,
    )
    op.create_index("ix_chunks_section_id", "chunks", ["section_id"], unique=False)

    op.create_table(
        "embeddings",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vector", pgvector.sqlalchemy.Vector(dim=768), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), server_default="768", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.CheckConstraint("dimensions = 768", name="ck_embeddings_dimensions_768"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chunk_id", "model", "dimensions", name="uq_embeddings_chunk_model_dimensions"
        ),
    )
    op.create_index("ix_embeddings_chunk_id", "embeddings", ["chunk_id"], unique=False)
    op.create_index(
        "ix_embeddings_vector_hnsw_cosine",
        "embeddings",
        ["vector"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"vector": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
    )


def downgrade() -> None:
    # Additive Phase 4 foundation: downgrade removes only local RAG-derived data and
    # lifecycle metadata. Raw documents and NotebookLM source associations remain intact.
    op.drop_index("ix_embeddings_vector_hnsw_cosine", table_name="embeddings")
    op.drop_index("ix_embeddings_chunk_id", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index("ix_chunks_section_id", table_name="chunks")
    op.drop_index("ix_chunks_document_content_hash", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_document_sections_document_id", table_name="document_sections")
    op.drop_table("document_sections")
    postgresql.ENUM(name="section_locator_kind").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_notebook_sources_notebooklm_source_id", table_name="notebook_sources")
    op.drop_column("notebook_sources", "notebooklm_source_id")
    op.drop_column("documents", "rag_status")
    postgresql.ENUM(name="document_rag_status").drop(op.get_bind(), checkfirst=True)
    # Keep the shared vector extension installed; other schemas may depend on it.
