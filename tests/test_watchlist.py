"""Tests for the watchlist model with committed + flexible planning."""

import pytest
from unittest.mock import patch

from optimizer.hos_model import HOSState
from optimizer.watchlist import (
    WatchlistEntry,
    WatchlistPlan,
    build_watchlist,
    resolve_watchlist,
)

TEST_DB_PATH = "/tmp/profitability_test.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_load(origin_city, origin_state, dest_city, dest_state, rate, mileage=200):
    return {
        "origin_city": origin_city,
        "origin_state": origin_state,
        "destination_city": dest_city,
        "destination_state": dest_state,
        "rate_total": rate,
        "mileage": mileage,
    }


def _fake_drive_info(origin, destination, avg_speed=52.0):
    if origin == destination:
        return {"distance_miles": 0, "drive_time_hours": 0, "source": "mock"}

    routes = {
        ("Cleveland, OH", "Columbus, OH"): (140, 2.5),
        ("Columbus, OH", "Cleveland, OH"): (140, 2.5),
        ("Columbus, OH", "Pittsburgh, PA"): (185, 3.2),
        ("Pittsburgh, PA", "Columbus, OH"): (185, 3.2),
        ("Pittsburgh, PA", "Cleveland, OH"): (133, 2.3),
        ("Cleveland, OH", "Pittsburgh, PA"): (133, 2.3),
        ("Cleveland, OH", "Akron, OH"): (40, 0.7),
        ("Akron, OH", "Cleveland, OH"): (40, 0.7),
        ("Akron, OH", "Canton, OH"): (25, 0.5),
        ("Canton, OH", "Akron, OH"): (25, 0.5),
        ("Canton, OH", "Cleveland, OH"): (60, 1.0),
        ("Cleveland, OH", "Canton, OH"): (60, 1.0),
        ("Canton, OH", "Youngstown, OH"): (50, 0.9),
        ("Youngstown, OH", "Cleveland, OH"): (75, 1.3),
        ("Cleveland, OH", "Youngstown, OH"): (75, 1.3),
        ("Columbus, OH", "Akron, OH"): (120, 2.1),
        ("Akron, OH", "Columbus, OH"): (120, 2.1),
        ("Pittsburgh, PA", "Akron, OH"): (100, 1.7),
        ("Akron, OH", "Pittsburgh, PA"): (100, 1.7),
    }

    key = (origin, destination)
    if key in routes:
        miles, hours = routes[key]
        return {"distance_miles": miles, "drive_time_hours": hours, "source": "mock"}

    return {"distance_miles": 100, "drive_time_hours": 1.8, "source": "mock"}


def _fake_score_load(load, deadhead_miles=None, detention_hours=0.0,
                     assumptions=None, current_city=None):
    rate = load.get("rate_total") or 0
    miles = load.get("mileage") or 200
    cost_per_mile = 1.50
    dh_miles = deadhead_miles if deadhead_miles is not None else 0
    total_miles = miles + dh_miles
    total_cost = total_miles * cost_per_mile
    net_revenue = rate * 0.97
    profit = net_revenue - total_cost

    origin = f"{load.get('origin_city', '')}, {load.get('origin_state', '')}"
    dest = f"{load.get('destination_city', '')}, {load.get('destination_state', '')}"

    dh_info = _fake_drive_info(current_city or "Cleveland, OH", origin)
    loaded_info = _fake_drive_info(origin, dest)

    total_drive = dh_info["drive_time_hours"] + loaded_info["drive_time_hours"]
    total_hours = total_drive + 1.5

    return {
        "origin_city": load.get("origin_city", ""),
        "origin_state": load.get("origin_state", ""),
        "destination_city": load.get("destination_city", ""),
        "destination_state": load.get("destination_state", ""),
        "rate_total": rate,
        "mileage": miles,
        "deadhead_miles": round(dh_miles, 1),
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
         patch("optimizer.chain_optimizer.score_strategic", side_effect=_fake_score_strategic), \
         patch("optimizer.watchlist.get_drive_info", side_effect=_fake_drive_info):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildWatchlistNoCommitted:
    def test_build_watchlist_with_no_committed(self):
        """With no committed loads, available loads go on watchlist."""
        available = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),
        ]
        plan = build_watchlist(
            committed_loads=[],
            available_loads=available,
            current_city="Cleveland, OH",
            db_path=TEST_DB_PATH,
        )

        assert isinstance(plan, WatchlistPlan)
        assert plan.committed == []
        # Scenario tree should have all four scenarios
        assert "scenarios" in plan.scenario_tree
        for name in ["quick", "normal", "slow", "detention"]:
            assert name in plan.scenario_tree["scenarios"]


