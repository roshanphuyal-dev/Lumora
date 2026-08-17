from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.core.config import Settings
from app.models.document import Document, DocumentRagStatus
from app.models.notebook import NotebookSource
from app.models.rag import Chunk, DocumentSection, Embedding


def test_phase_four_feature_flags_default_off() -> None:
    assert Settings.model_fields["rag_enabled"].default is False
    assert Settings.model_fields["personalization_enabled"].default is False


def test_rag_models_are_registered_with_expected_vector_dimension() -> None:
    assert DocumentSection.__tablename__ == "document_sections"
    assert Chunk.__tablename__ == "chunks"
    assert Embedding.__tablename__ == "embeddings"
    assert isinstance(Embedding.__table__.c.vector.type, Vector)
    assert Embedding.__table__.c.vector.type.dim == 768
    assert Embedding.__table__.c.dimensions.default.arg == 768


def test_chunks_have_generated_english_full_text_search_vector() -> None:
    search_vector = Chunk.__table__.c.search_vector
    assert isinstance(search_vector.type, TSVECTOR)
    assert isinstance(search_vector.computed, Computed)
    assert str(search_vector.computed.sqltext) == "to_tsvector('english', text)"
    assert search_vector.computed.persisted is True

    gin_index = next(
        index for index in Chunk.__table__.indexes if index.name == "ix_chunks_search_vector_gin"
    )
    assert gin_index.dialect_options["postgresql"]["using"] == "gin"


def test_rag_lifecycle_and_notebooklm_source_id_are_separate() -> None:
    assert Document.__table__.c.rag_status.default.arg is DocumentRagStatus.PENDING
    assert "notebooklm_source_id" in NotebookSource.__table__.c
