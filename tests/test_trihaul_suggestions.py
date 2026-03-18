"""Tests for the trihaul city suggestions module."""

import os
import pytest
from unittest.mock import patch

from database import init_db, seed_defaults, get_db
from optimizer.trihaul_suggestions import suggest_trihaul_cities, TrihaulSuggestion

TEST_DB_PATH = "/tmp/profitability_test_trihaul.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_db():
    """Initialize and seed a fresh test database."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    seed_defaults(TEST_DB_PATH)


def _fake_drive_info(origin, destination, avg_speed=52.0):
    """Deterministic drive info for known city pairs."""
    if origin == destination:
        return {"distance_miles": 0, "drive_time_hours": 0, "source": "mock"}

    routes = {
        ("Pittsburgh, PA", "Cleveland, OH"): (133, 2.3),
        ("Cleveland, OH", "Pittsburgh, PA"): (133, 2.3),
        ("Pittsburgh, PA", "Columbus, OH"): (185, 3.2),
        ("Columbus, OH", "Pittsburgh, PA"): (185, 3.2),
        ("Pittsburgh, PA", "Indianapolis, IN"): (360, 6.2),
        ("Indianapolis, IN", "Pittsburgh, PA"): (360, 6.2),
        ("Indianapolis, IN", "Cleveland, OH"): (310, 5.3),
        ("Pittsburgh, PA", "Detroit, MI"): (290, 5.0),
        ("Detroit, MI", "Cleveland, OH"): (170, 2.8),
        ("Pittsburgh, PA", "Cincinnati, OH"): (290, 5.0),
        ("Cincinnati, OH", "Cleveland, OH"): (250, 4.3),
        ("Pittsburgh, PA", "Buffalo, NY"): (200, 3.5),
        ("Buffalo, NY", "Cleveland, OH"): (190, 3.3),
        ("Pittsburgh, PA", "Nashville, TN"): (530, 9.1),
        ("Nashville, TN", "Cleveland, OH"): (530, 9.1),
        ("Pittsburgh, PA", "Chicago, IL"): (460, 7.9),
        ("Chicago, IL", "Cleveland, OH"): (345, 5.9),
        ("Pittsburgh, PA", "Louisville, KY"): (410, 7.0),
        ("Louisville, KY", "Cleveland, OH"): (350, 6.0),
        ("Pittsburgh, PA", "Philadelphia, PA"): (305, 5.2),
        ("Philadelphia, PA", "Cleveland, OH"): (430, 7.4),
        ("Pittsburgh, PA", "Atlanta, GA"): (680, 11.7),
        ("Atlanta, GA", "Cleveland, OH"): (720, 12.4),
        ("Pittsburgh, PA", "Charlotte, NC"): (460, 7.9),
        ("Charlotte, NC", "Cleveland, OH"): (530, 9.1),
        ("Pittsburgh, PA", "Memphis, TN"): (660, 11.3),
        ("Memphis, TN", "Cleveland, OH"): (660, 11.3),
        ("Pittsburgh, PA", "Jacksonville, FL"): (800, 13.8),
        ("Jacksonville, FL", "Cleveland, OH"): (830, 14.3),
        ("Pittsburgh, PA", "Raleigh, NC"): (400, 6.9),
        ("Raleigh, NC", "Cleveland, OH"): (480, 8.3),
        ("Pittsburgh, PA", "Baltimore, MD"): (250, 4.3),
        ("Baltimore, MD", "Cleveland, OH"): (370, 6.4),
        ("Pittsburgh, PA", "St. Louis, MO"): (600, 10.3),
        ("St. Louis, MO", "Cleveland, OH"): (540, 9.3),
        ("Pittsburgh, PA", "Kansas City, MO"): (780, 13.4),
        ("Kansas City, MO", "Cleveland, OH"): (780, 13.4),
        ("Pittsburgh, PA", "Milwaukee, WI"): (500, 8.6),
        ("Milwaukee, WI", "Cleveland, OH"): (420, 7.2),
        ("Pittsburgh, PA", "Minneapolis, MN"): (830, 14.3),
        ("Minneapolis, MN", "Cleveland, OH"): (760, 13.1),
        ("Pittsburgh, PA", "Denver, CO"): (1400, 24.1),
        ("Denver, CO", "Cleveland, OH"): (1350, 23.3),
        ("Pittsburgh, PA", "New Orleans, LA"): (930, 16.0),
        ("New Orleans, LA", "Cleveland, OH"): (930, 16.0),
        ("Pittsburgh, PA", "Birmingham, AL"): (600, 10.3),
        ("Birmingham, AL", "Cleveland, OH"): (620, 10.7),
        ("Pittsburgh, PA", "Knoxville, TN"): (400, 6.9),
        ("Knoxville, TN", "Cleveland, OH"): (440, 7.6),
        ("Pittsburgh, PA", "Grand Rapids, MI"): (400, 6.9),
        ("Grand Rapids, MI", "Cleveland, OH"): (290, 5.0),
        ("Pittsburgh, PA", "Tampa, FL"): (960, 16.6),
        ("Tampa, FL", "Cleveland, OH"): (1000, 17.2),
        ("Pittsburgh, PA", "Erie, PA"): (130, 2.2),
        ("Erie, PA", "Cleveland, OH"): (100, 1.7),
        ("Pittsburgh, PA", "Toledo, OH"): (250, 4.3),
        ("Toledo, OH", "Cleveland, OH"): (117, 2.0),
        ("Pittsburgh, PA", "Akron, OH"): (115, 2.0),
        ("Akron, OH", "Cleveland, OH"): (40, 0.7),
        ("Pittsburgh, PA", "Dayton, OH"): (260, 4.5),
        ("Dayton, OH", "Cleveland, OH"): (230, 4.0),
        ("Pittsburgh, PA", "Fort Wayne, IN"): (340, 5.9),
        ("Fort Wayne, IN", "Cleveland, OH"): (280, 4.8),
        ("Pittsburgh, PA", "Lexington, KY"): (380, 6.5),
        ("Lexington, KY", "Cleveland, OH"): (330, 5.7),
        ("Pittsburgh, PA", "Mobile, AL"): (810, 13.9),
        ("Mobile, AL", "Cleveland, OH"): (830, 14.3),
        ("Pittsburgh, PA", "Little Rock, AR"): (750, 12.9),
        ("Little Rock, AR", "Cleveland, OH"): (750, 12.9),
        ("Pittsburgh, PA", "Oklahoma City, OK"): (1050, 18.1),
        ("Oklahoma City, OK", "Cleveland, OH"): (1050, 18.1),
        ("Pittsburgh, PA", "Houston, TX"): (1250, 21.6),
        ("Houston, TX", "Cleveland, OH"): (1270, 21.9),
        ("Pittsburgh, PA", "Dallas, TX"): (1170, 20.2),
        ("Dallas, TX", "Cleveland, OH"): (1190, 20.5),
    }

    key = (origin, destination)
    if key in routes:
        miles, hours = routes[key]
        return {"distance_miles": miles, "drive_time_hours": hours, "source": "mock"}

    # Default
    return {"distance_miles": 500, "drive_time_hours": 8.6, "source": "mock"}


@pytest.fixture(autouse=True)
def _patch_drive_info():
    """Patch get_drive_info for all tests."""
    with patch(
        "optimizer.trihaul_suggestions.get_drive_info",
        side_effect=_fake_drive_info,
    ):
        yield


@pytest.fixture(autouse=True)
def _cleanup_db():
    """Clean up test database."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReturnsSuggestions:
    def test_returns_suggestions(self):
        """From Pittsburgh with Cleveland home, should get suggestions."""
        _setup_db()
        results = suggest_trihaul_cities(
            current_city="Pittsburgh",
            current_state="PA",
            home_city="Cleveland",
            home_state="OH",
            db_path=TEST_DB_PATH,
        )
        assert len(results) > 0
        assert all(isinstance(r, TrihaulSuggestion) for r in results)


