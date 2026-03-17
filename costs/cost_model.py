"""Cost calculation with itemized breakdown.

Supports tolls, accessorials, detention, and all driver pay modes defined
in :class:`models.CostConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from models import CostConfig


@dataclass
class CostBreakdown:
    """Itemized cost breakdown for a single load."""

    # Miles
    loaded_miles: float
    deadhead_miles: float
    total_miles: float

    # Cost components
    fuel_cost: float
    driver_cost: float
    lease_cost: float
    insurance_cost: float
    overhead_cost: float
    maint_reserve_cost: float
    toll_cost: float
    accessorial_total: float
    accessorial_detail: Dict[str, float] = field(default_factory=dict)
    base_cpm: float = 0.0
    total_cost: float = 0.0

    # Revenue (None when rate unknown)
    gross_revenue: Optional[float] = None
    factoring_amount: Optional[float] = None
    net_revenue: Optional[float] = None
    profit: Optional[float] = None
    margin_pct: Optional[float] = None
    rpm: Optional[float] = None
    all_in_rpm: Optional[float] = None


def calculate_load_cost(
    loaded_miles: float,
    deadhead_miles: float,
    rate_total: Optional[float],
    config: CostConfig,
    fuel_price_override: Optional[float] = None,
    toll_cost: float = 0.0,
    accessorial_costs: Optional[Dict[str, float]] = None,
    detention_hours: float = 0.0,
    detention_rate: float = 50.0,
) -> CostBreakdown:
    """Calculate per-load cost with full itemization.

    Parameters
    ----------
    loaded_miles:
        Revenue miles for the load.
    deadhead_miles:
        Empty / repositioning miles.
    rate_total:
        Gross line-haul rate (before detention). *None* when rate is unknown.
    config:
        Carrier cost configuration.
    fuel_price_override:
        If provided, overrides ``config.default_fuel_price``.
    toll_cost:
        Flat toll amount for the load.
    accessorial_costs:
        Mapping of accessorial name -> dollar amount.
    detention_hours:
        Hours of detention to bill.
    detention_rate:
        Hourly detention rate.
    """
    total_miles = loaded_miles + deadhead_miles
    fuel_price = fuel_price_override if fuel_price_override is not None else config.default_fuel_price

    # Individual cost components (per-mile rate * total miles)
    fuel_cost = round((fuel_price / config.fuel_mpg) * total_miles, 2)
    driver_cost = round(config.driver_pay_per_mile * total_miles, 2)
    lease_cost = round(config.truck_lease_per_mile * total_miles, 2)
    insurance_cost = round(config.insurance_per_mile * total_miles, 2)
    overhead_cost = round(config.overhead_per_mile * total_miles, 2)
    maint_reserve_cost = round(config.maint_reserve_per_mile * total_miles, 2)

    # Base CPM (excludes factoring — factoring is a revenue-side deduction)
    base_cpm = round(
        (fuel_price / config.fuel_mpg)
        + config.driver_pay_per_mile
        + config.truck_lease_per_mile
        + config.insurance_per_mile
        + config.overhead_per_mile
        + config.maint_reserve_per_mile,
        4,
    )

    # Accessorials
    acc = accessorial_costs or {}
    accessorial_total = round(sum(acc.values()), 2)

    # Total cost
    total_cost = round(base_cpm * total_miles + toll_cost + accessorial_total, 2)

    # Revenue / profit (only when rate is known)
    gross_revenue: Optional[float] = None
    factoring_amount: Optional[float] = None
    net_revenue: Optional[float] = None
    profit: Optional[float] = None
    margin_pct: Optional[float] = None
    rpm: Optional[float] = None
    all_in_rpm: Optional[float] = None

    if rate_total is not None:
        detention_revenue = round(detention_hours * detention_rate, 2)
        gross_revenue = round(rate_total + detention_revenue, 2)
        factoring_amount = round(rate_total * config.factoring_fee_pct / 100, 2)
        net_revenue = round(gross_revenue - factoring_amount, 2)
        profit = round(net_revenue - total_cost, 2)
        if gross_revenue:
            margin_pct = round(profit / gross_revenue * 100, 2)
        if loaded_miles:
            rpm = round(gross_revenue / loaded_miles, 2)
        if total_miles:
            all_in_rpm = round(net_revenue / total_miles, 2)

    return CostBreakdown(
        loaded_miles=loaded_miles,
        deadhead_miles=deadhead_miles,
        total_miles=total_miles,
        fuel_cost=fuel_cost,
        driver_cost=driver_cost,
        lease_cost=lease_cost,
        insurance_cost=insurance_cost,
        overhead_cost=overhead_cost,
        maint_reserve_cost=maint_reserve_cost,
        toll_cost=toll_cost,
        accessorial_total=accessorial_total,
        accessorial_detail=dict(acc),
        base_cpm=base_cpm,
        total_cost=total_cost,
        gross_revenue=gross_revenue,
        factoring_amount=factoring_amount,
        net_revenue=net_revenue,
        profit=profit,
        margin_pct=margin_pct,
        rpm=rpm,
        all_in_rpm=all_in_rpm,
    )
