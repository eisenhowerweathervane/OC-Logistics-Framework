"""Tests for the chain optimizer with full HOS and repositioning value."""

import os
import pytest
from unittest.mock import patch, MagicMock

from optimizer.hos_model import HOSState
from optimizer.chain_optimizer import optimize_chain

TEST_DB_PATH = "/tmp/profitability_test.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_load(origin_city, origin_state, dest_city, dest_state, rate, mileage=200):
    """Create a minimal load dict for testing."""
    return {
        "origin_city": origin_city,
        "origin_state": origin_state,
        "destination_city": dest_city,
        "destination_state": dest_state,
        "rate_total": rate,
        "mileage": mileage,
    }


# We mock get_drive_info so tests don't depend on Google Maps or Haversine coords.
# We also mock score_load and score_strategic to keep tests deterministic.

def _fake_drive_info(origin, destination, avg_speed=52.0):
    """Return deterministic drive info based on city pairs."""
    if origin == destination:
        return {"distance_miles": 0, "drive_time_hours": 0, "source": "mock"}

    # Use a lookup of known pairs; default to short trip
    routes = {
        # Cleveland -> Columbus: ~140 mi, 2.5 hrs
        ("Cleveland, OH", "Columbus, OH"): (140, 2.5),
        ("Columbus, OH", "Cleveland, OH"): (140, 2.5),
        # Columbus -> Pittsburgh: ~185 mi, 3.2 hrs
        ("Columbus, OH", "Pittsburgh, PA"): (185, 3.2),
        ("Pittsburgh, PA", "Columbus, OH"): (185, 3.2),
        # Pittsburgh -> Cleveland: ~133 mi, 2.3 hrs
        ("Pittsburgh, PA", "Cleveland, OH"): (133, 2.3),
        ("Cleveland, OH", "Pittsburgh, PA"): (133, 2.3),
        # Cleveland -> Cincinnati: ~250 mi, 4.3 hrs
        ("Cleveland, OH", "Cincinnati, OH"): (250, 4.3),
        ("Cincinnati, OH", "Cleveland, OH"): (250, 4.3),
        # Cincinnati -> Columbus: ~110 mi, 1.8 hrs
        ("Cincinnati, OH", "Columbus, OH"): (110, 1.8),
        ("Columbus, OH", "Cincinnati, OH"): (110, 1.8),
        # Cleveland -> Detroit: ~170 mi, 2.8 hrs
        ("Cleveland, OH", "Detroit, MI"): (170, 2.8),
        ("Detroit, MI", "Cleveland, OH"): (170, 2.8),
        # Detroit -> Toledo: ~60 mi, 1.0 hrs
        ("Detroit, MI", "Toledo, OH"): (60, 1.0),
        ("Toledo, OH", "Detroit, MI"): (60, 1.0),
        # Toledo -> Cleveland: ~117 mi, 2.0 hrs
        ("Toledo, OH", "Cleveland, OH"): (117, 2.0),
        ("Cleveland, OH", "Toledo, OH"): (117, 2.0),
        # Cleveland -> Akron: ~40 mi, 0.7 hrs
        ("Cleveland, OH", "Akron, OH"): (40, 0.7),
        ("Akron, OH", "Cleveland, OH"): (40, 0.7),
        # Akron -> Canton (approx): ~25 mi, 0.5 hrs
        ("Akron, OH", "Canton, OH"): (25, 0.5),
        ("Canton, OH", "Akron, OH"): (25, 0.5),
        ("Canton, OH", "Cleveland, OH"): (60, 1.0),
        ("Cleveland, OH", "Canton, OH"): (60, 1.0),
        # Columbus -> Indianapolis: ~175 mi, 3.0 hrs
        ("Columbus, OH", "Indianapolis, IN"): (175, 3.0),
        ("Indianapolis, IN", "Columbus, OH"): (175, 3.0),
        ("Indianapolis, IN", "Cleveland, OH"): (310, 5.3),
        ("Cleveland, OH", "Indianapolis, IN"): (310, 5.3),
        # Short hops for multi-load day test
        ("Cleveland, OH", "Akron, OH"): (40, 0.7),
        ("Akron, OH", "Canton, OH"): (25, 0.5),
        ("Canton, OH", "Akron, OH"): (25, 0.5),
        ("Akron, OH", "Youngstown, OH"): (60, 1.0),
        ("Youngstown, OH", "Cleveland, OH"): (75, 1.3),
        ("Cleveland, OH", "Youngstown, OH"): (75, 1.3),
        ("Youngstown, OH", "Akron, OH"): (60, 1.0),
        ("Canton, OH", "Youngstown, OH"): (50, 0.9),
    }

    key = (origin, destination)
    if key in routes:
        miles, hours = routes[key]
        return {"distance_miles": miles, "drive_time_hours": hours, "source": "mock"}

    # Default: 100 miles, 1.8 hours
    return {"distance_miles": 100, "drive_time_hours": 1.8, "source": "mock"}


