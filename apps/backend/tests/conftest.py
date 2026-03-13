"""
Test configuration.

Uses an in-memory SQLite database (via aiosqlite) so tests run without Postgres or Docker.
MinIO/S3 calls are mocked via monkeypatching.
"""

import os
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point at SQLite for tests before any app module loads config
os.environ["TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")

from app.core.security import create_access_token, hash_password
from app.db.base import Base, get_db
from app.db.models.org import Organization, Role, User, UserRole
from app.main import app

TEST_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_db(db: AsyncSession):
    """Returns (org, owner_user, access_token)."""
    now = datetime.now(timezone.utc)

    org = Organization(legal_name="Test Carrier LLC", country="US")
    db.add(org)
    await db.flush()

    role = Role(name="owner", created_at=now)
    db.add(role)
    await db.flush()

    disp_role = Role(name="dispatcher", created_at=now)
    db.add(disp_role)
    await db.flush()

    driver_role = Role(name="driver", created_at=now)
    db.add(driver_role)
    await db.flush()

    user = User(
        organization_id=org.id,
        email="owner@test.com",
        password_hash=hash_password("password123"),
        status="active",
    )
    db.add(user)
    await db.flush()

    ur = UserRole(user_id=user.id, role_id=role.id, created_at=now)
    db.add(ur)
    await db.commit()

    token = create_access_token(user.id)
    return org, user, token


@pytest_asyncio.fixture
async def client(seeded_db) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth token pre-set, DB overridden to test session."""
    org, user, token = seeded_db

    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthed_client() -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
