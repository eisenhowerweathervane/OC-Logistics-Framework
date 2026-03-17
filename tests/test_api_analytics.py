"""Tests for feedback, outcome, analytics, watchlist, and optimizer API endpoints."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_DB_PATH
from database import init_db, seed_defaults, get_db

# Patch DATABASE_PATH before importing app so all get_db calls use the test DB
with patch("app.DATABASE_PATH", TEST_DB_PATH):
    from app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize and seed a fresh test database for each test."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    seed_defaults(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def _insert_test_load(
    origin_city="Cleveland",
    origin_state="OH",
    dest_city="Columbus",
    dest_state="OH",
    rate=400.0,
    mileage=140,
    broker="Test Broker",
    pickup_date="2026-03-20",
    outcome=None,
):
    """Helper to insert a test load directly into the DB."""
    with get_db(TEST_DB_PATH) as conn:
        cursor = conn.execute(
            """INSERT INTO loads
               (origin_city, origin_state, destination_city, destination_state,
                rate_total, mileage, broker_name, pickup_date, outcome, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (origin_city, origin_state, dest_city, dest_state,
             rate, mileage, broker, pickup_date, outcome, "test"),
        )
        conn.commit()
        return cursor.lastrowid


# ── TestPostFeedback ─────────────────────────────────────────────────────

class TestPostFeedback:
    def test_post_feedback(self):
        load_id = _insert_test_load()
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post(
                f"/api/loads/{load_id}/feedback",
                json={
                    "actual_dwell_hours": 1.5,
                    "actual_rate_paid": 400.0,
                    "actual_toll_cost": 12.50,
                    "detention_hours": 0.5,
                    "ontime_pickup": True,
                    "issues": "",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["load_id"] == load_id
        assert data["actual_dwell_hours"] == 1.5
        assert data["detention_hours"] == 0.5

    def test_post_feedback_not_found(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post(
                "/api/loads/99999/feedback",
                json={"detention_hours": 0.5, "ontime_pickup": True},
            )
        assert resp.status_code == 404


# ── TestPatchOutcome ─────────────────────────────────────────────────────

class TestPatchOutcome:
    def test_patch_outcome(self):
        load_id = _insert_test_load()
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.patch(
                f"/api/loads/{load_id}/outcome",
                json={"outcome": "booked"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome"] == "booked"

        # Verify persisted
        with get_db(TEST_DB_PATH) as conn:
            row = conn.execute(
                "SELECT outcome FROM loads WHERE id = ?", (load_id,)
            ).fetchone()
        assert row["outcome"] == "booked"

    def test_patch_outcome_invalid(self):
        load_id = _insert_test_load()
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.patch(
                f"/api/loads/{load_id}/outcome",
                json={"outcome": "invalid_value"},
            )
        assert resp.status_code == 400

    def test_patch_outcome_not_found(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.patch(
                "/api/loads/99999/outcome",
                json={"outcome": "booked"},
            )
        assert resp.status_code == 404


# ── TestGetLanes ─────────────────────────────────────────────────────────

class TestGetLanes:
    def test_get_lanes_empty(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.get("/api/analytics/lanes")
        assert resp.status_code == 200
        assert resp.json() == []


# ── TestGetBrokers ───────────────────────────────────────────────────────

class TestGetBrokers:
    def test_get_brokers_empty(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.get("/api/analytics/brokers")
        assert resp.status_code == 200
        assert resp.json() == []


# ── TestDemandTiers ──────────────────────────────────────────────────────

class TestDemandTiers:
    def test_get_demand_tiers(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.get("/api/config/demand-tiers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify seeded data is present
        cities = {r["city"] for r in data}
        assert "Atlanta" in cities

    def test_update_demand_tiers(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.put(
                "/api/config/demand-tiers",
                json=[{"city": "Zanesville", "state": "OH", "tier": 4}],
            )
        assert resp.status_code == 200
        data = resp.json()
        zanesville = [r for r in data if r["city"] == "Zanesville"]
        assert len(zanesville) == 1
        assert zanesville[0]["tier"] == 4
        assert zanesville[0]["state"] == "OH"
