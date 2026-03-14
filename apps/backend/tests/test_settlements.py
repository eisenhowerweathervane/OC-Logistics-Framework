"""Tests for /api/settlements routes."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fleet import Driver, Vehicle
from app.db.models.loads import Assignment, Load


async def _seed_delivered_load(
    db: AsyncSession,
    org_id: uuid.UUID,
    pay_type: str = "per_mile",
    pay_rate: float = 0.60,
) -> tuple[str, str]:
    """Create a driver, vehicle, delivered load, and assignment directly in DB.

    Returns (driver_id, load_id) as strings.
    """
    now = datetime.now(timezone.utc)

    driver = Driver(
        organization_id=org_id,
        first_name="John",
        last_name="Doe",
        pay_type=pay_type,
        pay_rate=pay_rate,
        status="active",
    )
    db.add(driver)

    vehicle = Vehicle(organization_id=org_id, unit_number="T-100", status="available")
    db.add(vehicle)

    load = Load(
        organization_id=org_id,
        commodity="Test Freight",
        rate_total=2000.00,
        miles_loaded=500,
        status="delivered",
    )
    db.add(load)
    await db.flush()

    assignment = Assignment(
        load_id=load.id,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        assigned_at=now,
        created_at=now,
    )
    db.add(assignment)
    await db.commit()

    return str(driver.id), str(load.id)


@pytest.mark.asyncio
async def test_generate_settlement(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    resp = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["driver_id"] == driver_id
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["line_type"] == "load_pay"
    # per_mile: 0.60 * 500 miles = 300.00
    assert float(data["net_pay"]) == 300.00


@pytest.mark.asyncio
async def test_generate_settlement_percentage(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id, pay_type="percentage", pay_rate=25)

    resp = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    assert resp.status_code == 201
    # percentage: 25% of $2000 = $500
    assert float(resp.json()["net_pay"]) == 500.00


@pytest.mark.asyncio
async def test_list_settlements(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2025-06-30"},
    )
    await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2025-07-01", "period_end": "2030-12-31"},
    )

    resp = await client.get("/api/settlements")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_settlement(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    gen = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    sid = gen.json()["id"]

    resp = await client.get(f"/api/settlements/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid
    assert len(resp.json()["line_items"]) >= 1


@pytest.mark.asyncio
async def test_approve_settlement(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    gen = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    sid = gen.json()["id"]

    resp = await client.post(f"/api/settlements/{sid}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approved_by"] is not None


@pytest.mark.asyncio
async def test_pay_settlement(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    gen = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    sid = gen.json()["id"]

    await client.post(f"/api/settlements/{sid}/approve")

    resp = await client.post(f"/api/settlements/{sid}/pay")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"
    assert resp.json()["paid_at"] is not None


@pytest.mark.asyncio
async def test_pay_requires_approval(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    gen = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    sid = gen.json()["id"]

    resp = await client.post(f"/api/settlements/{sid}/pay")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_deduction_line(client: AsyncClient, seeded_db, db: AsyncSession):
    org, _, _ = seeded_db
    driver_id, _ = await _seed_delivered_load(db, org.id)

    gen = await client.post(
        "/api/settlements/generate",
        json={"driver_id": driver_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    sid = gen.json()["id"]
    original_net = float(gen.json()["net_pay"])

    resp = await client.post(
        f"/api/settlements/{sid}/lines",
        json={"line_type": "fuel_advance", "amount": "50.00", "description": "Fuel advance 3/10"},
    )
    assert resp.status_code == 201
    assert resp.json()["line_type"] == "fuel_advance"

    # Verify net_pay decreased
    detail = await client.get(f"/api/settlements/{sid}")
    assert float(detail.json()["net_pay"]) == original_net - 50.00


@pytest.mark.asyncio
async def test_driver_not_found(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        "/api/settlements/generate",
        json={"driver_id": fake_id, "period_start": "2020-01-01", "period_end": "2030-12-31"},
    )
    assert resp.status_code == 404
