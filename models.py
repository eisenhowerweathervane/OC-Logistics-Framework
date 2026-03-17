"""Shared Pydantic models for the profitability engine.

These models are used across all modules: ingestion parsers, cost calculator,
scorers, optimizer, and API endpoints.
"""

from typing import Literal, Optional, Union

from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# ParsedField — OCR confidence wrapper
# ---------------------------------------------------------------------------

class ParsedField(BaseModel):
    """Wraps a parsed value with confidence and source metadata."""

    value: Optional[Union[str, int, float]] = None
    confidence: float = 1.0
    source: Literal["email", "paste", "ocr", "manual"] = "manual"


# ---------------------------------------------------------------------------
# ParsedLoad — Unified load structure from all parsers
# ---------------------------------------------------------------------------

class ParsedLoad(BaseModel):
    """Unified load structure produced by every parser."""

    # Required
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    mileage: int
    source: Literal["email", "paste", "ocr", "manual"]

    # Optional — rate
    rate_total: Optional[float] = None
    rate_per_mile: Optional[float] = None

    # Optional — logistics
    deadhead_miles: int = 0
    weight: Optional[int] = None
    equipment_type: str = "Van"
    commodity: str = ""

    # Optional — schedule
    pickup_date: str = ""
    pickup_time_window: str = ""
    delivery_date: str = ""
    delivery_time_window: str = ""

    # Optional — broker / contact
    broker_name: str = ""
    broker_mc_number: str = ""
    contact_phone: str = ""
    contact_email: str = ""

    # Optional — reference
    load_number: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _auto_calc_rate_per_mile(self) -> "ParsedLoad":
        """Auto-calculate rate_per_mile from rate_total / mileage when not set."""
        if (
            self.rate_per_mile is None
            and self.rate_total is not None
            and self.mileage
            and self.mileage > 0
        ):
            self.rate_per_mile = round(self.rate_total / self.mileage, 2)
        return self

    def to_dict(self) -> dict:
        """Return a plain dict compatible with the existing score_load() function."""
        return self.model_dump()


# ---------------------------------------------------------------------------
# CostConfig — Cost configuration with monthly-to-per-mile conversion
# ---------------------------------------------------------------------------

_WEEKS_PER_MONTH = 4.33


class CostConfig(BaseModel):
    """Carrier cost configuration. Monthly fixed costs are converted to per-mile."""

    # Monthly fixed costs
    truck_lease_monthly: float = 4000.0
    insurance_monthly: float = 1800.0
    overhead_monthly: float = 500.0
    maint_reserve_monthly: float = 0.0
    expected_monthly_miles: int = 8000

    # Driver pay
    driver_pay_mode: Literal["base_plus_mile", "per_mile_only", "base_only"] = "per_mile_only"
    driver_base_weekly: float = 0.0
    driver_per_mile: float = 0.55

    # Other variable costs
    factoring_fee_pct: float = 3.0
    fuel_mpg: float = 6.5
    default_fuel_price: float = 3.85

    # -- Per-mile properties --------------------------------------------------

    @property
    def truck_lease_per_mile(self) -> float:
        return self.truck_lease_monthly / self.expected_monthly_miles

    @property
    def insurance_per_mile(self) -> float:
        return self.insurance_monthly / self.expected_monthly_miles

    @property
    def overhead_per_mile(self) -> float:
        return self.overhead_monthly / self.expected_monthly_miles

    @property
    def maint_reserve_per_mile(self) -> float:
        return self.maint_reserve_monthly / self.expected_monthly_miles

    @property
    def driver_pay_per_mile(self) -> float:
        """Compute effective driver cost per mile based on pay mode."""
        if self.driver_pay_mode == "per_mile_only":
            return self.driver_per_mile
        elif self.driver_pay_mode == "base_only":
            monthly_base = self.driver_base_weekly * _WEEKS_PER_MONTH
            return monthly_base / self.expected_monthly_miles
        else:  # base_plus_mile
            monthly_base = self.driver_base_weekly * _WEEKS_PER_MONTH
            return (monthly_base / self.expected_monthly_miles) + self.driver_per_mile

    def total_base_cpm(self, fuel_price_override: float | None = None) -> float:
        """Total base cost-per-mile including fuel."""
        fuel_price = fuel_price_override if fuel_price_override is not None else self.default_fuel_price
        fuel_cpm = fuel_price / self.fuel_mpg

        return (
            self.truck_lease_per_mile
            + self.insurance_per_mile
            + self.overhead_per_mile
            + self.maint_reserve_per_mile
            + self.driver_pay_per_mile
            + self.factoring_fee_pct / 100
            + fuel_cpm
        )


# ---------------------------------------------------------------------------
# ScorerConfig — Composite scorer weights
# ---------------------------------------------------------------------------

class ScorerConfig(BaseModel):
    """Weights for the composite load scorer. Must sum to 1.0."""

    financial_weight: float = 0.50
    lane_weight: float = 0.15
    broker_weight: float = 0.15
    strategic_weight: float = 0.20

    @model_validator(mode="after")
    def _weights_must_sum_to_one(self) -> "ScorerConfig":
        total = (
            self.financial_weight
            + self.lane_weight
            + self.broker_weight
            + self.strategic_weight
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Scorer weights must sum to 1.0 (got {total:.4f})"
            )
        return self
