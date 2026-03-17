"""Tests for paste ingestion, gap resolution, and duplicate detection API endpoints."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_DB_PATH
from database import init_db, seed_defaults

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


SAMPLE_PASTE = (
    "Cleveland, OH -> Columbus, OH\n"
    "140 mi\n"
    "Rate: $420.00\n"
    "Van\n"
    "42,000 lbs\n"
    "Pickup: 03/20/2026\n"
    "Company: Test Broker LLC\n"
    "MC# 123456\n"
    "214-555-1234\n"
    "broker@example.com"
)


# ── TestPasteEndpoint ────────────────────────────────────────────────────

class TestPasteEndpoint:
    def test_parse_paste_returns_loads(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post("/api/ingest/paste", json={"text": SAMPLE_PASTE})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["loads"]) == 1
        load = data["loads"][0]
        assert load["origin_city"] == "Cleveland"
        assert load["origin_state"] == "OH"
        assert load["destination_city"] == "Columbus"
        assert load["destination_state"] == "OH"
        assert load["rate_total"] == 420.0
        assert load["mileage"] == 140
        # Gap and duplicate info should be present
        assert "gaps" in load
        assert "duplicate" in load
        assert load["duplicate"]["is_duplicate"] is False
        assert isinstance(data["gaps"], list)
        assert isinstance(data["duplicates"], int)

    def test_parse_paste_empty_text(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post("/api/ingest/paste", json={"text": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["loads"] == []
        assert data["gaps"] == []
        assert data["duplicates"] == 0


# ── TestCompleteEndpoint ─────────────────────────────────────────────────

class TestCompleteEndpoint:
    def test_complete_and_save_load(self):
        load_data = {
            "origin_city": "Cleveland",
            "origin_state": "OH",
            "destination_city": "Columbus",
            "destination_state": "OH",
            "mileage": 140,
            "rate_total": 420.0,
            "deadhead_miles": 0,
            "equipment_type": "Van",
            "commodity": "",
            "pickup_date": "2026-03-20",
            "pickup_time_window": "",
            "delivery_date": "",
            "delivery_time_window": "",
            "broker_name": "Test Broker",
            "broker_mc_number": "",
            "contact_phone": "",
            "contact_email": "",
            "load_number": "",
            "notes": "",
        }
        fills = {"weight": 42000, "source": "paste"}

        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post(
                "/api/ingest/complete",
                json={"load": load_data, "fills": fills, "save": True},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert data["id"] is not None
        assert "scored" in data
        assert data["scored"]["origin_city"] == "Cleveland"


# ── TestDuplicateEndpoint ────────────────────────────────────────────────

class TestDuplicateEndpoint:
    def test_duplicate_flagged(self):
        """Insert a load directly into the DB, then paste the same load → duplicate detected.

        We insert directly to ensure the mileage stored in the DB exactly matches
        what the paste parser produces (score_load may recalculate mileage via
        the distance service, causing a mismatch).
        """
        from database import get_db

        # Insert a load that matches SAMPLE_PASTE fields exactly
        with get_db(TEST_DB_PATH) as conn:
            conn.execute("""
                INSERT INTO loads (
                    origin_city, origin_state, destination_city, destination_state,
                    mileage, rate_total, broker_name, pickup_date,
                    equipment_type, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Cleveland", "OH", "Columbus", "OH",
                140, 420.0, "Test Broker LLC", "2026-03-20",
                "Van", "paste",
            ))
            conn.commit()

        # Now paste the same load — should detect duplicate
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.post("/api/ingest/paste", json={"text": SAMPLE_PASTE})
        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicates"] >= 1
        assert data["loads"][0]["duplicate"]["is_duplicate"] is True
