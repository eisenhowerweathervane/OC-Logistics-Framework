"""Tests for load scoring, lane profitability, and broker ratings."""
import pytest
from httpx import AsyncClient


async def _create_load_with_stops(
    client: AsyncClient,
    rate: float = 2500,
    miles: float = 800,
    deadhead: float = 50,
    origin_state: str = "TX",
    dest_state: str = "OK",
) -> dict:
    resp = await client.post("/api/loads", json={
        "rate_total": rate,
        "miles_loaded": miles,
        "miles_deadhead_est": deadhead,
        "stops": [
            {"seq": 1, "stop_type": "pickup", "city": "Dallas", "state": origin_state},
            {"seq": 2, "stop_type": "delivery", "city": "OKC", "state": dest_state},
        ],
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_score_load(client: AsyncClient):
    load = await _create_load_with_stops(client, rate=2500, miles=800, deadhead=50)
    resp = await client.get(f"/api/scoring/loads/{load['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_per_mile"] == 3.12  # 2500/800
    assert data["grade"] == "A"
    assert data["origin"] == "Dallas, TX"
    assert data["destination"] == "OKC, OK"


@pytest.mark.asyncio
async def test_score_load_low_rpm(client: AsyncClient):
    load = await _create_load_with_stops(client, rate=1000, miles=800)
    resp = await client.get(f"/api/scoring/loads/{load['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rate_per_mile"] == 1.25
    assert data["grade"] == "F"


@pytest.mark.asyncio
async def test_score_load_not_found(client: AsyncClient):
    resp = await client.get("/api/scoring/loads/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lane_profitability_empty(client: AsyncClient):
    resp = await client.get("/api/scoring/lanes")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_lane_profitability_with_delivered_loads(client: AsyncClient):
    """Only delivered+ loads count for lane analysis."""
    load = await _create_load_with_stops(client, rate=3000, miles=1000, origin_state="TX", dest_state="IL")

    # Load is in "quoted" status — shouldn't appear in lanes
    resp = await client.get("/api/scoring/lanes")
    assert resp.json() == []

    # Advance to delivered
    for next_status in ["booked", "dispatched", "arrived_pickup", "loaded", "in_transit", "arrived_delivery", "delivered"]:
        await client.post(
            f"/api/loads/{load['id']}/status-events",
            json={"status": next_status, "occurred_at": "2026-03-12T12:00:00Z"},
        )

    resp = await client.get("/api/scoring/lanes")
    assert resp.status_code == 200
    lanes = resp.json()
    assert len(lanes) == 1
    assert lanes[0]["lane"] == "TX→IL"
    assert lanes[0]["avg_rate_per_mile"] == 3.0


@pytest.mark.asyncio
async def test_broker_ratings_empty(client: AsyncClient):
    resp = await client.get("/api/scoring/brokers")
    assert resp.status_code == 200
    assert resp.json() == []
