"""Tests for the strategic scorer module."""

import os
import pytest

from database import get_db, init_db, seed_defaults
from scoring.strategic_scorer import StrategicScore, score_strategic

TEST_DB = "/tmp/test_strategic_scorer.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create a fresh test database with seed data for each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_defaults(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestStrategicScorer:
    """Tests for score_strategic() function."""

    def test_tier1_destination_scores_high(self):
        """Tier 1 city (Atlanta, GA) should score >= 0.7."""
        result = score_strategic("Atlanta", "GA", db_path=TEST_DB)
        assert result.score >= 0.7
        assert result.destination_tier == 1

    def test_tier3_destination_scores_low(self):
        """Tier 3 city (Erie, PA) should score <= 0.4."""
        result = score_strategic("Erie", "PA", db_path=TEST_DB)
        assert result.score <= 0.4
        assert result.destination_tier == 3

    def test_unknown_city_returns_default(self):
        """City not in tiers should return default score around 0.4."""
        result = score_strategic("Nowhereville", "XX", db_path=TEST_DB)
        assert result.score == pytest.approx(0.4, abs=0.1)
        assert result.destination_tier is None

    def test_home_state_bonus(self):
        """Destination in OH with Cleveland home should get +0.05 boost."""
        # Columbus OH is Tier 1 (base 0.8), home is Cleveland OH → +0.05
        result = score_strategic(
            "Columbus", "OH", home_base="Cleveland, OH", db_path=TEST_DB
        )
        assert result.home_distance_factor == 0.05
        assert result.score == pytest.approx(0.85, abs=0.01)

    def test_no_bonus_for_different_state(self):
        """Destination outside home state should get no proximity bonus."""
        result = score_strategic(
            "Atlanta", "GA", home_base="Cleveland, OH", db_path=TEST_DB
        )
        assert result.home_distance_factor == 0.0

    def test_tier2_destination(self):
        """Tier 2 city should score around 0.5."""
        result = score_strategic("Pittsburgh", "PA", db_path=TEST_DB)
        assert result.destination_tier == 2
        assert result.score == pytest.approx(0.5, abs=0.1)

    def test_score_clamped(self):
        """Score should never exceed 1.0 even with bonuses."""
        # Tier 1 OH city with OH home = 0.8 + 0.05 = 0.85 (fine, but test clamp logic)
        result = score_strategic(
            "Columbus", "OH", home_base="Cleveland, OH", db_path=TEST_DB
        )
        assert 0.0 <= result.score <= 1.0

    def test_returns_strategic_score_dataclass(self):
        """Should return a StrategicScore instance."""
        result = score_strategic("Atlanta", "GA", db_path=TEST_DB)
        assert isinstance(result, StrategicScore)

    def test_detail_dict_populated(self):
        """Detail dict should contain context information."""
        result = score_strategic("Atlanta", "GA", db_path=TEST_DB)
        assert "dest_city" in result.detail
        assert "dest_state" in result.detail
        assert "home_base" in result.detail
        assert result.detail["dest_city"] == "Atlanta"
