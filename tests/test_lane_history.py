"""Tests for lane history analytics rebuild."""

import os
from datetime import datetime, timezone, timedelta

import pytest

from tests.conftest import TEST_DB_PATH
from database import init_db, get_db
from analytics.lane_history import rebuild_lane_history


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


class TestRebuildLaneHistory:
    def test_rebuild_empty_db(self):
        """Rebuilding with no loads should produce no lane_history rows."""
        rebuild_lane_history(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute("SELECT * FROM lane_history").fetchall()
        assert len(rows) == 0

    def test_rebuild_with_loads(self):
        """Insert 3 loads for the same lane, rebuild, verify lane_history row."""
        now = datetime.now(timezone.utc)
        with get_db(TEST_DB_PATH) as conn:
            for i in range(3):
                created = (now - timedelta(days=i * 10)).isoformat()
                conn.execute(
                    """INSERT INTO loads
                       (origin_city, origin_state, destination_city, destination_state,
                        rate_total, margin_pct, mileage, outcome, created_at, pickup_date, broker_name)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("Cleveland", "OH", "Columbus", "OH",
                     400 + i * 50, 20.0 + i, 140 + i * 10,
                     "booked" if i == 0 else None,
                     created, f"2026-03-{20 + i}", f"Broker{i}"),
                )
            conn.commit()

        rebuild_lane_history(TEST_DB_PATH)

        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute("SELECT * FROM lane_history").fetchall()

        assert len(rows) == 1
        row = dict(rows[0])
        assert row["origin_city"] == "Cleveland"
        assert row["origin_state"] == "OH"
        assert row["destination_city"] == "Columbus"
        assert row["destination_state"] == "OH"
        assert row["load_count"] == 3
        assert row["booked_count"] == 1
        assert row["avg_rate"] > 0
        assert row["avg_margin_pct"] > 0
        assert row["trend_direction"] in ("up", "down", "stable")
        assert row["last_seen"] is not None
