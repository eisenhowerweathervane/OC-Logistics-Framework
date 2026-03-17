"""Tests for the scenario engine with dwell-time branches."""

import pytest
from unittest.mock import patch, MagicMock

from optimizer.hos_model import HOSState
from optimizer.scenario_engine import generate_scenarios

TEST_DB_PATH = "/tmp/profitability_test.db"


# ---------------------------------------------------------------------------
# Helpers — reuse the mock patterns from test_chain_optimizer
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


def _fake_drive_info(origin, destination, avg_speed=52.0):
    """Return deterministic drive info based on city pairs."""
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
        ("Youngstown, OH", "Akron, OH"): (60, 1.0),
        ("Columbus, OH", "Akron, OH"): (120, 2.1),
        ("Akron, OH", "Columbus, OH"): (120, 2.1),
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
         patch("optimizer.chain_optimizer.score_strategic", side_effect=_fake_score_strategic):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGeneratesFourScenarios:
    def test_generates_four_scenarios(self):
        """Result should have quick/normal/slow/detention keys."""
        loads = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),
        ]
        result = generate_scenarios(
            loads=loads,
            current_city="Columbus, OH",
            db_path=TEST_DB_PATH,
        )

        assert "scenarios" in result
        scenarios = result["scenarios"]
        assert "quick" in scenarios
        assert "normal" in scenarios
        assert "slow" in scenarios
        assert "detention" in scenarios

        # Each scenario should have dwell_hours and recommendations keys
        for name in ["quick", "normal", "slow", "detention"]:
            assert "dwell_hours" in scenarios[name]
            assert "recommendations" in scenarios[name]

        # Verify dwell hours
        assert scenarios["quick"]["dwell_hours"] == 0.5
        assert scenarios["normal"]["dwell_hours"] == 1.5
        assert scenarios["slow"]["dwell_hours"] == 3.0
        assert scenarios["detention"]["dwell_hours"] == 6.0


class TestQuickScenarioHasMoreOptions:
    def test_quick_scenario_has_more_options(self):
        """Quick (less dwell) should have >= as many options as detention."""
        loads = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),
            _make_load("Akron", "OH", "Canton", "OH", 200, 25),
        ]
        result = generate_scenarios(
            loads=loads,
            current_city="Columbus, OH",
            db_path=TEST_DB_PATH,
        )
        scenarios = result["scenarios"]

        quick_count = len(scenarios["quick"]["recommendations"])
        detention_count = len(scenarios["detention"]["recommendations"])

        assert quick_count >= detention_count


class TestEmptyLoadsReturnsEmptyScenarios:
    def test_empty_loads_returns_empty_scenarios(self):
        """No loads should produce all empty scenario recommendations."""
        result = generate_scenarios(
            loads=[],
            current_city="Columbus, OH",
            db_path=TEST_DB_PATH,
        )

        assert "scenarios" in result
        for name in ["quick", "normal", "slow", "detention"]:
            assert result["scenarios"][name]["recommendations"] == []


class TestDetentionReducesOptions:
    def test_detention_reduces_options(self):
        """With tight HOS, detention scenario should have fewer/no options."""
        # Give driver very limited duty hours
        # After 6hr detention dwell, duty_remaining would go negative
        tight_hos = HOSState(
            drive_hours_remaining=8.0,
            duty_hours_remaining=7.0,  # 7hr left - 6hr detention = 1hr, not enough
            weekly_hours_remaining=50.0,
        )
        loads = [
            _make_load("Columbus", "OH", "Pittsburgh", "PA", 600, 185),
        ]
        result = generate_scenarios(
            loads=loads,
            current_city="Columbus, OH",
            hos_state=tight_hos,
            db_path=TEST_DB_PATH,
        )
        scenarios = result["scenarios"]

        quick_count = len(scenarios["quick"]["recommendations"])
        detention_count = len(scenarios["detention"]["recommendations"])

        # Quick should have options (7 - 0.5 = 6.5hr duty left)
        # Detention may have fewer or none (7 - 6 = 1hr duty left)
        assert quick_count >= detention_count


class TestResultFormat:
    def test_result_has_current_city(self):
        result = generate_scenarios(
            loads=[],
            current_city="Columbus, OH",
            db_path=TEST_DB_PATH,
        )
        assert result["current_city"] == "Columbus, OH"

    def test_result_has_hos_state(self):
        hos = HOSState(drive_hours_remaining=9.0)
        result = generate_scenarios(
            loads=[],
            current_city="Columbus, OH",
            hos_state=hos,
            db_path=TEST_DB_PATH,
        )
        assert result["hos_state"]["drive_hours_remaining"] == 9.0