def _fake_score_load(load, deadhead_miles=None, detention_hours=0.0,
                     assumptions=None, current_city=None):
    """Return a deterministic scored load dict."""
    rate = load.get("rate_total") or 0
    miles = load.get("mileage") or 200
    # Simple cost model
    cost_per_mile = 1.50
    dh_miles = deadhead_miles if deadhead_miles is not None else 0
    total_miles = miles + dh_miles
    total_cost = total_miles * cost_per_mile
    net_revenue = rate * 0.97  # 3% factoring
    profit = net_revenue - total_cost

    origin = f"{load.get('origin_city', '')}, {load.get('origin_state', '')}"
    dest = f"{load.get('destination_city', '')}, {load.get('destination_state', '')}"

    dh_info = _fake_drive_info(current_city or "Cleveland, OH", origin)
    loaded_info = _fake_drive_info(origin, dest)

    total_drive = dh_info["drive_time_hours"] + loaded_info["drive_time_hours"]
    total_hours = total_drive + 1.5  # dwell

    return {
        "origin_city": load.get("origin_city", ""),
        "origin_state": load.get("origin_state", ""),
        "destination_city": load.get("destination_city", ""),
        "destination_state": load.get("destination_state", ""),
        "rate_total": rate,
        "mileage": miles,
        "deadhead_miles": round(dh_miles, 1),
        "deadhead_drive_time": round(dh_info["drive_time_hours"], 2),
        "loaded_drive_time": round(loaded_info["drive_time_hours"], 2),
        "total_miles": round(total_miles, 1),
        "total_cost": round(total_cost, 2),
        "net_revenue": round(net_revenue, 2),
        "profit": round(profit, 2),
        "margin_pct": round((profit / net_revenue) * 100, 2) if net_revenue > 0 else 0,
        "rpm": round(rate / miles, 2) if miles > 0 else 0,
        "all_in_rpm": round(net_revenue / total_miles, 2) if total_miles > 0 else 0,
        "drive_hours": round(total_drive, 2),
        "dwell_time": 1.5,
        "total_hours": round(total_hours, 2),
        "profit_per_hour": round(profit / total_hours, 2) if total_hours > 0 else 0,
        "score": 5,
        "action": "BOOK IT",
        "floor_rpm": 1.80,
        "warnings": [],
    }


def _fake_score_strategic(dest_city, dest_state, home_base="Cleveland, OH",
                          db_path=None):
    """Return a deterministic strategic score."""
    from scoring.strategic_scorer import StrategicScore
    return StrategicScore(
        score=0.5,
        destination_tier=2,
        home_distance_factor=0.0,
        detail={},
    )


@pytest.fixture(autouse=True)
def _patch_externals():
    """Patch external dependencies for all tests."""
    with patch("optimizer.chain_optimizer.get_drive_info", side_effect=_fake_drive_info), \
         patch("optimizer.chain_optimizer.score_load", side_effect=_fake_score_load), \
         patch("optimizer.chain_optimizer.score_strategic", side_effect=_fake_score_strategic):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmptyLoads:
    def test_empty_loads_returns_empty(self):
        result = optimize_chain([], start_city="Cleveland, OH", db_path=TEST_DB_PATH)
        assert result["legs"] == []
        assert result["summary"]["total_profit"] == 0
        assert result["summary"]["num_loads"] == 0


class TestSingleLoad:
    def test_single_load_chain(self):
        loads = [_make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185)]
        result = optimize_chain(loads, start_city="Cleveland, OH", db_path=TEST_DB_PATH)

        # Should have at least 1 real leg + return home
        real_legs = [l for l in result["legs"] if not l.get("is_return_home")]
        return_legs = [l for l in result["legs"] if l.get("is_return_home")]

        assert len(real_legs) == 1
        assert len(return_legs) == 1
        assert result["summary"]["num_loads"] == 1

    def test_return_home_included(self):
        loads = [_make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185)]
        result = optimize_chain(loads, start_city="Cleveland, OH", db_path=TEST_DB_PATH)

        last_leg = result["legs"][-1]
        assert last_leg["is_return_home"] is True


