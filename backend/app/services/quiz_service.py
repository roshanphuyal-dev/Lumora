import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quiz import Quiz, QuizStatus
from app.schemas.course import PageResult
from app.schemas.quiz import QuizCreate
from app.services.notebook_service import get_owned_notebook
from app.workers.quiz_tasks import generate_quiz_task


async def create_quiz(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    payload: QuizCreate,
) -> Quiz:
    await get_owned_notebook(db, user_id, notebook_id)
    quiz = Quiz(
        notebook_id=notebook_id,
        user_id=user_id,
        status=QuizStatus.PENDING,
        title=payload.title or payload.topic or "Untitled quiz",
        topic=payload.topic or None,
        question_types=payload.question_types,
        question_count=payload.question_count,
        difficulty=payload.difficulty,
        time_limit_seconds=payload.time_limit_seconds,
        include_web_search=payload.include_web_search,
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    generate_quiz_task.delay(str(quiz.id))
    return await get_owned_quiz(db, user_id, notebook_id, quiz.id)


async def list_quizzes(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, limit: int, offset: int
) -> PageResult[Quiz]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [Quiz.notebook_id == notebook_id, Quiz.user_id == user_id]
    total = await db.scalar(select(func.count()).select_from(Quiz).where(*filters))
    result = await db.scalars(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(*filters)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_quiz(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, quiz_id: uuid.UUID
) -> Quiz:
    quiz = await db.scalar(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(
            Quiz.id == quiz_id,
            Quiz.notebook_id == notebook_id,
            Quiz.user_id == user_id,
        )
    )
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz


async def delete_quiz(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, quiz_id: uuid.UUID
) -> None:
    quiz = await get_owned_quiz(db, user_id, notebook_id, quiz_id)
    await db.delete(quiz)
    await db.commit()
