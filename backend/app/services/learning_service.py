import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.flashcard import FlashcardSet
from app.models.learning import LearningEvidence, StudyActivity, StudyActivityType, TopicMastery
from app.models.note import Note
from app.models.notebook import Notebook, NotebookSource
from app.models.quiz import Quiz, QuizDifficulty
from app.models.quiz_attempt import QuizAttempt, QuizAttemptAnswer, QuizAttemptStatus
from app.schemas.course import PageResult
from app.schemas.learning import (
    ActivityAnalyticsRead,
    ActivityHeatmapDay,
    DailyQuizPerformance,
    NotebookProgressRead,
    QuizPerformancePoint,
    QuizPerformanceRead,
    RevisionHistoryItem,
    StudyActivityCreate,
    TopicMasteryRead,
)
from app.services.notebook_service import get_owned_notebook

_DIFFICULTY_MULTIPLIERS = {
    QuizDifficulty.EASY.value: 0.75,
    QuizDifficulty.MEDIUM.value: 1.0,
    QuizDifficulty.MIXED.value: 1.0,
    QuizDifficulty.HARD.value: 1.25,
}


@dataclass(frozen=True)
class MasteryCalculation:
    mastery_percent: float
    confidence: float
    evidence_weight: float
    evidence_count: int


def calculate_mastery(
    evidence: list[tuple[float, str, datetime]], *, now: datetime | None = None
) -> MasteryCalculation:
    """Apply ADR 0014's neutral-prior, difficulty, and 30-day half-life formula."""
    calculated_at = now or datetime.now(UTC)
    weighted_score = 0.0
    total_weight = 0.0
    for score, difficulty, observed_at in evidence:
        age_seconds = max(0.0, (calculated_at - observed_at).total_seconds())
        age_days = age_seconds / 86_400
        multiplier = _DIFFICULTY_MULTIPLIERS[difficulty]
        weight = multiplier * math.pow(0.5, age_days / 30)
        weighted_score += weight * score
        total_weight += weight
    return MasteryCalculation(
        mastery_percent=(1 + weighted_score) / (2 + total_weight) * 100,
        confidence=min(1.0, total_weight / 5),
        evidence_weight=total_weight,
        evidence_count=len(evidence),
    )


async def record_attempt_evidence(
    db: AsyncSession,
    attempt: QuizAttempt,
    notebook_id: uuid.UUID,
    answer_rows: list[QuizAttemptAnswer],
    *,
    observed_at: datetime,
) -> None:
    """Stage idempotent evidence and mastery snapshots in the caller's transaction."""
    existing_ids = (
        set(
            await db.scalars(
                select(LearningEvidence.attempt_answer_id).where(
                    LearningEvidence.attempt_answer_id.in_([row.id for row in answer_rows])
                )
            )
        )
        if answer_rows
        else set()
    )
    affected_topics: set[str] = set()
    canonical_topics: dict[str, str] = {}
    for row in answer_rows:
        topic = row.topic_tag.strip() if row.topic_tag else ""
        if not topic or row.id in existing_ids or row.is_correct is None:
            continue
        topic_key = topic.casefold()
        if topic_key not in canonical_topics:
            existing_mastery = await db.scalar(
                select(TopicMastery).where(
                    TopicMastery.user_id == attempt.user_id,
                    TopicMastery.notebook_id == notebook_id,
                    func.lower(TopicMastery.topic) == topic.lower(),
                )
            )
            canonical_topics[topic_key] = existing_mastery.topic if existing_mastery else topic
        topic = canonical_topics[topic_key]
        score = min(1.0, max(0.0, float(row.score)))
        db.add(
            LearningEvidence(
                user_id=attempt.user_id,
                notebook_id=notebook_id,
                attempt_answer_id=row.id,
                topic=topic,
                difficulty=row.question.difficulty.value,
                score=Decimal(str(score)),
                observed_at=observed_at,
            )
        )
        affected_topics.add(topic)
    await db.flush()
    for topic in affected_topics:
        await _refresh_mastery(db, attempt.user_id, notebook_id, topic, now=observed_at)


async def _topic_evidence(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, topic: str
) -> list[tuple[float, str, datetime]]:
    rows = await db.execute(
        select(LearningEvidence.score, LearningEvidence.difficulty, LearningEvidence.observed_at)
        .join(Notebook, Notebook.id == LearningEvidence.notebook_id)
        .where(
            LearningEvidence.user_id == user_id,
            LearningEvidence.notebook_id == notebook_id,
            func.lower(LearningEvidence.topic) == topic.lower(),
            Notebook.owner_id == user_id,
        )
    )
    return [(float(score), difficulty, observed_at) for score, difficulty, observed_at in rows]


