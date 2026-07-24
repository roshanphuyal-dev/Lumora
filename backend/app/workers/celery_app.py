"""Celery application instance — entrypoint for the worker process.

Run with: `uv run celery -A app.workers.celery_app worker --loglevel=info`
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_tutor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.document_tasks", "app.workers.notebook_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
