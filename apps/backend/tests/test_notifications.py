"""Tests for notification routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_overdue_ar_summary_no_overdue(client: AsyncClient):
    """When no overdue receivables exist, returns sent=False."""
    resp = await client.post("/api/notifications/slack/overdue-ar-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] is False
    assert data["reason"] == "no_overdue_receivables"


@pytest.mark.asyncio
async def test_compliance_check_empty_fleet(client: AsyncClient):
    """When no vehicles exist, returns alerts_sent=0."""
    resp = await client.post("/api/notifications/slack/compliance-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts_sent"] == 0


@pytest.mark.asyncio
async def test_compliance_check_with_vehicle(client: AsyncClient):
    """With a vehicle but no inspections, returns alerts_sent=0 (no expiry to check)."""
    await client.post("/api/vehicles", json={"unit_number": "T-100", "make": "Kenworth"})
    resp = await client.post("/api/notifications/slack/compliance-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts_sent"] == 0
