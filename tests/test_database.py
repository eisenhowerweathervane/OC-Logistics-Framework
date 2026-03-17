"""Tests for database.py — init, migration, and seed data."""

import sqlite3

from tests.conftest import TEST_DB_PATH
from database import get_db, init_db, seed_defaults

EXPECTED_TABLES = sorted([
    "loads", "email_log", "lane_history", "broker_history",
    "load_feedback", "accessorials", "cost_config", "scorer_config",
    "toll_corridors", "fuel_prices", "city_demand_tiers",
])


# ── TestInitDb ──────────────────────────────────────────────────────────────

class TestInitDb:
    def test_creates_all_tables(self):
        init_db(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            tables = sorted(r["name"] for r in rows)
            for t in EXPECTED_TABLES:
                assert t in tables, f"Missing table: {t}"
            assert len(tables) >= len(EXPECTED_TABLES)

    def test_loads_table_has_new_columns(self):
        init_db(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            info = conn.execute("PRAGMA table_info(loads)").fetchall()
            col_names = [r["name"] for r in info]
            assert "outcome" in col_names
            assert "duplicate_of" in col_names
            assert "source" in col_names

    def test_idempotent_init(self):
        init_db(TEST_DB_PATH)
        init_db(TEST_DB_PATH)  # second call must not raise
        with get_db(TEST_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            tables = sorted(r["name"] for r in rows)
            for t in EXPECTED_TABLES:
                assert t in tables


# ── TestSeedDefaults ────────────────────────────────────────────────────────

class TestSeedDefaults:
    def test_seeds_cost_config(self):
        init_db(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            row = conn.execute("SELECT * FROM cost_config WHERE id=1").fetchone()
            assert row is not None
            assert row["truck_lease_monthly"] == 4000.0
            assert row["fuel_mpg"] == 6.5

    def test_seeds_scorer_config(self):
        init_db(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            row = conn.execute("SELECT * FROM scorer_config WHERE id=1").fetchone()
            assert row is not None
            assert row["financial_weight"] == 0.50

    def test_seeds_toll_corridors(self):
        init_db(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM toll_corridors").fetchone()[0]
            assert count == 7

    def test_seeds_city_demand_tiers(self):
        init_db(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)
        with get_db(TEST_DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM city_demand_tiers").fetchone()[0]
            assert count > 0
            # Verify tier assignment
            atl = conn.execute(
                "SELECT tier FROM city_demand_tiers WHERE city='Atlanta'"
            ).fetchone()
            assert atl is not None
            assert atl["tier"] == 1

    def test_seed_idempotent(self):
        init_db(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)
        seed_defaults(TEST_DB_PATH)  # second call must not raise or duplicate
        with get_db(TEST_DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM toll_corridors").fetchone()[0]
            assert count == 7
            cc_count = conn.execute("SELECT COUNT(*) FROM cost_config").fetchone()[0]
            assert cc_count == 1
