"""
Application middleware: rate limiting, request logging, global error handling.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Callable

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Rate limiting (Redis-backed with in-memory fallback) ─────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP rate limiter using Redis sliding window counter.
    Falls back to in-memory token bucket if Redis is unavailable.
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/api/health"]
        self._redis: aioredis.Redis | None = None
        self._redis_available = True
        # In-memory fallback
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": max_requests, "last_refill": time.monotonic()}
        )

    async def _get_redis(self) -> aioredis.Redis | None:
        if not self._redis_available:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.redis_url, decode_responses=True, socket_connect_timeout=2
                )
                await self._redis.ping()
            except Exception:
                logger.warning("Redis unavailable for rate limiting, using in-memory fallback")
                self._redis_available = False
                self._redis = None
                return None
        return self._redis

    async def _check_rate_redis(self, client_ip: str) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        r = await self._get_redis()
        if r is None:
            return self._check_rate_memory(client_ip)
        try:
            key = f"rate:{client_ip}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, self.window_seconds)
            return count <= self.max_requests
        except Exception:
            return self._check_rate_memory(client_ip)

    def _check_rate_memory(self, client_ip: str) -> bool:
        """In-memory token bucket fallback."""
        bucket = self._buckets[client_ip]
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        refill = elapsed * (self.max_requests / self.window_seconds)
        bucket["tokens"] = min(self.max_requests, bucket["tokens"] + refill)
        bucket["last_refill"] = now
        if bucket["tokens"] < 1:
            return False
        bucket["tokens"] -= 1
        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Disable rate limiting during tests
        if os.environ.get("TESTING"):
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed = await self._check_rate_redis(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        return await call_next(request)


# ── Request logging ──────────────────────────────────────────────────────────


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # Skip health check noise
        if request.url.path == "/api/health":
            return response

        logger.info(
            "request_complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
            },
        )
        return response


# ── Global exception handler ─────────────────────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for structured error responses."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred. Please try again later.",
                "error_type": type(exc).__name__,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )
