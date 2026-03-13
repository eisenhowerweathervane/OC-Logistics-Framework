"""
Thin wrapper around arq's Redis pool for enqueueing jobs.

Usage:
    from app.worker.queue import enqueue
    await enqueue("check_invoice_readiness", str(load_id))

The pool is lazily initialised on first use so tests can run without Redis.
In tests, set REDIS_URL to an invalid value and the enqueue() calls will be
no-ops (the pool init is skipped when SKIP_TASK_QUEUE=true).
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        from arq import create_pool
        from arq.connections import RedisSettings

        from app.core.config import settings

        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue(task_name: str, *args: Any, **kwargs: Any) -> None:
    """Enqueue a background task. Silently skips if SKIP_TASK_QUEUE=true."""
    if os.getenv("SKIP_TASK_QUEUE", "").lower() in ("1", "true", "yes"):
        return
    try:
        pool = await _get_pool()
        await pool.enqueue_job(task_name, *args, **kwargs)
    except Exception:
        # Log but don't surface queue failures to the caller — the HTTP request
        # should still succeed even if Redis is temporarily unavailable.
        logger.exception("task_enqueue_failed", extra={"task": task_name})
