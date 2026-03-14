"""Multi-tenant isolation integration tests.

Verify that data created under Organization A is invisible to Organization B,
both on list endpoints (items don't appear) and single-item GET endpoints
(returns 404, not 403).  Covers loads and drivers.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.base import get_db
from app.db.models.org import Organization, Role, User, UserRole
from app.main import app

from .conftest import TestSession

# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

LOAD_BODY_A = {
    "commodity": "Steel Beams",
    "rate_total": "3200.00",
    "rate_type": "flat",
    "miles_loaded": "620",
    "miles_deadhead_est": "35",
    "stops": [
        {
            "seq": 1,
            "stop_type": "pickup",
            "facility_name": "Org-A Warehouse",
            "city": "Detroit",
            "state": "MI",
        },
        {
            "seq": 2,
            "stop_type": "delivery",
            "facility_name": "Org-A Receiver",
            "city": "Indianapolis",
            "state": "IN",
        },
    ],
}

LOAD_BODY_B = {
    "commodity": "Frozen Produce",
    "rate_total": "2750.00",
    "rate_type": "flat",
    "miles_loaded": "410",
    "miles_deadhead_est": "15",
    "stops": [
        {
            "seq": 1,
            "stop_type": "pickup",
            "facility_name": "Org-B Cold Storage",
            "city": "Memphis",
            "state": "TN",
        },
        {
            "seq": 2,
            "stop_type": "delivery",
            "facility_name": "Org-B Grocer",
            "city": "Nashville",
            "state": "TN",
        },
    ],
}

DRIVER_BODY_A = {"first_name": "Alice", "last_name": "Anderson", "phone": "555-0001"}
DRIVER_BODY_B = {"first_name": "Bob", "last_name": "Baker", "phone": "555-0002"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _ensure_role(db: AsyncSession, name: str) -> Role:
    """Return the role with *name*, creating it only if it doesn't exist yet."""
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role:
        return role
    role = Role(name=name, created_at=datetime.now(timezone.utc))
    db.add(role)
    await db.flush()
    return role


