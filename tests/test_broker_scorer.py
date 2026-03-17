"""Tests for the broker scorer module."""

import os
import pytest

from database import get_db, init_db
from scoring.broker_scorer import BrokerScore, score_broker

TEST_DB = "/tmp/test_broker_scorer.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create a fresh test database for each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _insert_broker(conn, broker_name, grade, loads_completed,
                   avg_detention=1.0, tonu_count=0,
                   rate_accuracy=95.0, ontime_pickup=90.0):
    conn.execute(
        """INSERT INTO broker_history
           (broker_name, reliability_grade, loads_completed,
            avg_detention_hours, tonu_count,
            rate_accuracy_pct, ontime_pickup_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (broker_name, grade, loads_completed,
         avg_detention, tonu_count, rate_accuracy, ontime_pickup),
    )
    conn.commit()


class TestBrokerScorer:
    """Tests for score_broker() function."""

    def test_unknown_broker_returns_neutral(self):
        """Broker not in DB should return neutral score with grade U."""
        result = score_broker("Unknown Logistics LLC", db_path=TEST_DB)
        assert result.score == 0.5
        assert result.grade == "U"
        assert result.loads_completed == 0

    def test_reliable_broker_scores_high(self):
        """Grade A broker should score above 0.6."""
        with get_db(TEST_DB) as conn:
            _insert_broker(conn, "Great Freight Inc", "A", 50,
                           avg_detention=0.5, tonu_count=0,
                           rate_accuracy=99.0, ontime_pickup=98.0)

        result = score_broker("Great Freight Inc", db_path=TEST_DB)
        assert result.score > 0.6
        assert result.grade == "A"
        assert result.loads_completed == 50

    def test_unreliable_broker_scores_low(self):
        """Grade F broker should score below 0.4."""
        with get_db(TEST_DB) as conn:
            _insert_broker(conn, "Bad Broker Co", "F", 3,
                           avg_detention=5.0, tonu_count=10,
                           rate_accuracy=60.0, ontime_pickup=40.0)

        result = score_broker("Bad Broker Co", db_path=TEST_DB)
        assert result.score < 0.4
        assert result.grade == "F"

    def test_empty_broker_name_returns_neutral(self):
        """Empty string broker name should return neutral."""
        result = score_broker("", db_path=TEST_DB)
        assert result.score == 0.5
        assert result.grade == "U"

    def test_none_broker_name_returns_neutral(self):
        """None broker name should return neutral."""
        result = score_broker(None, db_path=TEST_DB)
        assert result.score == 0.5
        assert result.grade == "U"

    def test_detail_dict_populated(self):
        """Detail dict should contain operational metrics for known brokers."""
        with get_db(TEST_DB) as conn:
            _insert_broker(conn, "Detail Test LLC", "B", 20,
                           avg_detention=2.0, tonu_count=1,
                           rate_accuracy=92.0, ontime_pickup=85.0)

        result = score_broker("Detail Test LLC", db_path=TEST_DB)
        assert "avg_detention_hours" in result.detail
        assert "tonu_count" in result.detail
        assert "rate_accuracy_pct" in result.detail
        assert "ontime_pickup_pct" in result.detail
        assert result.detail["avg_detention_hours"] == 2.0

    def test_returns_broker_score_dataclass(self):
        """Should return a BrokerScore instance."""
        result = score_broker("Anything", db_path=TEST_DB)
        assert isinstance(result, BrokerScore)

    def test_grade_b_score(self):
        """Grade B should map to 0.7."""
        with get_db(TEST_DB) as conn:
            _insert_broker(conn, "Mid Tier LLC", "B", 15)

        result = score_broker("Mid Tier LLC", db_path=TEST_DB)
        assert result.score == 0.7
        assert result.grade == "B"
