"""Celery application instance — entrypoint for the worker process.

Run with: `uv run celery -A app.workers.celery_app worker --loglevel=info`
"""

from celery import Celery

from app.core.config import get_settings

# Registers every model with Base.metadata before any task runs -- the worker otherwise only
# imports the task modules it needs (below), each touching a couple of models directly, and
# SQLAlchemy can't resolve a cross-table FK (e.g. documents.subject_id -> subjects.id) for a
# model whose module never got imported in this process. Same pattern as backend/tests/conftest.py.
from app.models import (  # noqa: F401
    chat,
    course,
    document,
    flashcard,
    generated_material,
    note,
    notebook,
    quiz,
    quiz_attempt,
    user,
    weak_topic,
)

settings = get_settings()

celery_app = Celery(
    "ai_tutor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.document_tasks",
        "app.workers.notebook_tasks",
        "app.workers.note_tasks",
        "app.workers.flashcard_tasks",
        "app.workers.studio_tasks",
        "app.workers.quiz_tasks",
        "app.workers.quiz_grading_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
