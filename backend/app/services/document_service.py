"""Document persistence for the parsing pipeline and the Document API.

`get_document`/`mark_processing`/`mark_parsed`/`mark_parse_failed` below are
NOT scoped to a requesting user — they're called from the Celery worker
(app/workers/document_tasks.py) on a document_id the backend itself enqueued
after already checking ownership at upload time, not on a client-supplied ID
from an inbound request.

Everything below the worker-only section IS user-scoped and backs
`app/api/v1/documents.py` — each function takes a `user_id` and filters on
`Document.uploaded_by` itself rather than reusing `get_document`, per the
note above.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_file_storage
from app.models.document import Document, DocumentParseStatus
from app.schemas.course import PageResult


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


async def mark_processing(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await get_document(db, document_id)
    document.parse_status = DocumentParseStatus.PROCESSING
    await db.commit()
    await db.refresh(document)
    return document


async def mark_parsed(db: AsyncSession, document_id: uuid.UUID, extracted_text: str) -> Document:
    document = await get_document(db, document_id)
    document.extracted_text = extracted_text
    document.parse_status = DocumentParseStatus.DONE
    await db.commit()
    await db.refresh(document)
    return document


async def mark_parse_failed(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await get_document(db, document_id)
    document.parse_status = DocumentParseStatus.FAILED
    await db.commit()
    await db.refresh(document)
    return document


# --- User-scoped: backs app/api/v1/documents.py -----------------------------------


async def create_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    filename: str,
    mime_type: str,
    file_type: str,
    content: bytes,
    subject_id: uuid.UUID | None = None,
) -> Document:
    """Persist the uploaded bytes and create the `Document` row in `pending` status.

    Does NOT dispatch `parse_document_task` — the caller (the upload route) does
    that once this returns, to avoid a circular import between this module and
    `app/workers/document_tasks.py` (which itself imports this module).
    """
    document_id = uuid.uuid4()
    storage_path = f"{user_id}/{document_id}/{filename}"
    await get_file_storage().upload(storage_path, content)

    document = Document(
        id=document_id,
        uploaded_by=user_id,
        subject_id=subject_id,
        filename=filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_type=file_type,
        parse_status=DocumentParseStatus.PENDING,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def get_owned_document(
    db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID
) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.uploaded_by == user_id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


async def list_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
    *,
    subject_id: uuid.UUID | None = None,
) -> PageResult[Document]:
    filters = [Document.uploaded_by == user_id]
    if subject_id is not None:
        filters.append(Document.subject_id == subject_id)

    total = await db.scalar(select(func.count()).select_from(Document).where(*filters))
    result = await db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def delete_document(db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = await get_owned_document(db, user_id, document_id)
    await db.delete(document)
    await db.commit()
