import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.course import Page


class TopicMasteryRead(BaseModel):
    topic: str
    mastery_percent: float
    confidence: float
    evidence_weight: float
    evidence_count: int
    calculated_at: datetime


class NotebookProgressRead(BaseModel):
    notebook_id: uuid.UUID
    graded_attempts: int
    answered_questions: int
    average_score_percent: float | None
    topics_tracked: int
    low_mastery_topics: int


class QuizPerformancePoint(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    graded_at: datetime
    score_percent: float


class DailyQuizPerformance(BaseModel):
    day: date
    attempts: int
    average_score_percent: float


class QuizPerformanceRead(BaseModel):
    recent_attempts: Page[QuizPerformancePoint]
    daily: list[DailyQuizPerformance]


ClientActivityType = Literal["study_session", "material_viewed", "material_revised"]
ResourceType = Literal["document", "note", "flashcard_set", "quiz", "notebook"]


class StudyActivityCreate(BaseModel):
    activity_key: uuid.UUID
    activity_type: ClientActivityType
    duration_seconds: int = Field(ge=0, le=14_400)
    occurred_at: datetime
    resource_type: ResourceType | None = None
    resource_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_boundary(self) -> "StudyActivityCreate":
        now = datetime.now(UTC)
        occurred_at = self.occurred_at
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        if occurred_at > now + timedelta(minutes=5):
            raise ValueError("occurred_at cannot be in the future")
        if occurred_at < now - timedelta(days=7):
            raise ValueError("occurred_at cannot be more than 7 days old")
        if (self.resource_type is None) != (self.resource_id is None):
            raise ValueError("resource_type and resource_id must be provided together")
        return self


class StudyActivityRead(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    activity_key: uuid.UUID
    activity_type: str
    duration_seconds: int
    occurred_at: datetime
    resource_type: str | None
    resource_id: uuid.UUID | None


class ActivityHeatmapDay(BaseModel):
    day: date
    duration_seconds: int
    activity_count: int


class ActivityAnalyticsRead(BaseModel):
    total_study_seconds: int
    current_streak_days: int
    longest_streak_days: int
    active_days: int
    heatmap: list[ActivityHeatmapDay]


class RevisionHistoryItem(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    activity_type: str
    occurred_at: datetime
    duration_seconds: int
    resource_type: str | None
    resource_id: uuid.UUID | None
