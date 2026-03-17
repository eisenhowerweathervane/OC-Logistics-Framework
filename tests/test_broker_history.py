"""Tests for broker history analytics rebuild."""

import os
from datetime import datetime, timezone

import pytest

from tests.conftest import TEST_DB_PATH
from database import init_db, get_db
from analytics.broker_history import rebuild_broker_history


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


class TestRebuildBrokerHistory:
    def test_rebuild_no_feedback(self):
        """Brokers with no feedback should get grade U."""
        with get_db(TEST_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO loads
                   (origin_city, origin_state, destination_city, destination_state,
                    rate_total, mileage, broker_name, pickup_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("Cleveland", "OH", "Columbus", "OH", 400, 140,
                 "No Feedback Broker", "2026-03-20"),
            )
            conn.commit()

        rebuild_broker_history(TEST_DB_PATH)

        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT * FROM broker_history WHERE broker_name = ?",
                ("No Feedback Broker",),
            ).fetchall()

        assert len(rows) == 1
        row = dict(rows[0])
        assert row["reliability_grade"] == "U"
        assert row["loads_seen"] == 1

    def test_rebuild_with_feedback(self):
        """Insert loads + feedback, verify grade is calculated."""
        with get_db(TEST_DB_PATH) as conn:
            # Insert a load
            cursor = conn.execute(
                """INSERT INTO loads
                   (origin_city, origin_state, destination_city, destination_state,
                    rate_total, mileage, broker_name, outcome, pickup_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("Cleveland", "OH", "Columbus", "OH", 400, 140,
                 "Good Broker", "booked", "2026-03-20"),
            )
            load_id = cursor.lastrowid

            # Insert feedback — good broker metrics
            conn.execute(
                """INSERT INTO load_feedback
                   (load_id, detention_hours, actual_rate_paid, ontime_pickup)
                   VALUES (?, ?, ?, ?)""",
                (load_id, 0.5, 400.0, True),
            )
            conn.commit()

        rebuild_broker_history(TEST_DB_PATH)

        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT * FROM broker_history WHERE broker_name = ?",
                ("Good Broker",),
            ).fetchall()

        assert len(rows) == 1
        row = dict(rows[0])
        # detention < 1, ontime 100%, tonu 0 → grade A
        assert row["reliability_grade"] == "A"
        assert row["loads_completed"] == 1
        assert row["loads_seen"] == 1
        assert row["avg_detention_hours"] == 0.5
        assert row["ontime_pickup_pct"] == 100.0
