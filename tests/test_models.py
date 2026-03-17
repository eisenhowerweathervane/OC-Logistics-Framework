"""Tests for shared Pydantic models."""

import pytest
from pydantic import ValidationError

from models import ParsedLoad, ParsedField, CostConfig, ScorerConfig


# ---------------------------------------------------------------------------
# ParsedLoad
# ---------------------------------------------------------------------------

class TestParsedLoad:
    """Tests for the ParsedLoad model."""

    def test_valid_minimal(self):
        """Minimal required fields produce a valid model."""
        load = ParsedLoad(
            origin_city="Chicago",
            origin_state="IL",
            destination_city="Dallas",
            destination_state="TX",
            mileage=920,
            source="email",
        )
        assert load.origin_city == "Chicago"
        assert load.origin_state == "IL"
        assert load.destination_city == "Dallas"
        assert load.destination_state == "TX"
        assert load.mileage == 920
        assert load.source == "email"
        # Defaults
        assert load.rate_total is None
        assert load.rate_per_mile is None
        assert load.deadhead_miles == 0
        assert load.weight is None
        assert load.equipment_type == "Van"
        assert load.commodity == ""
        assert load.broker_name == ""

    def test_valid_full(self):
        """All fields populated produce a valid model."""
        load = ParsedLoad(
            origin_city="Memphis",
            origin_state="TN",
            destination_city="Atlanta",
            destination_state="GA",
            mileage=390,
            source="ocr",
            rate_total=975.00,
            rate_per_mile=2.50,
            deadhead_miles=45,
            weight=42000,
            equipment_type="Reefer",
            commodity="Frozen Chicken",
            pickup_date="2026-03-20",
            pickup_time_window="08:00-12:00",
            delivery_date="2026-03-21",
            delivery_time_window="06:00-18:00",
            broker_name="TQL",
            broker_mc_number="MC-123456",
            contact_phone="555-123-4567",
            contact_email="dispatch@tql.com",
            load_number="LD-99887",
            notes="No touch freight",
        )
        assert load.rate_total == 975.00
        assert load.rate_per_mile == 2.50
        assert load.weight == 42000
        assert load.commodity == "Frozen Chicken"

    def test_missing_required_raises(self):
        """Omitting any required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ParsedLoad(
                origin_city="Chicago",
                # origin_state missing
                destination_city="Dallas",
                destination_state="TX",
                mileage=920,
                source="email",
            )

    def test_invalid_source_raises(self):
        """A source value outside the allowed literal raises ValidationError."""
        with pytest.raises(ValidationError):
            ParsedLoad(
                origin_city="Chicago",
                origin_state="IL",
                destination_city="Dallas",
                destination_state="TX",
                mileage=920,
                source="fax",
            )

    def test_rate_per_mile_auto_calc(self):
        """rate_per_mile is auto-calculated when rate_total and mileage are present."""
        load = ParsedLoad(
            origin_city="Chicago",
            origin_state="IL",
            destination_city="Dallas",
            destination_state="TX",
            mileage=1000,
            source="paste",
            rate_total=2500.00,
        )
        assert load.rate_per_mile == pytest.approx(2.50)

    def test_rate_per_mile_no_overwrite(self):
        """Explicit rate_per_mile is not overwritten by auto-calc."""
        load = ParsedLoad(
            origin_city="A",
            origin_state="B",
            destination_city="C",
            destination_state="D",
            mileage=1000,
            source="manual",
            rate_total=2500.00,
            rate_per_mile=3.00,
        )
        assert load.rate_per_mile == 3.00

    def test_to_dict(self):
        """to_dict returns a plain dict compatible with score_load()."""
        load = ParsedLoad(
            origin_city="Chicago",
            origin_state="IL",
            destination_city="Dallas",
            destination_state="TX",
            mileage=920,
            source="email",
            rate_total=2300.0,
        )
        d = load.to_dict()
        assert isinstance(d, dict)
        assert d["origin_city"] == "Chicago"
        assert d["origin_state"] == "IL"
        assert d["destination_city"] == "Dallas"
        assert d["destination_state"] == "TX"
        assert d["mileage"] == 920
        assert d["rate_total"] == 2300.0


# ---------------------------------------------------------------------------
# ParsedField
# ---------------------------------------------------------------------------

class TestParsedField:
    """Tests for the ParsedField OCR confidence wrapper."""

    def test_defaults(self):
        pf = ParsedField()
        assert pf.value is None
        assert pf.confidence == 1.0
        assert pf.source == "manual"

    def test_with_values(self):
        pf = ParsedField(value="Chicago", confidence=0.92, source="ocr")
        assert pf.value == "Chicago"
        assert pf.confidence == 0.92
        assert pf.source == "ocr"

    def test_numeric_value(self):
        pf = ParsedField(value=42000, confidence=0.85, source="ocr")
        assert pf.value == 42000


# ---------------------------------------------------------------------------
# CostConfig
# ---------------------------------------------------------------------------

class TestCostConfig:
    """Tests for the CostConfig model."""

    def test_defaults(self):
        cfg = CostConfig()
        assert cfg.truck_lease_monthly == 4000.0
        assert cfg.insurance_monthly == 1800.0
        assert cfg.overhead_monthly == 500.0
        assert cfg.expected_monthly_miles == 8000
        assert cfg.driver_pay_mode == "per_mile_only"
        assert cfg.driver_per_mile == 0.55
        assert cfg.fuel_mpg == 6.5
        assert cfg.default_fuel_price == 3.85

    def test_per_mile_conversions(self):
        cfg = CostConfig()
        assert cfg.truck_lease_per_mile == pytest.approx(4000.0 / 8000)
        assert cfg.insurance_per_mile == pytest.approx(1800.0 / 8000)
        assert cfg.overhead_per_mile == pytest.approx(500.0 / 8000)
        assert cfg.maint_reserve_per_mile == pytest.approx(0.0)

    def test_driver_pay_per_mile_only(self):
        cfg = CostConfig(driver_pay_mode="per_mile_only", driver_per_mile=0.60)
        assert cfg.driver_pay_per_mile == pytest.approx(0.60)

    def test_driver_pay_base_only(self):
        cfg = CostConfig(
            driver_pay_mode="base_only",
            driver_base_weekly=1200.0,
            expected_monthly_miles=10000,
        )
        # Weekly 1200 * 4.33 weeks/month = 5196 / 10000 miles
        expected = (1200.0 * 4.33) / 10000
        assert cfg.driver_pay_per_mile == pytest.approx(expected, rel=1e-2)

    def test_driver_pay_base_plus_mile(self):
        cfg = CostConfig(
            driver_pay_mode="base_plus_mile",
            driver_base_weekly=800.0,
            driver_per_mile=0.30,
            expected_monthly_miles=8000,
        )
        base_component = (800.0 * 4.33) / 8000
        expected = base_component + 0.30
        assert cfg.driver_pay_per_mile == pytest.approx(expected, rel=1e-2)

    def test_total_base_cpm(self):
        cfg = CostConfig()
        cpm = cfg.total_base_cpm()
        # Should be sum of all per-mile costs
        expected = (
            cfg.truck_lease_per_mile
            + cfg.insurance_per_mile
            + cfg.overhead_per_mile
            + cfg.maint_reserve_per_mile
            + cfg.driver_pay_per_mile
            + cfg.factoring_fee_pct / 100  # factoring as a fraction (applied differently, but included as base)
            + cfg.default_fuel_price / cfg.fuel_mpg
        )
        assert cpm == pytest.approx(expected, rel=1e-2)

    def test_total_base_cpm_fuel_override(self):
        cfg = CostConfig()
        cpm_default = cfg.total_base_cpm()
        cpm_high = cfg.total_base_cpm(fuel_price_override=5.00)
        assert cpm_high > cpm_default


# ---------------------------------------------------------------------------
# ScorerConfig
# ---------------------------------------------------------------------------

class TestScorerConfig:
    """Tests for the ScorerConfig model."""

    def test_defaults_sum_to_one(self):
        cfg = ScorerConfig()
        total = (
            cfg.financial_weight
            + cfg.lane_weight
            + cfg.broker_weight
            + cfg.strategic_weight
        )
        assert total == pytest.approx(1.0, abs=0.01)

    def test_custom_weights_valid(self):
        cfg = ScorerConfig(
            financial_weight=0.40,
            lane_weight=0.20,
            broker_weight=0.20,
            strategic_weight=0.20,
        )
        assert cfg.financial_weight == 0.40

    def test_custom_weights_invalid_sum(self):
        with pytest.raises(ValidationError):
            ScorerConfig(
                financial_weight=0.50,
                lane_weight=0.50,
                broker_weight=0.50,
                strategic_weight=0.50,
            )
