"""Tests for the standalone financial scorer module."""

import pytest
from scoring.financial_scorer import FinancialScore, score_financial


class TestFinancialScorer:
    """Tests for score_financial() function."""

    def test_excellent_load(self):
        """High-margin, high-RPM, low-deadhead, sweet-spot mileage, no detention."""
        result = score_financial(
            margin_pct=30.0,
            all_in_rpm=3.50,
            deadhead_pct=3.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert result.score is not None
        assert result.score >= 0.7
        assert result.action == "BOOK IT"

    def test_terrible_load(self):
        """Negative margin, low RPM, high deadhead, short haul, long detention."""
        result = score_financial(
            margin_pct=-5.0,
            all_in_rpm=1.50,
            deadhead_pct=40.0,
            loaded_miles=50.0,
            detention_hours=3.0,
        )
        assert result.score is not None
        assert result.score <= 0.3
        assert result.action == "PASS"

    def test_null_rate_returns_none(self):
        """When margin_pct is None (no rate available), score should be None."""
        result = score_financial(
            margin_pct=None,
            all_in_rpm=None,
            deadhead_pct=10.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert result.score is None
        assert result.raw_score is None
        assert result.action == "NEGOTIATE"

    def test_action_tier_book_it(self):
        """High margin should produce BOOK IT action."""
        result = score_financial(
            margin_pct=30.0,
            all_in_rpm=3.00,
            deadhead_pct=5.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert result.action == "BOOK IT"

    def test_action_tier_pass(self):
        """Negative margin should produce PASS action."""
        result = score_financial(
            margin_pct=-5.0,
            all_in_rpm=1.50,
            deadhead_pct=30.0,
            loaded_miles=50.0,
            detention_hours=3.0,
        )
        assert result.action == "PASS"

    def test_score_normalized_to_zero_one(self):
        """All scores should be normalized between 0.0 and 1.0."""
        test_cases = [
            {"margin_pct": 30.0, "all_in_rpm": 3.50},
            {"margin_pct": 20.0, "all_in_rpm": 2.75},
            {"margin_pct": 10.0, "all_in_rpm": 2.00},
            {"margin_pct": 0.0, "all_in_rpm": 1.80},
            {"margin_pct": -5.0, "all_in_rpm": 1.50},
        ]
        for case in test_cases:
            result = score_financial(
                margin_pct=case["margin_pct"],
                all_in_rpm=case["all_in_rpm"],
                deadhead_pct=10.0,
                loaded_miles=200.0,
                detention_hours=0.0,
            )
            assert result.score is not None, f"Score should not be None for {case}"
            assert 0.0 <= result.score <= 1.0, (
                f"Score {result.score} out of range for {case}"
            )

    def test_components_dict_present(self):
        """The components dict should contain the individual score breakdowns."""
        result = score_financial(
            margin_pct=30.0,
            all_in_rpm=3.50,
            deadhead_pct=3.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert isinstance(result.components, dict)
        assert "margin" in result.components
        assert "rpm" in result.components
        assert "deadhead" in result.components
        assert "mileage" in result.components
        assert "detention" in result.components

    def test_raw_score_clamped(self):
        """Raw score should be clamped to [-10, +10]."""
        result = score_financial(
            margin_pct=30.0,
            all_in_rpm=3.50,
            deadhead_pct=3.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert result.raw_score is not None
        assert -10 <= result.raw_score <= 10

    def test_consider_tier(self):
        """Mid-range score should produce CONSIDER action."""
        result = score_financial(
            margin_pct=15.0,
            all_in_rpm=2.50,
            deadhead_pct=10.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        # raw = 2 (margin) + 1 (rpm) + 1 (deadhead) + 1 (mileage) + 0 (detention) = 5
        # Actually that's BOOK IT territory. Let's adjust.
        # With margin=15 -> +2, rpm=2.00 -> 0, deadhead=10 -> +1, miles=200 -> +1, det=0 -> 0 = 4
        result2 = score_financial(
            margin_pct=15.0,
            all_in_rpm=2.00,
            deadhead_pct=10.0,
            loaded_miles=200.0,
            detention_hours=0.0,
        )
        assert result2.action == "CONSIDER"

    def test_negotiate_tier(self):
        """Borderline score should produce NEGOTIATE action."""
        # margin=5% -> 0, rpm=2.00 -> 0, deadhead=10 -> +1, miles=100 -> 0, det=0 -> 0 = 1
        result = score_financial(
            margin_pct=5.0,
            all_in_rpm=2.00,
            deadhead_pct=10.0,
            loaded_miles=100.0,
            detention_hours=0.0,
        )
        assert result.action == "NEGOTIATE"
