"""
arq worker entry point.

Run with:
    python -m arq app.worker.main.WorkerSettings

Or via docker-compose worker service:
    command: python -m arq app.worker.main.WorkerSettings
"""

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.worker.tasks import (
    check_invoice_readiness,
    daily_compliance_digest,
    document_retention_cleanup,
    notify_load_delivered,
    weekly_ar_reminder,
)


class WorkerSettings:
    # On-demand tasks (enqueued by HTTP routes)
    functions = [check_invoice_readiness, notify_load_delivered]

    # Scheduled tasks (cron-like)
    cron_jobs = [
        cron(daily_compliance_digest, hour=7, minute=0),  # 7 AM UTC daily
        cron(weekly_ar_reminder, weekday=1, hour=9, minute=0),  # Monday 9 AM UTC
        cron(document_retention_cleanup, hour=3, minute=0),  # 3 AM UTC daily
    ]

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 minutes
