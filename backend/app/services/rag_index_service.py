"""Persistence operations for the local document indexing lifecycle."""

import uuid

from ai.orchestrator.schemas import TextEmbeddingResponse
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRagStatus
from app.models.rag import Chunk, DocumentSection, Embedding, SectionLocatorKind
from app.parsers.base import ParsedDocument
from app.rag.chunking import chunk_text

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_MODEL_VERSION = "001"
EMBEDDING_DIMENSIONS = 768


async def claim_document(db: AsyncSession, document_id: uuid.UUID) -> bool:
    """Atomically claim one pending/failed document for indexing."""
    claimed_id = await db.scalar(
        update(Document)
        .where(
            Document.id == document_id,
            Document.rag_status.in_([DocumentRagStatus.PENDING, DocumentRagStatus.FAILED]),
        )
        .values(rag_status=DocumentRagStatus.INDEXING)
        .returning(Document.id)
    )
    await db.commit()
    return claimed_id is not None


def locator_kind(file_type: str) -> SectionLocatorKind:
    if file_type == "pdf":
        return SectionLocatorKind.PAGE
    if file_type == "pptx":
        return SectionLocatorKind.SLIDE
    return SectionLocatorKind.GENERIC


async def persist_parsed_document(
    db: AsyncSession, document: Document, parsed: ParsedDocument
) -> None:
    """Atomically replace parser sections and mark parsing complete."""
    await db.execute(delete(DocumentSection).where(DocumentSection.document_id == document.id))
    document.extracted_text = parsed.text
    document.parse_status = "done"
    document.rag_status = DocumentRagStatus.PENDING
    kind = locator_kind(document.file_type)
    for section in parsed.sections:
        db.add(
            DocumentSection(
                document_id=document.id,
                ordinal=section.index,
                locator_kind=kind,
                text=section.text,
            )
        )
    await db.commit()


async def build_chunks(db: AsyncSession, document_id: uuid.UUID) -> list[Chunk]:
    document = await db.get(Document, document_id)
    if document is None:
        return []
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    sections = list(
        await db.scalars(
            select(DocumentSection)
            .where(DocumentSection.document_id == document_id)
            .order_by(DocumentSection.ordinal)
        )
    )
    if not sections and document.extracted_text:
        sections = [
            DocumentSection(document_id=document.id, ordinal=1, text=document.extracted_text)
        ]
        db.add_all(sections)
        await db.flush()
    chunks: list[Chunk] = []
    ordinal = 1
    for section in sections:
        for draft in chunk_text(section.text):
            chunk = Chunk(
                document_id=document.id,
                section_id=section.id,
                ordinal=ordinal,
                text=draft.text,
                content_hash=draft.content_hash,
            )
            db.add(chunk)
            chunks.append(chunk)
            ordinal += 1
    await db.commit()
    return chunks


async def persist_embeddings(
    db: AsyncSession, chunks: list[Chunk], response: TextEmbeddingResponse
) -> None:
    for chunk, vector in zip(chunks, response.embeddings, strict=True):
        db.add(
            Embedding(
                chunk_id=chunk.id,
                vector=vector,
                model=EMBEDDING_MODEL,
                model_version=EMBEDDING_MODEL_VERSION,
                dimensions=EMBEDDING_DIMENSIONS,
            )
        )
    await db.commit()


async def mark_failed(db: AsyncSession, document_id: uuid.UUID) -> None:
    document = await db.get(Document, document_id)
    if document is not None:
        document.rag_status = DocumentRagStatus.FAILED
        await db.commit()


async def mark_indexed(db: AsyncSession, document_id: uuid.UUID) -> None:
    document = await db.get(Document, document_id)
    if document is not None:
        document.rag_status = DocumentRagStatus.INDEXED
        await db.commit()
