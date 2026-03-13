"""Tests for IFTA returns, IRP registration, and fleet compliance scanning."""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient


async def _create_vehicle(client: AsyncClient) -> dict:
    resp = await client.post("/api/vehicles", json={
        "unit_number": "T-100",
        "make": "Freightliner",
        "model": "Cascadia",
        "year": 2022,
    })
    assert resp.status_code == 201
    return resp.json()


async def _create_driver(client: AsyncClient) -> dict:
    resp = await client.post("/api/drivers", json={
        "first_name": "John",
        "last_name": "Smith",
    })
    assert resp.status_code == 201
    return resp.json()


# ── IFTA ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ifta_calculate_empty(client: AsyncClient):
    """Calculate IFTA return with no fuel or load data yields empty jurisdictions."""
    resp = await client.post("/api/compliance/ifta/calculate", json={
        "year": 2026, "quarter": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2026
    assert data["quarter"] == 1
    assert data["status"] == "draft"
    assert data["fuel_by_jurisdiction"] == []
    assert data["distance_by_jurisdiction"] == []


@pytest.mark.asyncio
async def test_ifta_calculate_with_fuel(client: AsyncClient):
    """Fuel purchases aggregate by jurisdiction in IFTA return."""
    vehicle = await _create_vehicle(client)

    # Add fuel purchases in TX and OK
    for jur, gallons in [("TX", 150.0), ("TX", 100.0), ("OK", 75.0)]:
        await client.post("/api/fuel/purchases", json={
            "vehicle_id": vehicle["id"],
            "purchased_at_local": "2026-02-15T10:00:00",
            "seller_name": "Pilot",
            "jurisdiction": jur,
            "gallons": gallons,
        })

    resp = await client.post("/api/compliance/ifta/calculate", json={
        "year": 2026, "quarter": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    fuel = {f["jurisdiction"]: f for f in data["fuel_by_jurisdiction"]}
    assert "TX" in fuel
    assert "OK" in fuel
    assert float(fuel["TX"]["gallons"]) == 250.0
    assert float(fuel["OK"]["gallons"]) == 75.0


@pytest.mark.asyncio
async def test_ifta_invalid_quarter(client: AsyncClient):
    resp = await client.post("/api/compliance/ifta/calculate", json={
        "year": 2026, "quarter": 5,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ifta_list(client: AsyncClient):
    """Create an IFTA return then list it."""
    await client.post("/api/compliance/ifta/calculate", json={
        "year": 2025, "quarter": 4,
    })
    resp = await client.get("/api/compliance/ifta")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["year"] == 2025
    assert data[0]["quarter"] == 4


@pytest.mark.asyncio
async def test_ifta_file(client: AsyncClient):
    """File an IFTA return, then verify recalculate is blocked."""
    calc_resp = await client.post("/api/compliance/ifta/calculate", json={
        "year": 2025, "quarter": 3,
    })
    ifta_id = calc_resp.json()["id"]

    file_resp = await client.post(f"/api/compliance/ifta/{ifta_id}/file")
    assert file_resp.status_code == 200
    assert file_resp.json()["status"] == "filed"

    # Recalculate should return the filed return without changes
    recalc_resp = await client.post("/api/compliance/ifta/calculate", json={
        "year": 2025, "quarter": 3,
    })
    assert recalc_resp.status_code == 200
    assert recalc_resp.json()["status"] == "filed"


# ── IRP ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_irp_create_and_list(client: AsyncClient):
    resp = await client.post("/api/compliance/irp", json={
        "registration_year": 2026,
    })
    assert resp.status_code == 201
    assert resp.json()["registration_year"] == 2026

    list_resp = await client.get("/api/compliance/irp")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


# ── Fleet compliance scan ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compliance_scan_no_inspection(client: AsyncClient):
    """Vehicle with no annual inspection should trigger critical alert."""
    await _create_vehicle(client)

    resp = await client.get("/api/compliance/scan")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["alert_type"] == "no_annual_inspection" for a in alerts)


@pytest.mark.asyncio
async def test_compliance_scan_expired_inspection(client: AsyncClient):
    """Vehicle with expired annual inspection should trigger critical alert."""
    vehicle = await _create_vehicle(client)

    past_date = (date.today() - timedelta(days=60)).isoformat()
    expired_date = (date.today() - timedelta(days=10)).isoformat()
    await client.post("/api/compliance/annual-inspections", json={
        "vehicle_id": vehicle["id"],
        "inspected_at": past_date,
        "expires_at": expired_date,
    })

    resp = await client.get("/api/compliance/scan")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["alert_type"] == "annual_inspection_expired" for a in alerts)


@pytest.mark.asyncio
async def test_compliance_scan_clean(client: AsyncClient):
    """Vehicle with valid inspection and no overdue maintenance returns no critical alerts."""
    vehicle = await _create_vehicle(client)

    future_date = (date.today() + timedelta(days=200)).isoformat()
    await client.post("/api/compliance/annual-inspections", json={
        "vehicle_id": vehicle["id"],
        "inspected_at": date.today().isoformat(),
        "expires_at": future_date,
    })

    resp = await client.get("/api/compliance/scan")
    assert resp.status_code == 200
    alerts = resp.json()
    critical = [a for a in alerts if a["severity"] == "critical"]
    assert len(critical) == 0


@pytest.mark.asyncio
async def test_compliance_scan_overdue_maintenance(client: AsyncClient):
    """Vehicle with overdue maintenance should trigger warning alert."""
    vehicle = await _create_vehicle(client)

    # Add valid inspection so we don't get a no_inspection alert
    future_date = (date.today() + timedelta(days=200)).isoformat()
    await client.post("/api/compliance/annual-inspections", json={
        "vehicle_id": vehicle["id"],
        "inspected_at": date.today().isoformat(),
        "expires_at": future_date,
    })

    past_date = (date.today() - timedelta(days=5)).isoformat()
    await client.post("/api/compliance/maintenance", json={
        "vehicle_id": vehicle["id"],
        "category": "Oil Change",
        "due_date": past_date,
    })

    resp = await client.get("/api/compliance/scan")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["alert_type"] == "overdue_maintenance" for a in alerts)
