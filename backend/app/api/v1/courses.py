import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import CourseCreate, CourseRead, Page, SubjectCreate, SubjectRead
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])

Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate, current_user: CurrentUser, db: DbSession
) -> CourseRead:
    course = await course_service.create_course(db, current_user.id, payload.name)
    return CourseRead.model_validate(course)


@router.get("", response_model=Page[CourseRead])
async def list_courses(
    current_user: CurrentUser, db: DbSession, limit: int = Limit, offset: int = Offset
) -> Page[CourseRead]:
    page = await course_service.list_courses(db, current_user.id, limit, offset)
    return Page[CourseRead](
        items=[CourseRead.model_validate(c) for c in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    await course_service.delete_course(db, current_user.id, course_id)


@router.post(
    "/{course_id}/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED
)
async def create_subject(
    course_id: uuid.UUID, payload: SubjectCreate, current_user: CurrentUser, db: DbSession
) -> SubjectRead:
    subject = await course_service.create_subject(db, current_user.id, course_id, payload.name)
    return SubjectRead.model_validate(subject)


@router.get("/{course_id}/subjects", response_model=Page[SubjectRead])
async def list_subjects(
    course_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[SubjectRead]:
    page = await course_service.list_subjects(db, current_user.id, course_id, limit, offset)
    return Page[SubjectRead](
        items=[SubjectRead.model_validate(s) for s in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
