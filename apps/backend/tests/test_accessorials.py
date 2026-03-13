"""Tests for /api/loads/{load_id}/accessorials and /api/accessorials routes."""

import pytest
from httpx import AsyncClient

LOAD_BODY = {
    "commodity": "Test Freight",
    "rate_total": "2000.00",
    "stops": [
        {"seq": 1, "stop_type": "pickup", "city": "Dallas", "state": "TX"},
        {"seq": 2, "stop_type": "delivery", "city": "Memphis", "state": "TN"},
    ],
}


async def _create_load(client: AsyncClient) -> str:
    resp = await client.post("/api/loads", json=LOAD_BODY)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_accessorial(client: AsyncClient):
    load_id = await _create_load(client)
    resp = await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "detention", "amount": "150.00", "description": "2 hours waiting at shipper"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["charge_type"] == "detention"
    assert float(data["amount"]) == 150.00
    assert data["status"] == "pending"
    assert data["load_id"] == load_id


@pytest.mark.asyncio
async def test_list_accessorials(client: AsyncClient):
    load_id = await _create_load(client)
    await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "detention", "amount": "150.00"},
    )
    await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "lumper", "amount": "75.00"},
    )

    resp = await client.get(f"/api/loads/{load_id}/accessorials")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    types = {c["charge_type"] for c in data}
    assert types == {"detention", "lumper"}


@pytest.mark.asyncio
async def test_update_accessorial(client: AsyncClient):
    load_id = await _create_load(client)
    create = await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "tonu", "amount": "300.00"},
    )
    charge_id = create.json()["id"]

    resp = await client.patch(
        f"/api/accessorials/{charge_id}",
        json={"amount": "350.00", "status": "approved"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["amount"]) == 350.00
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_delete_accessorial(client: AsyncClient):
    load_id = await _create_load(client)
    create = await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "toll", "amount": "25.00"},
    )
    charge_id = create.json()["id"]

    resp = await client.delete(f"/api/accessorials/{charge_id}")
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(f"/api/loads/{load_id}/accessorials")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_accessorial_summary(client: AsyncClient):
    load_id = await _create_load(client)
    await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "detention", "amount": "150.00"},
    )
    await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "detention", "amount": "200.00"},
    )
    await client.post(
        f"/api/loads/{load_id}/accessorials",
        json={"charge_type": "lumper", "amount": "75.00"},
    )

    resp = await client.get("/api/accessorials/summary")
    assert resp.status_code == 200
    data = resp.json()
    detention = next(r for r in data if r["charge_type"] == "detention")
    assert detention["count"] == 2
    assert detention["total"] == 350.00


@pytest.mark.asyncio
async def test_accessorial_summary_by_load(client: AsyncClient):
    load1 = await _create_load(client)
    load2 = await _create_load(client)
    await client.post(f"/api/loads/{load1}/accessorials", json={"charge_type": "detention", "amount": "100.00"})
    await client.post(f"/api/loads/{load2}/accessorials", json={"charge_type": "detention", "amount": "200.00"})

    resp = await client.get(f"/api/accessorials/summary?load_id={load1}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["total"] == 100.00


@pytest.mark.asyncio
async def test_accessorial_load_not_found(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/loads/{fake_id}/accessorials",
        json={"charge_type": "detention", "amount": "100.00"},
    )
    assert resp.status_code == 404
