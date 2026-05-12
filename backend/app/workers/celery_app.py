"""
Celery Background Workers
Handles: file parsing, AI analysis, report generation, notifications
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "vyre",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.parse_uploaded_file": {"queue": "file_parsing"},
        "app.workers.tasks.run_diagnostic_analysis": {"queue": "ai_analysis"},
        "app.workers.tasks.generate_report": {"queue": "report_generation"},
        "app.workers.tasks.send_notification": {"queue": "default"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
