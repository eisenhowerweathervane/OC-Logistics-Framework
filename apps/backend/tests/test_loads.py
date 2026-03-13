"""Tests for /api/loads routes."""

import pytest
from httpx import AsyncClient

LOAD_BODY = {
    "commodity": "Auto Parts",
    "rate_total": "1850.00",
    "rate_type": "flat",
    "miles_loaded": "485",
    "miles_deadhead_est": "20",
    "stops": [
        {
            "seq": 1,
            "stop_type": "pickup",
            "facility_name": "ABC Distribution",
            "city": "Akron",
            "state": "OH",
        },
        {
            "seq": 2,
            "stop_type": "delivery",
            "facility_name": "Receiver B",
            "city": "Chicago",
            "state": "IL",
        },
    ],
}


@pytest.mark.asyncio
async def test_create_load(client: AsyncClient):
    resp = await client.post("/api/loads", json=LOAD_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "quoted"
    assert data["commodity"] == "Auto Parts"
    assert len(data["stops"]) == 2
    return data


@pytest.mark.asyncio
async def test_list_loads(client: AsyncClient):
    await client.post("/api/loads", json=LOAD_BODY)
    resp = await client.get("/api/loads")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_load(client: AsyncClient):
    create = await client.post("/api/loads", json=LOAD_BODY)
    load_id = create.json()["id"]

    resp = await client.get(f"/api/loads/{load_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == load_id


@pytest.mark.asyncio
async def test_get_load_not_found(client: AsyncClient):
    import uuid

    resp = await client.get(f"/api/loads/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_load(client: AsyncClient):
    create = await client.post("/api/loads", json=LOAD_BODY)
    load_id = create.json()["id"]

    resp = await client.patch(f"/api/loads/{load_id}", json={"commodity": "Steel Coils"})
    assert resp.status_code == 200
    assert resp.json()["commodity"] == "Steel Coils"


@pytest.mark.asyncio
async def test_status_event_valid_transition(client: AsyncClient):
    create = await client.post("/api/loads", json=LOAD_BODY)
    load_id = create.json()["id"]

    resp = await client.post(
        f"/api/loads/{load_id}/status-events",
        json={
            "status": "booked",
            "occurred_at": "2026-09-03T08:00:00Z",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "booked"


@pytest.mark.asyncio
async def test_status_event_invalid_transition(client: AsyncClient):
    create = await client.post("/api/loads", json=LOAD_BODY)
    load_id = create.json()["id"]

    # Can't jump from quoted to delivered
    resp = await client.post(
        f"/api/loads/{load_id}/status-events",
        json={
            "status": "delivered",
            "occurred_at": "2026-09-03T08:00:00Z",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_status_event_full_lifecycle(client: AsyncClient):
    """Walk a load through the full happy path."""
    create = await client.post("/api/loads", json=LOAD_BODY)
    load_id = create.json()["id"]

    transitions = [
        "booked",
        "dispatched",
        "arrived_pickup",
        "loaded",
        "in_transit",
        "arrived_delivery",
        "delivered",
    ]
    for new_status in transitions:
        resp = await client.post(
            f"/api/loads/{load_id}/status-events",
            json={
                "status": new_status,
                "occurred_at": "2026-09-03T09:00:00Z",
            },
        )
        assert resp.status_code == 201, f"Failed at {new_status}: {resp.json()}"

    final = await client.get(f"/api/loads/{load_id}")
    assert final.json()["status"] == "delivered"


@pytest.mark.asyncio
async def test_filter_loads_by_status(client: AsyncClient):
    await client.post("/api/loads", json=LOAD_BODY)

    resp = await client.get("/api/loads?status=quoted")
    assert resp.status_code == 200
    for load in resp.json():
        assert load["status"] == "quoted"
