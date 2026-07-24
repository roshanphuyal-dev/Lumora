import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Subject
from app.schemas.course import PageResult


async def create_course(db: AsyncSession, user_id: uuid.UUID, name: str) -> Course:
    course = Course(user_id=user_id, name=name)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def list_courses(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> PageResult[Course]:
    total = await db.scalar(
        select(func.count()).select_from(Course).where(Course.user_id == user_id)
    )
    result = await db.scalars(
        select(Course)
        .where(Course.user_id == user_id)
        .order_by(Course.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_course(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> Course:
    course = await db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def delete_course(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> None:
    course = await get_owned_course(db, user_id, course_id)
    await db.delete(course)
    await db.commit()


async def create_subject(
    db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID, name: str
) -> Subject:
    await get_owned_course(db, user_id, course_id)
    subject = Subject(course_id=course_id, name=name)
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


async def list_subjects(
    db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID, limit: int, offset: int
) -> PageResult[Subject]:
    await get_owned_course(db, user_id, course_id)
    total = await db.scalar(
        select(func.count()).select_from(Subject).where(Subject.course_id == course_id)
    )
    result = await db.scalars(
        select(Subject)
        .where(Subject.course_id == course_id)
        .order_by(Subject.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)
