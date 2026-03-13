"""Tests for /api/auth routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(unauthed_client: AsyncClient, seeded_db):
    _, user, _ = seeded_db
    resp = await unauthed_client.post(
        "/api/auth/login",
        json={
            "email": "owner@test.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(unauthed_client: AsyncClient, seeded_db):
    resp = await unauthed_client.post(
        "/api/auth/login",
        json={
            "email": "owner@test.com",
            "password": "wrongpassword",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(unauthed_client: AsyncClient, seeded_db):
    resp = await unauthed_client.post(
        "/api/auth/login",
        json={
            "email": "nobody@test.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "owner@test.com"
    assert "owner" in data["roles"]


@pytest.mark.asyncio
async def test_me_unauthenticated(unauthed_client: AsyncClient, seeded_db):
    resp = await unauthed_client.get("/api/auth/me")
    assert resp.status_code in (401, 403)  # HTTPBearer returns 401/403 when no token


@pytest.mark.asyncio
async def test_refresh(unauthed_client: AsyncClient, seeded_db):
    # Get tokens via login
    login = await unauthed_client.post(
        "/api/auth/login",
        json={
            "email": "owner@test.com",
            "password": "password123",
        },
    )
    refresh_token = login.json()["refresh_token"]

    resp = await unauthed_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 204
