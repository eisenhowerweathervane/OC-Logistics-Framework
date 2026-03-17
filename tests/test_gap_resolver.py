"""Tests for ingestion.gap_resolver — gap detection and field completion."""

import pytest

from models import ParsedLoad
from ingestion.gap_resolver import (
    CONFIDENCE_THRESHOLD,
    SCORING_FIELDS,
    GapReport,
    resolve_gaps,
)


# ---------------------------------------------------------------------------
# Helpers — sample loads
# ---------------------------------------------------------------------------

def _full_load() -> ParsedLoad:
    """A load with all required + scoring fields populated."""
    return ParsedLoad(
        origin_city="Dallas",
        origin_state="TX",
        destination_city="Houston",
        destination_state="TX",
        mileage=240,
        source="paste",
        rate_total=720.00,
        deadhead_miles=30,
        weight=42000,
        pickup_date="2026-03-20",
        delivery_date="2026-03-21",
        broker_name="ABC Logistics",
    )


def _minimal_load() -> ParsedLoad:
    """A load with only required fields."""
    return ParsedLoad(
        origin_city="Dallas",
        origin_state="TX",
        destination_city="Houston",
        destination_state="TX",
        mileage=240,
        source="paste",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveGaps:
    def test_complete_load_has_no_gaps(self):
        load = _full_load()
        report = resolve_gaps(load)

        assert report.is_complete is True
        assert report.missing_required == []
        assert report.missing_optional == []

    def test_missing_rate_flagged_as_optional_gap(self):
        load = _minimal_load()
        report = resolve_gaps(load)

        assert report.is_complete is True
        assert "rate_total" in report.missing_optional

    def test_low_confidence_fields_flagged(self):
        load = _full_load()
        confidence = {"rate_total": 0.5, "origin_city": 0.9}
        report = resolve_gaps(load, field_confidence=confidence)

        assert "rate_total" in report.low_confidence
        assert "origin_city" not in report.low_confidence

    def test_missing_required_mileage_zero(self):
        load = ParsedLoad(
            origin_city="Dallas",
            origin_state="TX",
            destination_city="Houston",
            destination_state="TX",
            mileage=0,
            source="paste",
        )
        report = resolve_gaps(load)

        assert report.is_complete is False
        assert "mileage" in report.missing_required

    def test_fields_parsed_count(self):
        load = _full_load()
        report = resolve_gaps(load)

        # All 5 required + 6 scoring fields present
        assert report.fields_parsed == 11

    def test_fields_total_is_eleven(self):
        report = resolve_gaps(_minimal_load())
        # 5 required + 6 scoring = 11
        assert report.fields_total == 11


class TestGapReport:
    def test_apply_fills_merges_fields(self):
        load = _minimal_load()
        report = resolve_gaps(load)
        updated = report.apply_fills(load, {"rate_total": 500.0, "broker_name": "XYZ"})

        assert updated.rate_total == 500.0
        assert updated.broker_name == "XYZ"
        # Original unchanged
        assert load.rate_total is None

    def test_summary_message(self):
        load = _minimal_load()
        report = resolve_gaps(load)

        assert "Parsed" in report.summary or "parsed" in report.summary.lower()
        assert "of" in report.summary
