"""Tests for WhatsApp-related routes: driver phone lookup, dispatch/docs notifications."""

import pytest
from httpx import AsyncClient


async def _create_driver_with_phone(client: AsyncClient, phone: str) -> dict:
    resp = await client.post(
        "/api/drivers",
        json={
            "first_name": "Mike",
            "last_name": "Trucker",
            "phone": phone,
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_driver_by_phone_exact(client: AsyncClient):
    driver = await _create_driver_with_phone(client, "+15551234567")
    resp = await client.get("/api/drivers/by-phone/+15551234567")
    assert resp.status_code == 200
    assert resp.json()["id"] == driver["id"]


@pytest.mark.asyncio
async def test_driver_by_phone_normalized(client: AsyncClient):
    driver = await _create_driver_with_phone(client, "(555) 987-6543")
    resp = await client.get("/api/drivers/by-phone/5559876543")
    assert resp.status_code == 200
    assert resp.json()["id"] == driver["id"]


@pytest.mark.asyncio
async def test_driver_by_phone_not_found(client: AsyncClient):
    resp = await client.get("/api/drivers/by-phone/+10000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dispatch_alert_no_phone(client: AsyncClient):
    """Driver without phone returns sent=False."""
    driver_resp = await client.post(
        "/api/drivers",
        json={
            "first_name": "No",
            "last_name": "Phone",
        },
    )
    driver_id = driver_resp.json()["id"]

    # Create a load
    load_resp = await client.post(
        "/api/loads",
        json={
            "stops": [{"seq": 1, "stop_type": "pickup", "city": "Dallas", "state": "TX"}],
        },
    )
    load_id = load_resp.json()["id"]

    resp = await client.post(
        "/api/notifications/whatsapp/dispatch-alert",
        json={
            "driver_id": driver_id,
            "load_id": load_id,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["sent"] is False
    assert resp.json()["reason"] == "driver_has_no_phone"


@pytest.mark.asyncio
async def test_docs_reminder_driver_not_found(client: AsyncClient):
    """Nonexistent driver returns 404."""
    load_resp = await client.post(
        "/api/loads",
        json={
            "stops": [{"seq": 1, "stop_type": "pickup"}],
        },
    )
    load_id = load_resp.json()["id"]

    resp = await client.post(
        "/api/notifications/whatsapp/docs-reminder",
        json={
            "driver_id": "00000000-0000-0000-0000-000000000000",
            "load_id": load_id,
            "missing_docs": ["bol"],
        },
    )
    assert resp.status_code == 404
