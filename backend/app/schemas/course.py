import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass
class PageResult[T]:
    """Service-layer pagination container — holds ORM instances, not a Pydantic schema."""

    items: list[T]
    total: int
    limit: int
    offset: int


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    created_at: datetime


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