class TestBuildWatchlistWithCommitted:
    def test_build_watchlist_with_committed(self):
        """Committed load should affect position used for watchlist scenarios."""
        committed = [
            _make_load("Cleveland", "OH", "Columbus", "OH", 500, 140),
        ]
        available = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),
        ]
        plan = build_watchlist(
            committed_loads=committed,
            available_loads=available,
            current_city="Cleveland, OH",
            db_path=TEST_DB_PATH,
        )

        assert len(plan.committed) == 1
        # Scenario tree should reflect position after committed load (Columbus, OH)
        assert plan.scenario_tree["current_city"] == "Columbus, OH"


class TestResolveQuickDwell:
    def test_resolve_quick_dwell(self):
        """0.5hr actual dwell should resolve to quick scenario."""
        # Build a scenario tree with known data
        scenario_tree = {
            "scenarios": {
                "quick": {
                    "dwell_hours": 0.5,
                    "recommendations": [{"load": {"id": 1}, "score": 7, "profit": 450}],
                },
                "normal": {
                    "dwell_hours": 1.5,
                    "recommendations": [{"load": {"id": 2}, "score": 6, "profit": 400}],
                },
                "slow": {
                    "dwell_hours": 3.0,
                    "recommendations": [{"load": {"id": 3}, "score": 5, "profit": 350}],
                },
                "detention": {
                    "dwell_hours": 6.0,
                    "recommendations": [],
                },
            },
        }

        recs = resolve_watchlist(0.5, scenario_tree)
        assert len(recs) == 1
        assert recs[0]["load"]["id"] == 1


class TestResolveDetentionDwell:
    def test_resolve_detention_dwell(self):
        """7hr actual dwell should resolve to detention scenario."""
        scenario_tree = {
            "scenarios": {
                "quick": {
                    "dwell_hours": 0.5,
                    "recommendations": [{"load": {"id": 1}, "score": 7, "profit": 450}],
                },
                "normal": {
                    "dwell_hours": 1.5,
                    "recommendations": [{"load": {"id": 2}, "score": 6, "profit": 400}],
                },
                "slow": {
                    "dwell_hours": 3.0,
                    "recommendations": [{"load": {"id": 3}, "score": 5, "profit": 350}],
                },
                "detention": {
                    "dwell_hours": 6.0,
                    "recommendations": [{"load": {"id": 4}, "score": 3, "profit": 200}],
                },
            },
        }

        recs = resolve_watchlist(7.0, scenario_tree)
        assert len(recs) == 1
        assert recs[0]["load"]["id"] == 4


class TestResolveNormalDwell:
    def test_resolve_normal_dwell(self):
        """1.5hr should resolve to normal scenario."""
        scenario_tree = {
            "scenarios": {
                "quick": {"dwell_hours": 0.5, "recommendations": [{"id": "q"}]},
                "normal": {"dwell_hours": 1.5, "recommendations": [{"id": "n"}]},
                "slow": {"dwell_hours": 3.0, "recommendations": [{"id": "s"}]},
                "detention": {"dwell_hours": 6.0, "recommendations": [{"id": "d"}]},
            },
        }
        recs = resolve_watchlist(1.5, scenario_tree)
        assert recs[0]["id"] == "n"

    def test_resolve_slow_dwell(self):
        """3.5hr should resolve to slow scenario."""
        scenario_tree = {
            "scenarios": {
                "quick": {"dwell_hours": 0.5, "recommendations": [{"id": "q"}]},
                "normal": {"dwell_hours": 1.5, "recommendations": [{"id": "n"}]},
                "slow": {"dwell_hours": 3.0, "recommendations": [{"id": "s"}]},
                "detention": {"dwell_hours": 6.0, "recommendations": [{"id": "d"}]},
            },
        }
        recs = resolve_watchlist(3.5, scenario_tree)
        assert recs[0]["id"] == "s"


class TestWatchlistEntriesTrackScenarios:
    def test_watchlist_entries_track_scenarios(self):
        """Entries should list which scenarios they appear in."""
        available = [
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),
        ]
        plan = build_watchlist(
            committed_loads=[],
            available_loads=available,
            current_city="Cleveland, OH",
            db_path=TEST_DB_PATH,
        )

        # If the load appears in any scenarios, it should track them
        for entry in plan.watchlist:
            assert isinstance(entry, WatchlistEntry)
            assert isinstance(entry.scenarios, list)
            # Each scenario name should be one of the known four
            for s in entry.scenarios:
                assert s in ["quick", "normal", "slow", "detention"]
            # Should appear in at least one scenario
            assert len(entry.scenarios) >= 1


class TestWatchlistEntryDataclass:
    def test_watchlist_entry_defaults(self):
        entry = WatchlistEntry(load={"id": 1})
        assert entry.load == {"id": 1}
        assert entry.score is None
        assert entry.profit is None
        assert entry.scenarios == []
        assert entry.pickup_deadline == ""

    def test_watchlist_plan_defaults(self):
        plan = WatchlistPlan()
        assert plan.committed == []
        assert plan.watchlist == []
        assert plan.scenario_tree == {}
