"""Celery application for async tasks (bulk scoring, backtest, webhooks)."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "paypredict",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    result_expires=3600,  # Results expire after 1 hour
)
