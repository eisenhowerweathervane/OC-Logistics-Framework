"""Tests for analytics and reporting endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_empty(client: AsyncClient):
    """Dashboard with no data returns zero metrics."""
    resp = await client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_loads"] == 0
    assert data["delivered_this_month"] == 0
    assert data["revenue_this_month"] == 0
    assert data["active_drivers"] == 0
    assert data["active_vehicles"] == 0
    assert data["outstanding_ar"] == 0
    assert data["overdue_ar"] == 0


@pytest.mark.asyncio
async def test_dashboard_with_load(client: AsyncClient):
    """Dashboard reflects active loads."""
    await client.post(
        "/api/loads",
        json={
            "rate_total": 2500,
            "stops": [{"seq": 1, "stop_type": "pickup", "city": "Dallas", "state": "TX"}],
        },
    )
    # Advance to booked (not closed/archived/quoted)
    loads_resp = await client.get("/api/loads")
    load_id = loads_resp.json()[0]["id"]
    await client.post(
        f"/api/loads/{load_id}/status-events",
        json={
            "status": "booked",
            "occurred_at": "2026-03-12T12:00:00Z",
        },
    )

    resp = await client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    assert resp.json()["active_loads"] >= 1


@pytest.mark.asyncio
async def test_revenue_report_empty(client: AsyncClient):
    resp = await client.get("/api/analytics/revenue")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_revenue_report_weekly(client: AsyncClient):
    resp = await client.get("/api/analytics/revenue?period=weekly&months_back=1")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_fleet_utilization_empty(client: AsyncClient):
    resp = await client.get("/api/analytics/fleet-utilization")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_fleet_utilization_with_driver(client: AsyncClient):
    await client.post(
        "/api/drivers",
        json={
            "first_name": "Bob",
            "last_name": "Driver",
        },
    )
    resp = await client.get("/api/analytics/fleet-utilization")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["driver_name"] == "Bob Driver"
    assert data[0]["completed_loads"] == 0


@pytest.mark.asyncio
async def test_fuel_costs_empty(client: AsyncClient):
    resp = await client.get("/api/analytics/fuel-costs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["purchases"] == 0
    assert data["total_gallons"] == 0
    assert data["total_cost"] == 0


@pytest.mark.asyncio
async def test_fuel_costs_with_purchases(client: AsyncClient):
    vehicle_resp = await client.post(
        "/api/vehicles",
        json={
            "unit_number": "A-1",
            "make": "Kenworth",
            "model": "T680",
            "year": 2023,
        },
    )
    vehicle_id = vehicle_resp.json()["id"]

    await client.post(
        "/api/fuel/purchases",
        json={
            "vehicle_id": vehicle_id,
            "purchased_at_local": "2026-03-10T14:00:00",
            "seller_name": "Love's",
            "gallons": 120.5,
            "total_price": 450.00,
        },
    )

    resp = await client.get("/api/analytics/fuel-costs?months_back=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["purchases"] == 1
    assert data["total_gallons"] == 120.5
    assert data["total_cost"] == 450.0
