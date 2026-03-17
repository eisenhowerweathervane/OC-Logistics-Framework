"""Tests for the lane scorer module."""

import os
import pytest

from database import get_db, init_db
from scoring.lane_scorer import LaneScore, score_lane

TEST_DB = "/tmp/test_lane_scorer.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create a fresh test database for each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _insert_lane(conn, origin_city, origin_state, dest_city, dest_state,
                 avg_rate, load_count):
    conn.execute(
        """INSERT INTO lane_history
           (origin_city, origin_state, destination_city, destination_state,
            avg_rate, load_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (origin_city, origin_state, dest_city, dest_state, avg_rate, load_count),
    )
    conn.commit()


class TestLaneScorer:
    """Tests for score_lane() function."""

    def test_no_history_returns_neutral(self):
        """Empty DB should return neutral score with no data."""
        result = score_lane("Cleveland", "OH", "Atlanta", "GA", 1000.0, db_path=TEST_DB)
        assert result.score == 0.5
        assert result.data_points == 0
        assert result.level == "none"

    def test_above_average_rate_scores_high(self):
        """Rate 20% above lane average should score above 0.5."""
        with get_db(TEST_DB) as conn:
            _insert_lane(conn, "Cleveland", "OH", "Atlanta", "GA", 500.0, 10)

        result = score_lane("Cleveland", "OH", "Atlanta", "GA", 600.0, db_path=TEST_DB)
        assert result.score > 0.5
        assert result.level == "city"
        assert result.data_points == 10
        assert result.avg_rate == 500.0
        assert result.vs_average_pct is not None
        assert result.vs_average_pct > 0

    def test_below_average_rate_scores_low(self):
        """Rate below lane average should score below 0.5."""
        with get_db(TEST_DB) as conn:
            _insert_lane(conn, "Cleveland", "OH", "Atlanta", "GA", 700.0, 10)

        result = score_lane("Cleveland", "OH", "Atlanta", "GA", 500.0, db_path=TEST_DB)
        assert result.score < 0.5
        assert result.level == "city"
        assert result.vs_average_pct is not None
        assert result.vs_average_pct < 0

    def test_falls_back_to_state_level(self):
        """When city-level has < 3 loads, should fall back to state aggregation."""
        with get_db(TEST_DB) as conn:
            # City-level: only 2 loads (not enough)
            _insert_lane(conn, "Cleveland", "OH", "Atlanta", "GA", 500.0, 2)
            # Other OH→GA lanes to provide state-level data
            _insert_lane(conn, "Columbus", "OH", "Savannah", "GA", 550.0, 8)
            _insert_lane(conn, "Cincinnati", "OH", "Macon", "GA", 520.0, 7)

        result = score_lane("Cleveland", "OH", "Atlanta", "GA", 540.0, db_path=TEST_DB)
        assert result.level == "state"
        assert result.data_points >= 3

    def test_none_rate_returns_neutral(self):
        """If rate_total is None, return neutral score."""
        result = score_lane("Cleveland", "OH", "Atlanta", "GA", None, db_path=TEST_DB)
        assert result.score == 0.5
        assert result.level == "none"

    def test_score_clamped_to_range(self):
        """Score should be clamped to [0.0, 1.0] even for extreme rates."""
        with get_db(TEST_DB) as conn:
            _insert_lane(conn, "Cleveland", "OH", "Atlanta", "GA", 500.0, 10)

        # Way above average
        high = score_lane("Cleveland", "OH", "Atlanta", "GA", 2000.0, db_path=TEST_DB)
        assert high.score <= 1.0

        # Way below average
        low = score_lane("Cleveland", "OH", "Atlanta", "GA", 50.0, db_path=TEST_DB)
        assert low.score >= 0.0

    def test_returns_lane_score_dataclass(self):
        """Should return a LaneScore instance."""
        result = score_lane("Cleveland", "OH", "Atlanta", "GA", 500.0, db_path=TEST_DB)
        assert isinstance(result, LaneScore)
