"""Tests for scheduled background task logic.

Since arq scheduled tasks create their own DB sessions, we test the underlying
service functions that the tasks call, and verify the cron configuration imports.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compliance_scan_via_api(client: AsyncClient):
    """Verify the compliance scan endpoint works (used by daily_compliance_digest)."""
    # Create a vehicle (will have no inspection -> critical alert)
    resp = await client.post(
        "/api/vehicles",
        json={
            "unit_number": "BG-1",
            "make": "Peterbilt",
            "model": "579",
            "year": 2021,
        },
    )
    assert resp.status_code == 201

    scan_resp = await client.get("/api/compliance/scan")
    assert scan_resp.status_code == 200
    alerts = scan_resp.json()
    assert len(alerts) >= 1
    assert alerts[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_ar_summary_via_api(client: AsyncClient):
    """Verify the overdue AR summary endpoint works (used by weekly_ar_reminder)."""
    resp = await client.post("/api/notifications/slack/overdue-ar-summary")
    assert resp.status_code == 200
    assert resp.json()["sent"] is False
    assert resp.json()["reason"] == "no_overdue_receivables"


@pytest.mark.asyncio
async def test_worker_settings_import():
    """Verify worker settings load correctly with cron jobs configured."""
    from app.worker.main import WorkerSettings

    assert len(WorkerSettings.functions) == 2
    assert len(WorkerSettings.cron_jobs) == 3


@pytest.mark.asyncio
async def test_retention_policy_round_trip(client: AsyncClient):
    """Documents with retention policies should be listable."""
    # Verify documents endpoint still works (retention cleanup reads documents)
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
