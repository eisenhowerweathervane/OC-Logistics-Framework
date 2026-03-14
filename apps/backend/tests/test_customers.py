"""Tests for customer CRUD routes."""

import uuid

import pytest
from httpx import AsyncClient

CUSTOMER_BODY = {
    "company_name": "Acme Shipping Co",
    "contact_name": "Jane Smith",
    "contact_email": "jane@acmeshipping.com",
    "contact_phone": "555-0200",
    "city": "Columbus",
    "state": "OH",
    "credit_terms_days": 30,
    "preferred_lanes": "OH to PA, OH to MI",
}


@pytest.mark.asyncio
async def test_create_customer(client: AsyncClient):
    resp = await client.post("/api/customers", json=CUSTOMER_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_name"] == "Acme Shipping Co"
    assert data["contact_name"] == "Jane Smith"
    assert data["status"] == "active"
    assert data["credit_terms_days"] == 30


@pytest.mark.asyncio
async def test_list_customers(client: AsyncClient):
    await client.post("/api/customers", json=CUSTOMER_BODY)
    resp = await client.get("/api/customers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_customers_filter_status(client: AsyncClient):
    await client.post("/api/customers", json=CUSTOMER_BODY)
    resp = await client.get("/api/customers?customer_status=active")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    resp2 = await client.get("/api/customers?customer_status=inactive")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 0


@pytest.mark.asyncio
async def test_get_customer(client: AsyncClient):
    create = await client.post("/api/customers", json=CUSTOMER_BODY)
    customer_id = create.json()["id"]

    resp = await client.get(f"/api/customers/{customer_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == customer_id
    assert resp.json()["preferred_lanes"] == "OH to PA, OH to MI"


@pytest.mark.asyncio
async def test_update_customer(client: AsyncClient):
    create = await client.post("/api/customers", json=CUSTOMER_BODY)
    customer_id = create.json()["id"]

    resp = await client.patch(
        f"/api/customers/{customer_id}",
        json={"status": "inactive", "credit_terms_days": 45},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"
    assert resp.json()["credit_terms_days"] == 45


@pytest.mark.asyncio
async def test_customer_not_found(client: AsyncClient):
    resp = await client.get(f"/api/customers/{uuid.uuid4()}")
    assert resp.status_code == 404