class TestHOSCompliance:
    def test_respects_hos_drive_limit(self):
        """Loads that would exceed 11hr drive limit should be skipped."""
        # This load requires Cleveland->Indianapolis deadhead (~5.3hrs)
        # plus Indianapolis->... loaded, which together will be very long.
        # With a nearly-exhausted HOS, it should be skipped.
        hos = HOSState(drive_hours_remaining=3.0, duty_hours_remaining=4.0)
        loads = [
            # Cleveland -> Cincinnati deadhead (~4.3 hrs drive) exceeds 3hr remaining
            _make_load("Cincinnati", "OH", "Indianapolis", "IN", 800, 175),
        ]
        result = optimize_chain(
            loads,
            start_city="Cleveland, OH",
            hos_state=hos,
            db_path=TEST_DB_PATH,
        )
        # Load should be skipped — can't complete within HOS
        assert result["summary"]["num_loads"] == 0


class TestMultiLoadDay:
    def test_multi_load_day(self):
        """Three short loads should chain in one day."""
        loads = [
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),
            _make_load("Canton", "OH", "Youngstown", "OH", 250, 50),
            _make_load("Cleveland", "OH", "Akron", "OH", 180, 40),
        ]
        result = optimize_chain(
            loads,
            start_city="Cleveland, OH",
            db_path=TEST_DB_PATH,
        )
        real_legs = [l for l in result["legs"] if not l.get("is_return_home")]
        # Should pick at least 2 loads (likely all 3 given short distances)
        assert len(real_legs) >= 2
        assert result["summary"]["num_loads"] >= 2
        assert result["summary"]["days"] == 1


class TestPicksProfitableChain:
    def test_picks_profitable_chain(self):
        """Given good and bad loads, picks the better ones."""
        loads = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),  # good
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 200, 185),  # bad - low rate
        ]
        result = optimize_chain(
            loads,
            start_city="Cleveland, OH",
            db_path=TEST_DB_PATH,
        )
        # The optimizer should pick the $600 load, not the $200 one
        real_legs = [l for l in result["legs"] if not l.get("is_return_home")]
        assert len(real_legs) >= 1
        first_leg_rate = real_legs[0]["result"]["rate_total"]
        assert first_leg_rate == 600


class TestMultiDayWithRest:
    def test_multi_day_with_rest(self):
        """max_days=2: first day fills up, rest inserted, second day continues."""
        # Short loads that fit individually but exhaust HOS after first
        # Load 1: Cleveland->Akron DH(0.7) + Akron->Canton loaded(0.5) = 1.2hr drive, +1.5 dwell = 2.7 on-duty
        # After load 1: drive_remaining=2.8, duty_remaining=1.3
        # Load 2: Canton->Youngstown DH(0.9) + ... needs ~1.4hr drive min -> won't fit in duty
        # But after rest it will.
        hos = HOSState(
            drive_hours_remaining=4.0,
            duty_hours_remaining=4.0,
        )
        loads = [
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),     # short
            _make_load("Canton", "OH", "Youngstown", "OH", 250, 50), # short
        ]
        result = optimize_chain(
            loads,
            start_city="Cleveland, OH",
            hos_state=hos,
            home_base="Cleveland, OH",
            max_days=2,
            db_path=TEST_DB_PATH,
        )
        real_legs = [l for l in result["legs"] if not l.get("is_return_home")]
        # With 4hr drive / 4hr duty:
        # Load 1: DH Cleveland->Akron(0.7) + loaded Akron->Canton(0.5) = 1.2hr drive + 1.5 dwell = 2.7 on-duty
        # After: drive=2.8, duty=1.3
        # Load 2: DH Canton->Canton(0) + loaded Canton->Youngstown(0.9) = 0.9hr drive + 1.5 dwell = 2.4 on-duty > 1.3 duty
        # So load 2 doesn't fit day 1. With max_days=2 and rest, it should fit day 2.
        assert len(real_legs) == 2
        assert result["summary"]["days"] == 2
        # Verify days are assigned correctly
        assert real_legs[0]["day"] == 1
        assert real_legs[1]["day"] == 2


class TestReturnFormat:
    def test_summary_keys(self):
        loads = [_make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185)]
        result = optimize_chain(loads, start_city="Cleveland, OH", db_path=TEST_DB_PATH)

        required_keys = [
            "total_profit", "total_revenue", "num_loads", "total_deadhead",
            "deadhead_pct", "total_hours", "total_drive_hours", "avg_margin",
            "profit_per_hour", "total_miles", "hos_state", "days",
        ]
        for key in required_keys:
            assert key in result["summary"], f"Missing summary key: {key}"

    def test_leg_keys(self):
        loads = [_make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185)]
        result = optimize_chain(loads, start_city="Cleveland, OH", db_path=TEST_DB_PATH)

        real_legs = [l for l in result["legs"] if not l.get("is_return_home")]
        assert len(real_legs) > 0
        leg = real_legs[0]
        for key in ["load", "deadhead", "deadhead_time", "loaded_time",
                     "leg_total_time", "result", "is_return_home", "day"]:
            assert key in leg, f"Missing leg key: {key}"