async def _refresh_mastery(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    topic: str,
    *,
    now: datetime,
) -> None:
    calculation = calculate_mastery(await _topic_evidence(db, user_id, notebook_id, topic), now=now)
    mastery = await db.scalar(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.notebook_id == notebook_id,
            func.lower(TopicMastery.topic) == topic.lower(),
        )
    )
    if mastery is None:
        mastery = TopicMastery(user_id=user_id, notebook_id=notebook_id, topic=topic)
        db.add(mastery)
    mastery.mastery_percent = Decimal(str(calculation.mastery_percent))
    mastery.confidence = Decimal(str(calculation.confidence))
    mastery.evidence_weight = Decimal(str(calculation.evidence_weight))
    mastery.evidence_count = calculation.evidence_count
    mastery.calculated_at = now


async def get_topic_mastery(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    topic: str,
) -> TopicMasteryRead | None:
    """Return one owner-scoped, live-decayed mastery value by case-insensitive topic."""
    await get_owned_notebook(db, user_id, notebook_id)
    normalized_topic = topic.strip()
    if not normalized_topic:
        return None
    snapshot = await db.scalar(
        select(TopicMastery)
        .join(Notebook, Notebook.id == TopicMastery.notebook_id)
        .where(
            TopicMastery.user_id == user_id,
            TopicMastery.notebook_id == notebook_id,
            func.lower(TopicMastery.topic) == normalized_topic.lower(),
            Notebook.owner_id == user_id,
        )
    )
    if snapshot is None:
        return None
    now = datetime.now(UTC)
    calculation = calculate_mastery(
        await _topic_evidence(db, user_id, notebook_id, snapshot.topic), now=now
    )
    return TopicMasteryRead(
        topic=snapshot.topic,
        mastery_percent=calculation.mastery_percent,
        confidence=calculation.confidence,
        evidence_weight=calculation.evidence_weight,
        evidence_count=calculation.evidence_count,
        calculated_at=now,
    )


async def list_topic_mastery(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    limit: int,
    offset: int,
) -> PageResult[TopicMasteryRead]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [TopicMastery.user_id == user_id, TopicMastery.notebook_id == notebook_id]
    total = await db.scalar(select(func.count()).select_from(TopicMastery).where(*filters))
    snapshots = list(
        await db.scalars(
            select(TopicMastery)
            .join(Notebook, Notebook.id == TopicMastery.notebook_id)
            .where(*filters, Notebook.owner_id == user_id)
            .order_by(TopicMastery.mastery_percent.asc(), TopicMastery.topic.asc())
            .limit(limit)
            .offset(offset)
        )
    )
    now = datetime.now(UTC)
    items = []
    for snapshot in snapshots:
        calculation = calculate_mastery(
            await _topic_evidence(db, user_id, notebook_id, snapshot.topic), now=now
        )
        items.append(
            TopicMasteryRead(
                topic=snapshot.topic,
                mastery_percent=calculation.mastery_percent,
                confidence=calculation.confidence,
                evidence_weight=calculation.evidence_weight,
                evidence_count=calculation.evidence_count,
                calculated_at=now,
            )
        )
    return PageResult(items=items, total=total or 0, limit=limit, offset=offset)


async def get_notebook_progress(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID
) -> NotebookProgressRead:
    await get_owned_notebook(db, user_id, notebook_id)
    attempt_filters = [
        QuizAttempt.user_id == user_id,
        QuizAttempt.status == QuizAttemptStatus.GRADED,
        Quiz.notebook_id == notebook_id,
        Quiz.user_id == user_id,
    ]
    graded_attempts = await db.scalar(
        select(func.count()).select_from(QuizAttempt).join(Quiz).where(*attempt_filters)
    )
    totals = await db.execute(
        select(func.sum(QuizAttempt.score), func.sum(QuizAttempt.max_score))
        .join(Quiz)
        .where(*attempt_filters)
    )
    total_score, max_score = totals.one()
    answered_questions = await db.scalar(
        select(func.count())
        .select_from(LearningEvidence)
        .join(Notebook, Notebook.id == LearningEvidence.notebook_id)
        .where(
            LearningEvidence.user_id == user_id,
            LearningEvidence.notebook_id == notebook_id,
            Notebook.owner_id == user_id,
        )
    )
    mastery_page = await list_topic_mastery(db, user_id, notebook_id, 100, 0)
    return NotebookProgressRead(
        notebook_id=notebook_id,
        graded_attempts=graded_attempts or 0,
        answered_questions=answered_questions or 0,
        average_score_percent=(
            float(total_score / max_score * 100) if max_score and max_score > 0 else None
        ),
        topics_tracked=mastery_page.total,
        low_mastery_topics=sum(item.mastery_percent < 40 for item in mastery_page.items),
    )


