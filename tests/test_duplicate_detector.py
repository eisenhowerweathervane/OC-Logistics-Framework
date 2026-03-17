"""Tests for the duplicate detector module."""

from tests.conftest import TEST_DB_PATH
from database import get_db, init_db
from ingestion.duplicate_detector import DuplicateResult, check_duplicate
from models import ParsedLoad


def _make_load(**overrides) -> ParsedLoad:
    """Create a ParsedLoad with sensible defaults, applying overrides."""
    defaults = dict(
        origin_city="Columbus",
        origin_state="OH",
        destination_city="Atlanta",
        destination_state="GA",
        mileage=550,
        source="email",
        rate_total=1650.00,
        pickup_date="2026-03-16",
        broker_name="TQL",
    )
    defaults.update(overrides)
    return ParsedLoad(**defaults)


def _insert_load(load: ParsedLoad, db_path: str) -> int:
    """Insert a ParsedLoad into the DB and return the row id."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO loads
               (origin_city, origin_state, destination_city, destination_state,
                pickup_date, broker_name, rate_total, mileage, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                load.origin_city,
                load.origin_state,
                load.destination_city,
                load.destination_state,
                load.pickup_date,
                load.broker_name,
                load.rate_total,
                load.mileage,
                load.source,
            ),
        )
        conn.commit()
        return cur.lastrowid


class TestDuplicateDetector:
    def test_exact_duplicate_detected(self):
        init_db(TEST_DB_PATH)
        load = _make_load()
        row_id = _insert_load(load, TEST_DB_PATH)

        result = check_duplicate(load, db_path=TEST_DB_PATH)

        assert result.is_duplicate is True
        assert result.matching_load_id == row_id
        assert f"Load #{row_id}" in result.message

    def test_different_rate_not_duplicate(self):
        init_db(TEST_DB_PATH)
        load = _make_load()
        _insert_load(load, TEST_DB_PATH)

        different_rate = _make_load(rate_total=2000.00)
        result = check_duplicate(different_rate, db_path=TEST_DB_PATH)

        assert result.is_duplicate is False
        assert result.matching_load_id is None

    def test_different_route_not_duplicate(self):
        init_db(TEST_DB_PATH)
        load = _make_load()
        _insert_load(load, TEST_DB_PATH)

        different_route = _make_load(origin_city="Chicago", origin_state="IL")
        result = check_duplicate(different_route, db_path=TEST_DB_PATH)

        assert result.is_duplicate is False
        assert result.matching_load_id is None

    def test_no_loads_in_db(self):
        init_db(TEST_DB_PATH)

        load = _make_load()
        result = check_duplicate(load, db_path=TEST_DB_PATH)

        assert result.is_duplicate is False
        assert result.matching_load_id is None
