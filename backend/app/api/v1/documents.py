import uuid

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.document import DocumentDetail, DocumentRead
from app.services import document_service
from app.workers.document_tasks import parse_document_task

router = APIRouter(prefix="/documents", tags=["documents"])

Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)
UploadedFile = File(...)
SubjectIdForm = Form(None)


def _infer_file_type(filename: str | None) -> str:
    """Extension-style fallback signal for `app/parsers/registry.py:get_parser`.

    `get_parser` tries `mime_type` first; this only matters when the client's
    reported mime type is missing/generic.
    """
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = UploadedFile,
    subject_id: uuid.UUID | None = SubjectIdForm,
) -> DocumentDetail:
    """Upload a file and start parsing it.

    No signed-upload-URL flow exists yet (no Supabase Storage client is wired
    up — see `app/core/storage.py`), so this endpoint accepts the file bytes
    directly (multipart) and writes them via `FileStorage.upload`, matching
    what `LocalFileStorage`/`FileStorage` actually support today. Swap this
    for a signed-URL flow once a real Supabase Storage client lands.
    """
    content = await file.read()
    document = await document_service.create_document(
        db,
        current_user.id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        file_type=_infer_file_type(file.filename),
        content=content,
        subject_id=subject_id,
    )
    parse_document_task.delay(str(document.id))
    return DocumentDetail.model_validate(document)


@router.get("", response_model=Page[DocumentRead])
async def list_documents(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
    subject_id: uuid.UUID | None = None,
) -> Page[DocumentRead]:
    page = await document_service.list_documents(
        db, current_user.id, limit, offset, subject_id=subject_id
    )
    return Page[DocumentRead](
        items=[DocumentRead.model_validate(d) for d in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> DocumentDetail:
    """Document detail — also the parse-status poll endpoint (`parse_status` +
    `extracted_text` once parsing completes); the document_id doubles as the
    job handle since parsing starts right after upload.
    """
    document = await document_service.get_owned_document(db, current_user.id, document_id)
    return DocumentDetail.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    await document_service.delete_document(db, current_user.id, document_id)
