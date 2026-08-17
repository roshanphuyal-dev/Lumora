import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ExplanationDepth = Literal["concise", "balanced", "detailed"]
ExplanationStyle = Literal["direct", "step_by_step", "socratic", "example_driven"]
SuggestionStatus = Literal["pending", "accepted", "rejected"]
RecommendationPriority = Literal["high", "medium", "low"]
RecommendationAction = Literal["review_topic", "take_quiz", "practice_challenge"]


class LearningPreferenceUpdate(BaseModel):
    explanation_depth: ExplanationDepth | None = None
    explanation_style: ExplanationStyle | None = None


class LearningPreferenceRead(LearningPreferenceUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    user_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LearningPreferenceSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    preference_key: Literal["explanation_depth", "explanation_style"]
    suggested_value: str
    signal_type: str
    rationale: str
    status: SuggestionStatus
    created_at: datetime
    updated_at: datetime


class RecommendationRead(BaseModel):
    action: RecommendationAction
    priority: RecommendationPriority
    topic: str
    url: str
    rationale: str
