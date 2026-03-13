"""
Application middleware: rate limiting, request logging, global error handling.
"""
import os
import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ── Rate limiting (in-memory token bucket) ───────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple per-IP rate limiter using token bucket algorithm.
    Configurable max requests and refill rate.

    In production, swap for Redis-backed limiter for multi-process support.
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
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": max_requests, "last_refill": time.monotonic()}
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Disable rate limiting during tests
        if os.environ.get("TESTING"):
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]

        # Refill tokens based on elapsed time
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        refill = elapsed * (self.max_requests / self.window_seconds)
        bucket["tokens"] = min(self.max_requests, bucket["tokens"] + refill)
        bucket["last_refill"] = now

        if bucket["tokens"] < 1:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        bucket["tokens"] -= 1
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