async def _create_org_user_token(
    db: AsyncSession,
    *,
    legal_name: str,
    email: str,
    password: str = "password123",
) -> tuple[Organization, User, str]:
    """Insert an org + owner user and return (org, user, jwt_token)."""
    org = Organization(legal_name=legal_name, country="US")
    db.add(org)
    await db.flush()

    owner_role = await _ensure_role(db, "owner")
    # dispatcher role needed so the user can create loads/drivers
    dispatcher_role = await _ensure_role(db, "dispatcher")
    # driver role may be referenced elsewhere; create once
    await _ensure_role(db, "driver")

    user = User(
        organization_id=org.id,
        email=email,
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    await db.flush()

    for role in (owner_role, dispatcher_role):
        db.add(UserRole(user_id=user.id, role_id=role.id, created_at=datetime.now(timezone.utc)))
    await db.commit()

    token = create_access_token(user.id)
    return org, user, token


async def _make_client(token: str) -> AsyncClient:
    """Build an httpx AsyncClient pointed at the FastAPI app with a given token."""
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_list_isolation():
    """Org A's loads must not appear in Org B's list response."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Alpha LLC", email="owner-a@alpha.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Beta LLC", email="owner-b@beta.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            # Org A creates a load
            resp = await client_a.post("/api/loads", json=LOAD_BODY_A)
            assert resp.status_code == 201, resp.text
            load_a_id = resp.json()["id"]

            # Org B creates a load
            resp = await client_b.post("/api/loads", json=LOAD_BODY_B)
            assert resp.status_code == 201, resp.text
            load_b_id = resp.json()["id"]

            # Org A lists loads — should see only its own
            resp = await client_a.get("/api/loads")
            assert resp.status_code == 200
            ids_a = [l["id"] for l in resp.json()]
            assert load_a_id in ids_a
            assert load_b_id not in ids_a

            # Org B lists loads — should see only its own
            resp = await client_b.get("/api/loads")
            assert resp.status_code == 200
            ids_b = [l["id"] for l in resp.json()]
            assert load_b_id in ids_b
            assert load_a_id not in ids_b
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_load_get_by_id_isolation():
    """Fetching another org's load by ID must return 404."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Gamma LLC", email="owner-g@gamma.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Delta LLC", email="owner-d@delta.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            # Org A creates a load
            resp = await client_a.post("/api/loads", json=LOAD_BODY_A)
            assert resp.status_code == 201, resp.text
            load_a_id = resp.json()["id"]

            # Org B tries to fetch Org A's load — must get 404
            resp = await client_b.get(f"/api/loads/{load_a_id}")
            assert resp.status_code == 404

            # Org A can still fetch its own load
            resp = await client_a.get(f"/api/loads/{load_a_id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == load_a_id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_load_update_isolation():
    """Patching another org's load by ID must return 404."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Epsilon LLC", email="owner-e@epsilon.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Zeta LLC", email="owner-z@zeta.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            resp = await client_a.post("/api/loads", json=LOAD_BODY_A)
            assert resp.status_code == 201, resp.text
            load_a_id = resp.json()["id"]

            # Org B tries to update Org A's load
            resp = await client_b.patch(
                f"/api/loads/{load_a_id}", json={"commodity": "Hacked!"}
            )
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_driver_list_isolation():
    """Org A's drivers must not appear in Org B's list response."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Eta LLC", email="owner-h@eta.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Theta LLC", email="owner-t@theta.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            # Org A creates a driver
            resp = await client_a.post("/api/drivers", json=DRIVER_BODY_A)
            assert resp.status_code == 201, resp.text
            driver_a_id = resp.json()["id"]

            # Org B creates a driver
            resp = await client_b.post("/api/drivers", json=DRIVER_BODY_B)
            assert resp.status_code == 201, resp.text
            driver_b_id = resp.json()["id"]

            # Org A lists drivers — should see only its own
            resp = await client_a.get("/api/drivers")
            assert resp.status_code == 200
            ids_a = [d["id"] for d in resp.json()]
            assert driver_a_id in ids_a
            assert driver_b_id not in ids_a

            # Org B lists drivers — should see only its own
            resp = await client_b.get("/api/drivers")
            assert resp.status_code == 200
            ids_b = [d["id"] for d in resp.json()]
            assert driver_b_id in ids_b
            assert driver_a_id not in ids_b
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_driver_get_by_id_isolation():
    """Fetching another org's driver by ID must return 404."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Iota LLC", email="owner-i@iota.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Kappa LLC", email="owner-k@kappa.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            resp = await client_a.post("/api/drivers", json=DRIVER_BODY_A)
            assert resp.status_code == 201, resp.text
            driver_a_id = resp.json()["id"]

            # Org B tries to fetch Org A's driver — must get 404
            resp = await client_b.get(f"/api/drivers/{driver_a_id}")
            assert resp.status_code == 404

            # Org A can still fetch its own driver
            resp = await client_a.get(f"/api/drivers/{driver_a_id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == driver_a_id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_driver_update_isolation():
    """Patching another org's driver by ID must return 404."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token_a = await _create_org_user_token(
                db, legal_name="Carrier Lambda LLC", email="owner-l@lambda.test"
            )
            _, _, token_b = await _create_org_user_token(
                db, legal_name="Carrier Mu LLC", email="owner-m@mu.test"
            )

        client_a = await _make_client(token_a)
        client_b = await _make_client(token_b)

        async with client_a, client_b:
            resp = await client_a.post("/api/drivers", json=DRIVER_BODY_A)
            assert resp.status_code == 201, resp.text
            driver_a_id = resp.json()["id"]

            # Org B tries to update Org A's driver
            resp = await client_b.patch(
                f"/api/drivers/{driver_a_id}",
                json={"first_name": "Hacked"},
            )
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_nonexistent_id_returns_404_not_500():
    """Requesting a totally bogus UUID should also return 404, not crash."""
    async def override_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with TestSession() as db:
            _, _, token = await _create_org_user_token(
                db, legal_name="Carrier Nu LLC", email="owner-n@nu.test"
            )

        client = await _make_client(token)
        async with client:
            bogus = str(uuid.uuid4())
            resp = await client.get(f"/api/loads/{bogus}")
            assert resp.status_code == 404

            resp = await client.get(f"/api/drivers/{bogus}")
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