class TestExcludesCurrentAndHome:
    def test_excludes_current_and_home(self):
        """Current city and home city should not appear in results."""
        _setup_db()
        results = suggest_trihaul_cities(
            current_city="Pittsburgh",
            current_state="PA",
            home_city="Cleveland",
            home_state="OH",
            db_path=TEST_DB_PATH,
            max_results=50,
            min_distance_mi=0,
        )
        cities = [(r.city, r.state) for r in results]
        assert ("Pittsburgh", "PA") not in cities
        assert ("Cleveland", "OH") not in cities


class TestRespectsDistanceLimits:
    def test_respects_distance_limits(self):
        """No suggestions outside min/max range."""
        _setup_db()
        results = suggest_trihaul_cities(
            current_city="Pittsburgh",
            current_state="PA",
            home_city="Cleveland",
            home_state="OH",
            db_path=TEST_DB_PATH,
            min_distance_mi=200,
            max_distance_mi=400,
            max_results=50,
        )
        for r in results:
            assert r.distance_from_current >= 200, (
                f"{r.city}, {r.state} is {r.distance_from_current} mi away, "
                f"below min 200"
            )
            assert r.distance_from_current <= 400, (
                f"{r.city}, {r.state} is {r.distance_from_current} mi away, "
                f"above max 400"
            )


class TestEmptyDbStillWorks:
    def test_empty_db_still_works(self):
        """Uses demand tiers even without lane history."""
        _setup_db()
        # Don't add any lane history - just rely on demand tiers
        results = suggest_trihaul_cities(
            current_city="Pittsburgh",
            current_state="PA",
            home_city="Cleveland",
            home_state="OH",
            db_path=TEST_DB_PATH,
        )
        # Should still return results from demand tiers alone
        assert len(results) > 0
        # All avg_rate fields should be None since no lane history
        for r in results:
            assert r.avg_rate_to_city is None
            assert r.avg_rate_to_home is None


class TestMaxResultsRespected:
    def test_max_results_respected(self):
        """Returns at most max_results."""
        _setup_db()
        results = suggest_trihaul_cities(
            current_city="Pittsburgh",
            current_state="PA",
            home_city="Cleveland",
            home_state="OH",
            db_path=TEST_DB_PATH,
            max_results=3,
            min_distance_mi=0,
        )
        assert len(results) <= 3
