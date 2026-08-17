"""Owner-scoped hybrid pgvector/full-text retrieval for notebook grounding."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from ai.orchestrator.orchestrator import run_task
from ai.orchestrator.schemas import Citation, EmbeddingPurpose, TextEmbeddingRequest
from ai.orchestrator.task_types import TaskType
from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRagStatus
from app.models.notebook import Notebook, NotebookSource
from app.models.rag import Chunk, DocumentSection, Embedding, SectionLocatorKind
from app.schemas.notebook import CitationChunkRead
from app.services.rag_index_service import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

VECTOR_LIMIT = 20
TEXT_LIMIT = 20
RRF_K = 60
MIN_VECTOR_SIMILARITY = 0.55
MAX_RESULTS = 8
MAX_CONTEXT_CHARS = 16_000
MAX_EXCERPT_CHARS = 500
MAX_RESOLVED_TEXT_CHARS = 4_000


@dataclass(frozen=True)
class RetrievalCandidate:
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    document_id: uuid.UUID
    source_title: str
    text: str
    locator_kind: SectionLocatorKind | None = None
    locator: int | None = None
    fused_score: float = 0.0
    vector_similarity: float | None = None
    text_rank: float | None = None


@dataclass(frozen=True)
class LocalGrounding:
    results: list[RetrievalCandidate]
    context: str
    citations: list[Citation]


class LocalRetrievalError(RuntimeError):
    """Raised when local grounding cannot be completed safely."""


async def retrieve(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    query: str,
) -> LocalGrounding:
    """Embed one query, retrieve both channels, fuse, and enforce the context budget."""
    try:
        has_indexed_source = await db.scalar(
            select(func.count())
            .select_from(NotebookSource)
            .join(Notebook, Notebook.id == NotebookSource.notebook_id)
            .join(Document, Document.id == NotebookSource.document_id)
            .join(Chunk, Chunk.document_id == Document.id)
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .where(
                Notebook.id == notebook_id,
                Notebook.owner_id == user_id,
                Document.uploaded_by == user_id,
                Document.rag_status == DocumentRagStatus.INDEXED,
                Embedding.model == EMBEDDING_MODEL,
                Embedding.dimensions == EMBEDDING_DIMENSIONS,
            )
            .limit(1)
        )
        if not has_indexed_source:
            return LocalGrounding(results=[], context="", citations=[])
        response = await run_task(
            TaskType.TEXT_EMBEDDING,
            TextEmbeddingRequest(texts=[query], purpose=EmbeddingPurpose.QUERY),
        )
        if len(response.embeddings) != 1 or len(response.embeddings[0]) != EMBEDDING_DIMENSIONS:
            raise LocalRetrievalError(
                "Query embedding response must contain one 768-dimensional vector."
            )
        vector_results = await _vector_search(db, user_id, notebook_id, response.embeddings[0])
        text_results = await _text_search(db, user_id, notebook_id, query)
    except SQLAlchemyError as exc:
        raise LocalRetrievalError("Local retrieval database query failed.") from exc
    return assemble_grounding(fuse_results(vector_results, text_results))


async def resolve_citation_chunk(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    chunk_id: uuid.UUID,
) -> CitationChunkRead:
    row = (
        await db.execute(
            select(
                NotebookSource.id.label("source_id"),
                Chunk.id.label("chunk_id"),
                func.coalesce(Document.title, Document.filename).label("source_title"),
                DocumentSection.locator_kind,
                DocumentSection.ordinal.label("locator"),
                Chunk.text,
            )
            .join(Notebook, Notebook.id == NotebookSource.notebook_id)
            .join(Document, Document.id == NotebookSource.document_id)
            .join(Chunk, Chunk.document_id == Document.id)
            .outerjoin(DocumentSection, DocumentSection.id == Chunk.section_id)
            .where(
                Notebook.id == notebook_id,
                Notebook.owner_id == user_id,
                NotebookSource.id == source_id,
                Chunk.id == chunk_id,
                Document.uploaded_by == user_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")
    return CitationChunkRead(
        source_id=row.source_id,
        chunk_id=row.chunk_id,
        source_title=row.source_title,
        locator_kind=row.locator_kind.value if row.locator_kind else None,
        locator=row.locator,
        text=row.text[:MAX_RESOLVED_TEXT_CHARS],
    )


def fuse_results(
    vector_results: list[RetrievalCandidate], text_results: list[RetrievalCandidate]
) -> list[RetrievalCandidate]:
    candidates: dict[uuid.UUID, RetrievalCandidate] = {}
    scores: dict[uuid.UUID, float] = {}
    for rank, item in enumerate(vector_results, start=1):
        candidates[item.chunk_id] = item
        scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1 / (RRF_K + rank)
    for rank, item in enumerate(text_results, start=1):
        previous = candidates.get(item.chunk_id)
        candidates[item.chunk_id] = (
            replace(previous, text_rank=item.text_rank) if previous is not None else item
        )
        scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1 / (RRF_K + rank)
    fused = [replace(item, fused_score=scores[item.chunk_id]) for item in candidates.values()]
    return sorted(
        fused,
        key=lambda item: (
            -item.fused_score,
            -(item.vector_similarity or 0.0),
            -(item.text_rank or 0.0),
            str(item.chunk_id),
        ),
    )


def assemble_grounding(candidates: list[RetrievalCandidate]) -> LocalGrounding:
    results: list[RetrievalCandidate] = []
    blocks: list[str] = []
    citations: list[Citation] = []
    used_chars = 0
    for candidate in candidates:
        locator = (
            f", {candidate.locator_kind.value} {candidate.locator}"
            if candidate.locator_kind and candidate.locator
            else ""
        )
        block = f"[Source: {candidate.source_title}{locator}]\n{candidate.text}"
        separator_chars = 2 if blocks else 0
        if (
            len(results) >= MAX_RESULTS
            or used_chars + separator_chars + len(block) > MAX_CONTEXT_CHARS
        ):
            continue
        results.append(candidate)
        blocks.append(block)
        used_chars += separator_chars + len(block)
        citations.append(
            Citation(
                source_id=str(candidate.source_id),
                chunk_id=str(candidate.chunk_id),
                excerpt=candidate.text[:MAX_EXCERPT_CHARS],
                source_title=candidate.source_title,
                locator_kind=candidate.locator_kind.value if candidate.locator_kind else None,
                locator=candidate.locator,
            )
        )
    return LocalGrounding(results=results, context="\n\n".join(blocks), citations=citations)


def _base_query() -> Select:
    return (
        select(
            Chunk.id.label("chunk_id"),
            NotebookSource.id.label("source_id"),
            Chunk.document_id,
            func.coalesce(Document.title, Document.filename).label("source_title"),
            Chunk.text,
            DocumentSection.locator_kind,
            DocumentSection.ordinal.label("locator"),
        )
        .join(Embedding, Embedding.chunk_id == Chunk.id)
        .join(Document, Document.id == Chunk.document_id)
        .join(NotebookSource, NotebookSource.document_id == Document.id)
        .join(Notebook, Notebook.id == NotebookSource.notebook_id)
        .outerjoin(DocumentSection, DocumentSection.id == Chunk.section_id)
        .where(
            Document.uploaded_by == Notebook.owner_id,
            Document.rag_status == DocumentRagStatus.INDEXED,
            Embedding.model == EMBEDDING_MODEL,
            Embedding.dimensions == EMBEDDING_DIMENSIONS,
        )
    )


async def _vector_search(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, query_vector: list[float]
) -> list[RetrievalCandidate]:
    distance = Embedding.vector.cosine_distance(query_vector)
    statement = _scoped_query(user_id, notebook_id).add_columns(distance.label("distance"))
    rows = (
        await db.execute(
            statement.where(distance <= 1 - MIN_VECTOR_SIMILARITY)
            .order_by(distance, Chunk.id)
            .limit(VECTOR_LIMIT)
        )
    ).all()
    return [_candidate(row, vector_similarity=1 - float(row.distance)) for row in rows]


async def _text_search(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, query: str
) -> list[RetrievalCandidate]:
    tsquery = func.plainto_tsquery("english", query)
    rank = func.ts_rank_cd(Chunk.search_vector, tsquery)
    rows = (
        await db.execute(
            _scoped_query(user_id, notebook_id)
            .add_columns(rank.label("text_rank"))
            .where(Chunk.search_vector.op("@@")(tsquery))
            .order_by(rank.desc(), Chunk.id)
            .limit(TEXT_LIMIT)
        )
    ).all()
    return [_candidate(row, text_rank=float(row.text_rank)) for row in rows]


def _scoped_query(user_id: uuid.UUID, notebook_id: uuid.UUID) -> Select:
    return _base_query().where(Notebook.id == notebook_id, Notebook.owner_id == user_id)


def _candidate(row: object, **scores: float) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=row.chunk_id,
        source_id=row.source_id,
        document_id=row.document_id,
        source_title=row.source_title,
        text=row.text,
        locator_kind=row.locator_kind,
        locator=row.locator,
        **scores,
    )
