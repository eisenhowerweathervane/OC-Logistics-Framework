"""Tests for cost/scorer config API endpoints."""

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


# ── TestCostConfigEndpoints ───────────────────────────────────────────────

class TestCostConfigEndpoints:
    def test_get_cost_config(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.get("/api/config/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["truck_lease_monthly"] == 4000.0
        assert data["insurance_monthly"] == 1800.0
        assert data["overhead_monthly"] == 500.0
        assert data["driver_per_mile"] == 0.55
        assert data["fuel_mpg"] == 6.5
        assert data["default_fuel_price"] == 3.85
        assert data["factoring_fee_pct"] == 3.0

    def test_update_cost_config(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            # Partial update
            resp = client.put(
                "/api/config/costs",
                json={"truck_lease_monthly": 5000.0, "fuel_mpg": 7.0},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["truck_lease_monthly"] == 5000.0
        assert data["fuel_mpg"] == 7.0
        # Unchanged fields should retain defaults
        assert data["insurance_monthly"] == 1800.0

        # Verify persistence via GET
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp2 = client.get("/api/config/costs")
        assert resp2.json()["truck_lease_monthly"] == 5000.0
        assert resp2.json()["fuel_mpg"] == 7.0


# ── TestScorerConfigEndpoints ─────────────────────────────────────────────

class TestScorerConfigEndpoints:
    def test_get_scorer_config(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.get("/api/config/scorer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["financial_weight"] == 0.50
        assert data["lane_weight"] == 0.15
        assert data["broker_weight"] == 0.15
        assert data["strategic_weight"] == 0.20

    def test_update_scorer_config(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.put(
                "/api/config/scorer",
                json={
                    "financial_weight": 0.40,
                    "lane_weight": 0.20,
                    "broker_weight": 0.20,
                    "strategic_weight": 0.20,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["financial_weight"] == 0.40
        assert data["lane_weight"] == 0.20

        # Verify persistence
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp2 = client.get("/api/config/scorer")
        assert resp2.json()["financial_weight"] == 0.40

    def test_reject_weights_not_summing_to_one(self):
        with patch("app.DATABASE_PATH", TEST_DB_PATH):
            resp = client.put(
                "/api/config/scorer",
                json={
                    "financial_weight": 0.90,
                    "lane_weight": 0.10,
                    "broker_weight": 0.10,
                    "strategic_weight": 0.10,
                },
            )
        assert resp.status_code == 422
