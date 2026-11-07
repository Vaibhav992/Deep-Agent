"""Celery config — for periodic/scheduled jobs only.

Event-driven work (embeddings, guardrail audit, etc.) goes through Kafka.
Celery is kept for:
- Scheduled cleanup (old STM archives, expired sessions)
- Periodic reports (weekly usage summaries)
- One-off delayed tasks (send notification in 5 min)
"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery = Celery(
    "deep-agent",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Phase 7: add scheduled tasks here
        # "cleanup-old-archives": {
        #     "task": "app.tasks.cleanup_old_archives",
        #     "schedule": crontab(hour=3, minute=0),  # daily at 3 AM
        # },
    },
)
