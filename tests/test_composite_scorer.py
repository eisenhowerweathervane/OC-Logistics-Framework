"""Tests for the composite scorer that combines all four sub-scorers."""

import os
import tempfile

import pytest

from database import init_db, seed_defaults, get_db
from costs.cost_model import CostBreakdown
from scoring.composite_scorer import CompositeScore, score_load_composite
from scoring.financial_scorer import FinancialScore
from scoring.lane_scorer import LaneScore
from scoring.broker_scorer import BrokerScore
from scoring.strategic_scorer import StrategicScore


@pytest.fixture()
def test_db(tmp_path):
    """Create a temporary test database with defaults seeded."""
    db_path = str(tmp_path / "test_composite.db")
    init_db(db_path)
    seed_defaults(db_path)
    return db_path


def _make_cost_breakdown(
    margin_pct=30.0,
    all_in_rpm=3.50,
    loaded_miles=200.0,
    deadhead_miles=10.0,
    rate_total=700.0,
) -> CostBreakdown:
    """Helper to build a CostBreakdown for testing."""
    total_miles = loaded_miles + deadhead_miles
    return CostBreakdown(
        loaded_miles=loaded_miles,
        deadhead_miles=deadhead_miles,
        total_miles=total_miles,
        fuel_cost=100.0,
        driver_cost=110.0,
        lease_cost=50.0,
        insurance_cost=20.0,
        overhead_cost=10.0,
        maint_reserve_cost=5.0,
        toll_cost=0.0,
        accessorial_total=0.0,
        base_cpm=1.40,
        total_cost=294.0,
        gross_revenue=rate_total,
        net_revenue=rate_total * 0.97 if rate_total else None,
        profit=rate_total * 0.97 - 294.0 if rate_total else None,
        margin_pct=margin_pct,
        rpm=rate_total / loaded_miles if rate_total and loaded_miles else None,
        all_in_rpm=all_in_rpm,
    )


def _make_load(
    origin_city="Columbus",
    origin_state="OH",
    dest_city="Atlanta",
    dest_state="GA",
    rate_total=700.0,
    broker_name="Test Broker",
):
    """Helper to build a load dict."""
    return {
        "origin_city": origin_city,
        "origin_state": origin_state,
        "destination_city": dest_city,
        "destination_state": dest_state,
        "rate_total": rate_total,
        "broker_name": broker_name,
        "mileage": 200,
    }


class TestCompositeScorer:
    """Tests for score_load_composite()."""

    def test_scores_with_all_defaults(self, test_db):
        """Provide a profitable load and get a score between 0 and 1 with an action."""
        load = _make_load()
        cost = _make_cost_breakdown()
        result = score_load_composite(load, cost, current_city=None, db_path=test_db)

        assert result.score is not None
        assert 0.0 <= result.score <= 1.0
        assert result.action in ("BOOK IT", "CONSIDER", "NEGOTIATE", "PASS")

    def test_null_rate_returns_negotiate(self, test_db):
        """When no rate is available, score should be None and action NEGOTIATE."""
        load = _make_load(rate_total=None)
        cost = _make_cost_breakdown(margin_pct=None, all_in_rpm=None, rate_total=None)
        result = score_load_composite(load, cost, current_city=None, db_path=test_db)

        assert result.score is None
        assert result.action == "NEGOTIATE"

    def test_weights_affect_score(self, test_db):
        """Changing weights in DB should produce a different composite score."""
        load = _make_load()
        cost = _make_cost_breakdown()

        result1 = score_load_composite(load, cost, current_city=None, db_path=test_db)

        # Change weights: make financial weight 1.0 and everything else 0.0
        with get_db(test_db) as conn:
            conn.execute(
                """UPDATE scorer_config SET
                   financial_weight = 1.0,
                   lane_weight = 0.0,
                   broker_weight = 0.0,
                   strategic_weight = 0.0
                   WHERE id = 1"""
            )
            conn.commit()

        result2 = score_load_composite(load, cost, current_city=None, db_path=test_db)

        # Scores should differ because the weights changed
        assert result2.score is not None
        assert result1.score != result2.score

    def test_includes_all_sub_scores(self, test_db):
        """Result should include financial, lane, broker, and strategic sub-scores."""
        load = _make_load()
        cost = _make_cost_breakdown()
        result = score_load_composite(load, cost, current_city=None, db_path=test_db)

        assert isinstance(result.financial, FinancialScore)
        assert isinstance(result.lane, LaneScore)
        assert isinstance(result.broker, BrokerScore)
        assert isinstance(result.strategic, StrategicScore)

    def test_action_tiers(self, test_db):
        """Verify that score thresholds produce correct action labels."""
        load = _make_load()

        # Set weights to 100% financial so we control the composite score
        with get_db(test_db) as conn:
            conn.execute(
                """UPDATE scorer_config SET
                   financial_weight = 1.0,
                   lane_weight = 0.0,
                   broker_weight = 0.0,
                   strategic_weight = 0.0
                   WHERE id = 1"""
            )
            conn.commit()

        # Excellent financial -> BOOK IT (score >= 0.75)
        cost_high = _make_cost_breakdown(margin_pct=30.0, all_in_rpm=3.50)
        result_high = score_load_composite(load, cost_high, current_city=None, db_path=test_db)
        assert result_high.action == "BOOK IT"

        # Terrible financial -> PASS (score < 0.40)
        cost_low = _make_cost_breakdown(margin_pct=-5.0, all_in_rpm=1.50, loaded_miles=50.0)
        result_low = score_load_composite(load, cost_low, current_city=None, db_path=test_db)
        assert result_low.action == "PASS"

    def test_weights_dict_in_result(self, test_db):
        """The result should include the weights that were used."""
        load = _make_load()
        cost = _make_cost_breakdown()
        result = score_load_composite(load, cost, current_city=None, db_path=test_db)

        assert isinstance(result.weights, dict)
        assert "financial" in result.weights
        assert "lane" in result.weights
        assert "broker" in result.weights
        assert "strategic" in result.weights