async def get_quiz_performance(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    limit: int,
    offset: int,
) -> QuizPerformanceRead:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [
        QuizAttempt.user_id == user_id,
        QuizAttempt.status == QuizAttemptStatus.GRADED,
        QuizAttempt.max_score > 0,
        Quiz.notebook_id == notebook_id,
        Quiz.user_id == user_id,
    ]
    total = await db.scalar(
        select(func.count()).select_from(QuizAttempt).join(Quiz).where(*filters)
    )
    attempts = list(
        await db.scalars(
            select(QuizAttempt)
            .join(Quiz)
            .where(*filters)
            .order_by(QuizAttempt.graded_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    points = [
        QuizPerformancePoint(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            graded_at=attempt.graded_at,
            score_percent=float(attempt.score / attempt.max_score * 100),
        )
        for attempt in attempts
        if attempt.graded_at is not None and attempt.score is not None and attempt.max_score
    ]
    daily_values: dict = defaultdict(list)
    for point in points:
        daily_values[point.graded_at.date()].append(point.score_percent)
    daily = [
        DailyQuizPerformance(
            day=day, attempts=len(scores), average_score_percent=sum(scores) / len(scores)
        )
        for day, scores in sorted(daily_values.items())
    ]
    return QuizPerformanceRead(
        recent_attempts={"items": points, "total": total or 0, "limit": limit, "offset": offset},
        daily=daily,
    )


async def record_study_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    payload: StudyActivityCreate,
) -> StudyActivity:
    await get_owned_notebook(db, user_id, notebook_id)
    if payload.resource_type is not None and payload.resource_id is not None:
        await _validate_activity_resource(
            db,
            user_id,
            notebook_id,
            payload.resource_type,
            payload.resource_id,
        )
    activity = await _insert_activity(
        db,
        user_id=user_id,
        notebook_id=notebook_id,
        activity_key=payload.activity_key,
        activity_type=payload.activity_type,
        duration_seconds=payload.duration_seconds,
        occurred_at=payload.occurred_at.astimezone(UTC),
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    await db.commit()
    await db.refresh(activity)
    return activity


async def _validate_activity_resource(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
) -> None:
    if resource_type == "notebook":
        exists = resource_id == notebook_id
    elif resource_type == "document":
        exists = bool(
            await db.scalar(
                select(func.count())
                .select_from(NotebookSource)
                .join(Document, Document.id == NotebookSource.document_id)
                .join(Notebook, Notebook.id == NotebookSource.notebook_id)
                .where(
                    NotebookSource.notebook_id == notebook_id,
                    NotebookSource.document_id == resource_id,
                    Notebook.owner_id == user_id,
                    Document.uploaded_by == user_id,
                )
            )
        )
    else:
        model = {"note": Note, "flashcard_set": FlashcardSet, "quiz": Quiz}[resource_type]
        exists = bool(
            await db.scalar(
                select(func.count())
                .select_from(model)
                .where(
                    model.id == resource_id,
                    model.notebook_id == notebook_id,
                    model.user_id == user_id,
                )
            )
        )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity resource not found"
        )


async def record_quiz_completed_activity(
    db: AsyncSession,
    attempt: QuizAttempt,
    notebook_id: uuid.UUID,
    *,
    occurred_at: datetime,
) -> None:
    """Stage one idempotent quiz-completion event in the grading transaction."""
    elapsed = max(0, int((occurred_at - attempt.started_at).total_seconds()))
    await _insert_activity(
        db,
        user_id=attempt.user_id,
        notebook_id=notebook_id,
        activity_key=attempt.id,
        activity_type=StudyActivityType.QUIZ_COMPLETED.value,
        duration_seconds=min(14_400, elapsed),
        occurred_at=occurred_at,
        resource_type="quiz",
        resource_id=attempt.quiz_id,
    )


async def _insert_activity(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    activity_key: uuid.UUID,
    activity_type: str,
    duration_seconds: int,
    occurred_at: datetime,
    resource_type: str | None,
    resource_id: uuid.UUID | None,
) -> StudyActivity:
    statement = (
        pg_insert(StudyActivity)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            notebook_id=notebook_id,
            activity_key=activity_key,
            activity_type=activity_type,
            duration_seconds=duration_seconds,
            occurred_at=occurred_at,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        .on_conflict_do_nothing(constraint="uq_study_activities_user_key")
        .returning(StudyActivity.id)
    )
    inserted_id = await db.scalar(statement)
    if inserted_id is not None:
        activity = await db.scalar(select(StudyActivity).where(StudyActivity.id == inserted_id))
    else:
        activity = await db.scalar(
            select(StudyActivity).where(
                StudyActivity.user_id == user_id,
                StudyActivity.activity_key == activity_key,
            )
        )
    if activity is None:  # pragma: no cover - insert/query contract guarantees a row
        raise RuntimeError("Study activity could not be persisted")
    return activity


def calculate_streaks(active_dates: list[date], *, today: date | None = None) -> tuple[int, int]:
    unique_dates = sorted(set(active_dates))
    if not unique_dates:
        return 0, 0
    longest = 1
    run = 1
    for previous, current in zip(unique_dates, unique_dates[1:], strict=False):
        if current == previous + timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    current_day = today or datetime.now(UTC).date()
    if unique_dates[-1] < current_day - timedelta(days=1):
        return 0, longest
    current = 1
    for index in range(len(unique_dates) - 1, 0, -1):
        if unique_dates[index - 1] != unique_dates[index] - timedelta(days=1):
            break
        current += 1
    return current, longest


async def get_activity_analytics(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    notebook_id: uuid.UUID | None,
    days: int,
) -> ActivityAnalyticsRead:
    if notebook_id is not None:
        await get_owned_notebook(db, user_id, notebook_id)
    start_date = datetime.now(UTC).date() - timedelta(days=days - 1)
    filters = [
        StudyActivity.user_id == user_id,
        StudyActivity.occurred_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
        Notebook.owner_id == user_id,
    ]
    if notebook_id is not None:
        filters.append(StudyActivity.notebook_id == notebook_id)
    activity_day = func.date(StudyActivity.occurred_at)
    rows = await db.execute(
        select(
            activity_day,
            func.sum(StudyActivity.duration_seconds),
            func.count(StudyActivity.id),
        )
        .join(Notebook, Notebook.id == StudyActivity.notebook_id)
        .where(*filters)
        .group_by(activity_day)
        .order_by(activity_day)
    )
    heatmap = [
        ActivityHeatmapDay(
            day=day,
            duration_seconds=int(duration or 0),
            activity_count=count,
        )
        for day, duration, count in rows
    ]
    current_streak, longest_streak = calculate_streaks([item.day for item in heatmap])
    return ActivityAnalyticsRead(
        total_study_seconds=sum(item.duration_seconds for item in heatmap),
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        active_days=len(heatmap),
        heatmap=heatmap,
    )


async def list_revision_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    limit: int,
    offset: int,
) -> PageResult[RevisionHistoryItem]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [
        StudyActivity.user_id == user_id,
        StudyActivity.notebook_id == notebook_id,
        StudyActivity.activity_type.in_(
            [
                StudyActivityType.MATERIAL_VIEWED.value,
                StudyActivityType.MATERIAL_REVISED.value,
                StudyActivityType.QUIZ_COMPLETED.value,
            ]
        ),
    ]
    total = await db.scalar(select(func.count()).select_from(StudyActivity).where(*filters))
    activities = list(
        await db.scalars(
            select(StudyActivity)
            .join(Notebook, Notebook.id == StudyActivity.notebook_id)
            .where(*filters, Notebook.owner_id == user_id)
            .order_by(StudyActivity.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return PageResult(
        items=[
            RevisionHistoryItem(
                id=item.id,
                notebook_id=item.notebook_id,
                activity_type=item.activity_type,
                occurred_at=item.occurred_at,
                duration_seconds=item.duration_seconds,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
            )
            for item in activities
        ],
        total=total or 0,
        limit=limit,
        offset=offset,
    )
