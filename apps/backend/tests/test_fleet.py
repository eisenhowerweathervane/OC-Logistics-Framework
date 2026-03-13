"""Tests for fleet CRUD routes: drivers, vehicles, trailers, brokers."""
import pytest
from httpx import AsyncClient


# ── Drivers ───────────────────────────────────────────────────────────────────

DRIVER_BODY = {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "555-0100",
    "license_state": "OH",
    "pay_type": "per_mile",
    "pay_rate": "0.55",
}


@pytest.mark.asyncio
async def test_create_driver(client: AsyncClient):
    resp = await client.post("/api/drivers", json=DRIVER_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_drivers(client: AsyncClient):
    await client.post("/api/drivers", json=DRIVER_BODY)
    resp = await client.get("/api/drivers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_driver(client: AsyncClient):
    create = await client.post("/api/drivers", json=DRIVER_BODY)
    driver_id = create.json()["id"]

    resp = await client.get(f"/api/drivers/{driver_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == driver_id


@pytest.mark.asyncio
async def test_update_driver(client: AsyncClient):
    create = await client.post("/api/drivers", json=DRIVER_BODY)
    driver_id = create.json()["id"]

    resp = await client.patch(f"/api/drivers/{driver_id}", json={"status": "inactive"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"


@pytest.mark.asyncio
async def test_driver_not_found(client: AsyncClient):
    import uuid
    resp = await client.get(f"/api/drivers/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Vehicles ──────────────────────────────────────────────────────────────────

VEHICLE_BODY = {
    "unit_number": "T-101",
    "make": "Kenworth",
    "model": "T680",
    "year": 2022,
    "plate_state": "OH",
    "plate_number": "ABC1234",
}


@pytest.mark.asyncio
async def test_create_vehicle(client: AsyncClient):
    resp = await client.post("/api/vehicles", json=VEHICLE_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["unit_number"] == "T-101"
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_list_vehicles(client: AsyncClient):
    await client.post("/api/vehicles", json=VEHICLE_BODY)
    resp = await client.get("/api/vehicles")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_vehicle(client: AsyncClient):
    create = await client.post("/api/vehicles", json=VEHICLE_BODY)
    vehicle_id = create.json()["id"]

    resp = await client.patch(f"/api/vehicles/{vehicle_id}", json={"status": "out_of_service"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "out_of_service"


# ── Trailers ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trailer(client: AsyncClient):
    resp = await client.post("/api/trailers", json={"trailer_number": "TR-55", "trailer_type": "reefer"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["trailer_number"] == "TR-55"
    assert data["trailer_type"] == "reefer"


@pytest.mark.asyncio
async def test_list_trailers(client: AsyncClient):
    await client.post("/api/trailers", json={"trailer_number": "TR-99"})
    resp = await client.get("/api/trailers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Brokers ───────────────────────────────────────────────────────────────────

BROKER_BODY = {
    "legal_name": "Acme Brokerage LLC",
    "billing_email": "billing@acme.com",
    "payment_terms_days": 30,
}


@pytest.mark.asyncio
async def test_create_broker(client: AsyncClient):
    resp = await client.post("/api/brokers", json=BROKER_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["legal_name"] == "Acme Brokerage LLC"
    assert data["payment_terms_days"] == 30


@pytest.mark.asyncio
async def test_list_brokers(client: AsyncClient):
    await client.post("/api/brokers", json=BROKER_BODY)
    resp = await client.get("/api/brokers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_broker(client: AsyncClient):
    create = await client.post("/api/brokers", json=BROKER_BODY)
    broker_id = create.json()["id"]

    resp = await client.get(f"/api/brokers/{broker_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == broker_id


@pytest.mark.asyncio
async def test_update_broker(client: AsyncClient):
    create = await client.post("/api/brokers", json=BROKER_BODY)
    broker_id = create.json()["id"]

    resp = await client.patch(f"/api/brokers/{broker_id}", json={"payment_terms_days": 45})
    assert resp.status_code == 200
    assert resp.json()["payment_terms_days"] == 45
