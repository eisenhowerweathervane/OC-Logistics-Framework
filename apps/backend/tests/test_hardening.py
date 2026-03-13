"""Tests for Phase 9 hardening: rate limiting, input validation, error handling."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_not_rate_limited(client: AsyncClient):
    """Health endpoint should be excluded from rate limiting."""
    for _ in range(10):
        resp = await client.get("/api/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_input_validation_load_negative_rate(client: AsyncClient):
    """Negative rate_total should be rejected by Pydantic validation."""
    resp = await client.post("/api/loads", json={
        "rate_total": -500,
        "stops": [{"seq": 1, "stop_type": "pickup"}],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_input_validation_load_excessive_weight(client: AsyncClient):
    """Weight exceeding 200,000 lbs should be rejected."""
    resp = await client.post("/api/loads", json={
        "weight_lbs": 999999,
        "stops": [{"seq": 1, "stop_type": "pickup"}],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_input_validation_stop_seq_zero(client: AsyncClient):
    """Stop seq must be >= 1."""
    resp = await client.post("/api/loads", json={
        "stops": [{"seq": 0, "stop_type": "pickup"}],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_input_validation_status_too_long(client: AsyncClient):
    """Status field capped at 30 chars."""
    load_resp = await client.post("/api/loads", json={
        "stops": [{"seq": 1, "stop_type": "pickup"}],
    })
    load_id = load_resp.json()["id"]

    resp = await client.post(f"/api/loads/{load_id}/status-events", json={
        "status": "a" * 50,
        "occurred_at": "2026-03-12T12:00:00Z",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_input_validation_password_empty(unauthed_client: AsyncClient):
    """Empty password should be rejected."""
    resp = await unauthed_client.post("/api/auth/login", json={
        "email": "test@test.com",
        "password": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_middleware_imports():
    """Verify middleware classes can be imported."""
    from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware, register_exception_handlers
    assert RateLimitMiddleware is not None
    assert RequestLoggingMiddleware is not None
    assert register_exception_handlers is not None
