"""Scenario engine for dwell-time branch analysis.

Generates multiple scenario branches (quick, normal, slow, detention) based on
different dwell times at delivery. Each scenario re-runs the chain optimizer
with adjusted HOS state to show how delays affect future load options.
"""

from __future__ import annotations

from typing import Optional

from optimizer.chain_optimizer import optimize_chain
from optimizer.hos_model import HOSState


# Dwell-time scenarios in hours
SCENARIOS = {
    "quick": 0.5,
    "normal": 1.5,
    "slow": 3.0,
    "detention": 6.0,
}


def generate_scenarios(
    loads: list[dict],
    current_city: str,
    hos_state: Optional[HOSState] = None,
    home_base: str = "Cleveland, OH",
    max_days: int = 1,
    db_path: str = "loads.db",
) -> dict:
    """Generate scenario branches based on different dwell times.

    For each dwell scenario (quick/normal/slow/detention), adjusts the HOS
    state by applying the dwell time and re-runs optimize_chain to find the
    top 3 recommended next loads.

    Args:
        loads: Available load dicts to consider.
        current_city: Current truck position (e.g., "Columbus, OH").
        hos_state: Current HOS state (default: fresh driver).
        home_base: Driver's home base city.
        max_days: Maximum planning horizon in days.
        db_path: Database path for scorers.

    Returns:
        Dict with 'scenarios' (keyed by scenario name), 'current_city',
        and 'hos_state'.
    """
    if hos_state is None:
        hos_state = HOSState()

    scenarios = {}

    for name, dwell_hours in SCENARIOS.items():
        # Adjust HOS by subtracting dwell time from duty hours remaining
        adjusted_duty = hos_state.duty_hours_remaining - dwell_hours
        adjusted_weekly = hos_state.weekly_hours_remaining - dwell_hours

        # If dwell time exhausts duty hours, no viable chains
        if adjusted_duty <= 0 or adjusted_weekly <= 0:
            scenarios[name] = {
                "dwell_hours": dwell_hours,
                "recommendations": [],
            }
            continue

        adjusted_hos = HOSState(
            drive_hours_remaining=hos_state.drive_hours_remaining,
            duty_hours_remaining=adjusted_duty,
            weekly_hours_remaining=adjusted_weekly,
            consecutive_drive_hours=hos_state.consecutive_drive_hours,
            needs_break=hos_state.needs_break,
            needs_rest=hos_state.needs_rest,
        )

        # Run chain optimizer with adjusted HOS
        chain_result = optimize_chain(
            loads=loads,
            start_city=current_city,
            hos_state=adjusted_hos,
            home_base=home_base,
            db_path=db_path,
            max_days=max_days,
        )

        # Extract recommendations from viable chains
        recommendations = _extract_recommendations(chain_result, loads)

        scenarios[name] = {
            "dwell_hours": dwell_hours,
            "recommendations": recommendations[:3],
        }

    return {
        "scenarios": scenarios,
        "current_city": current_city,
        "hos_state": {
            "drive_hours_remaining": hos_state.drive_hours_remaining,
            "duty_hours_remaining": hos_state.duty_hours_remaining,
            "weekly_hours_remaining": hos_state.weekly_hours_remaining,
            "consecutive_drive_hours": hos_state.consecutive_drive_hours,
            "needs_break": hos_state.needs_break,
            "needs_rest": hos_state.needs_rest,
        },
    }


def _extract_recommendations(chain_result: dict, loads: list[dict]) -> list[dict]:
    """Extract first-leg recommendations from chain optimizer result.

    Each recommendation includes the load, its score, profit, and a chain summary.
    """
    legs = chain_result.get("legs", [])
    real_legs = [leg for leg in legs if not leg.get("is_return_home")]

    if not real_legs:
        return []

    # The first leg is the immediate next load recommendation
    first_leg = real_legs[0]
    result = first_leg.get("result", {})

    recommendation = {
        "load": first_leg.get("load", {}),
        "score": result.get("score", 0),
        "profit": result.get("profit", 0.0),
        "chain_summary": chain_result.get("summary", {}),
    }

    return [recommendation]
