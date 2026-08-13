from pgvector.sqlalchemy import Vector

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


def test_rag_lifecycle_and_notebooklm_source_id_are_separate() -> None:
    assert Document.__table__.c.rag_status.default.arg is DocumentRagStatus.PENDING
    assert "notebooklm_source_id" in NotebookSource.__table__.c
