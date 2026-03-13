"""Tests for compliance data entry routes: maintenance, inspections, fuel, ELD."""

import pytest
from httpx import AsyncClient


async def _create_vehicle(client: AsyncClient) -> str:
    resp = await client.post("/api/vehicles", json={"unit_number": "T-001", "make": "Peterbilt"})
    return resp.json()["id"]


async def _create_driver(client: AsyncClient) -> str:
    resp = await client.post("/api/drivers", json={"first_name": "Jane", "last_name": "Smith"})
    return resp.json()["id"]


# ── Maintenance ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_maintenance_item(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    resp = await client.post(
        "/api/compliance/maintenance",
        json={
            "vehicle_id": vehicle_id,
            "category": "oil_change",
            "due_date": "2026-06-01",
            "notes": "5W-30 synthetic",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "oil_change"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_maintenance_items(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    await client.post(
        "/api/compliance/maintenance",
        json={
            "vehicle_id": vehicle_id,
            "category": "tires",
        },
    )
    resp = await client.get(f"/api/compliance/maintenance?vehicle_id={vehicle_id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_maintenance_status(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    create = await client.post(
        "/api/compliance/maintenance",
        json={
            "vehicle_id": vehicle_id,
            "category": "brake_inspection",
        },
    )
    item_id = create.json()["id"]

    resp = await client.patch(f"/api/compliance/maintenance/{item_id}", json={"status": "overdue"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "overdue"


# ── Annual inspections ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_annual_inspection(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    resp = await client.post(
        "/api/compliance/annual-inspections",
        json={
            "vehicle_id": vehicle_id,
            "inspected_at": "2026-01-15",
            "inspector_name": "Bob's Truck Shop",
            "expires_at": "2027-01-15",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["inspector_name"] == "Bob's Truck Shop"
    assert data["expires_at"] == "2027-01-15"


@pytest.mark.asyncio
async def test_list_annual_inspections(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    await client.post(
        "/api/compliance/annual-inspections",
        json={
            "vehicle_id": vehicle_id,
            "inspected_at": "2026-01-15",
        },
    )
    resp = await client.get(f"/api/compliance/annual-inspections?vehicle_id={vehicle_id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Roadside inspections ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_roadside_inspection(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    resp = await client.post(
        "/api/compliance/roadside-inspections",
        json={
            "vehicle_id": vehicle_id,
            "inspected_at": "2026-03-01",
            "corrections_certified_at": "2026-03-05",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["corrections_certified_at"] == "2026-03-05"


# ── Fuel purchases ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_fuel_purchase(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    resp = await client.post(
        "/api/fuel/purchases",
        json={
            "vehicle_id": vehicle_id,
            "purchased_at_local": "2026-03-10T14:30:00Z",
            "seller_name": "Pilot Flying J #142",
            "jurisdiction": "OH",
            "fuel_type": "diesel",
            "gallons": "150.450",
            "unit_price": "3.899",
            "total_price": "586.71",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["seller_name"] == "Pilot Flying J #142"
    assert data["jurisdiction"] == "OH"


@pytest.mark.asyncio
async def test_list_fuel_purchases(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    await client.post(
        "/api/fuel/purchases",
        json={
            "vehicle_id": vehicle_id,
            "purchased_at_local": "2026-03-10T14:30:00Z",
            "seller_name": "TA #22",
            "gallons": "120.0",
        },
    )
    resp = await client.get(f"/api/fuel/purchases?vehicle_id={vehicle_id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── ELD days ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_eld_day(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    driver_id = await _create_driver(client)
    resp = await client.post(
        "/api/eld/days",
        json={
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "date_local": "2026-03-10",
            "eld_vendor": "Samsara",
            "file_storage_key": "eld/2026/03/10/driver123.csv",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["eld_vendor"] == "Samsara"
    assert data["date_local"] == "2026-03-10"


@pytest.mark.asyncio
async def test_list_eld_days(client: AsyncClient):
    vehicle_id = await _create_vehicle(client)
    driver_id = await _create_driver(client)
    await client.post(
        "/api/eld/days",
        json={
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "date_local": "2026-03-10",
            "file_storage_key": "eld/2026/03/10/driver.csv",
        },
    )
    resp = await client.get(f"/api/eld/days?driver_id={driver_id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
