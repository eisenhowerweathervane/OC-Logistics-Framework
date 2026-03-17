"""Tests for the cost model with itemized breakdown and driver pay modes."""

import pytest

from costs.cost_model import CostBreakdown, calculate_load_cost
from models import CostConfig


@pytest.fixture
def default_config() -> CostConfig:
    """Standard CostConfig for testing."""
    return CostConfig()


@pytest.fixture
def config_with_maint() -> CostConfig:
    """Config that includes maintenance reserve."""
    return CostConfig(maint_reserve_monthly=400.0)


# ---- test_basic_cost_calculation ------------------------------------------

def test_basic_cost_calculation(default_config: CostConfig):
    """Verify total_cost > 0, profit = net_revenue - total_cost, factoring = rate * 0.03."""
    result = calculate_load_cost(
        loaded_miles=500,
        deadhead_miles=50,
        rate_total=1500.0,
        config=default_config,
    )
    assert result.total_cost > 0
    assert result.net_revenue is not None
    assert result.profit is not None
    assert result.profit == round(result.net_revenue - result.total_cost, 2)
    expected_factoring = round(1500.0 * default_config.factoring_fee_pct / 100, 2)
    assert result.factoring_amount == expected_factoring


# ---- test_cost_breakdown_components ---------------------------------------

def test_cost_breakdown_components(default_config: CostConfig):
    """Verify fuel_cost, driver_cost, lease_cost, insurance_cost are all > 0."""
    result = calculate_load_cost(
        loaded_miles=400,
        deadhead_miles=30,
        rate_total=1200.0,
        config=default_config,
    )
    assert result.fuel_cost > 0
    assert result.driver_cost > 0
    assert result.lease_cost > 0
    assert result.insurance_cost > 0


# ---- test_with_tolls_and_accessorials -------------------------------------

def test_with_tolls_and_accessorials(default_config: CostConfig):
    """Verify tolls and accessorials add to total_cost correctly."""
    base_result = calculate_load_cost(
        loaded_miles=300,
        deadhead_miles=20,
        rate_total=1000.0,
        config=default_config,
    )
    extras_result = calculate_load_cost(
        loaded_miles=300,
        deadhead_miles=20,
        rate_total=1000.0,
        config=default_config,
        toll_cost=75.0,
        accessorial_costs={"lumper": 50.0, "tarp": 25.0},
    )
    assert extras_result.toll_cost == 75.0
    assert extras_result.accessorial_total == 75.0
    assert extras_result.accessorial_detail == {"lumper": 50.0, "tarp": 25.0}
    expected_diff = 75.0 + 75.0  # tolls + accessorials
    assert round(extras_result.total_cost - base_result.total_cost, 2) == expected_diff


# ---- test_null_rate_returns_partial ---------------------------------------

def test_null_rate_returns_partial(default_config: CostConfig):
    """total_cost > 0 but revenue/profit fields are None when rate is None."""
    result = calculate_load_cost(
        loaded_miles=500,
        deadhead_miles=50,
        rate_total=None,
        config=default_config,
    )
    assert result.total_cost > 0
    assert result.gross_revenue is None
    assert result.factoring_amount is None
    assert result.net_revenue is None
    assert result.profit is None
    assert result.margin_pct is None
    assert result.rpm is None
    assert result.all_in_rpm is None


# ---- test_fuel_price_override ---------------------------------------------

def test_fuel_price_override(default_config: CostConfig):
    """Higher fuel price produces higher fuel_cost."""
    normal = calculate_load_cost(
        loaded_miles=500,
        deadhead_miles=50,
        rate_total=1500.0,
        config=default_config,
    )
    expensive = calculate_load_cost(
        loaded_miles=500,
        deadhead_miles=50,
        rate_total=1500.0,
        config=default_config,
        fuel_price_override=5.50,
    )
    assert expensive.fuel_cost > normal.fuel_cost


# ---- test_margin_and_rpm --------------------------------------------------

def test_margin_and_rpm(default_config: CostConfig):
    """Verify margin_pct and rpm calculations."""
    result = calculate_load_cost(
        loaded_miles=500,
        deadhead_miles=50,
        rate_total=2000.0,
        config=default_config,
    )
    assert result.margin_pct is not None
    assert result.rpm is not None
    assert result.all_in_rpm is not None

    # margin_pct = profit / gross_revenue * 100
    expected_margin = round(result.profit / result.gross_revenue * 100, 2)
    assert result.margin_pct == expected_margin

    # rpm = rate_per_mile on loaded miles only
    expected_rpm = round(result.gross_revenue / result.loaded_miles, 2)
    assert result.rpm == expected_rpm

    # all_in_rpm = net_revenue / total_miles
    expected_all_in = round(result.net_revenue / result.total_miles, 2)
    assert result.all_in_rpm == expected_all_in
