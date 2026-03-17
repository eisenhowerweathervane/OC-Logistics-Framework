"""Watchlist model for committed + flexible load planning.

Provides dataclasses and functions to manage a driver's committed loads
alongside a watchlist of candidate loads across different dwell-time scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from optimizer.hos_model import HOSState, apply_leg
from optimizer.scenario_engine import generate_scenarios
from distance_service import get_drive_info


@dataclass
class WatchlistEntry:
    """A candidate load on the watchlist with scenario context."""

    load: dict
    score: Optional[float] = None
    profit: Optional[float] = None
    scenarios: list[str] = field(default_factory=list)
    pickup_deadline: str = ""


@dataclass
class WatchlistPlan:
    """Complete plan with committed legs and flexible watchlist."""

    committed: list[dict] = field(default_factory=list)
    watchlist: list[WatchlistEntry] = field(default_factory=list)
    scenario_tree: dict = field(default_factory=dict)


def _load_destination_key(load: dict) -> str:
    """Format destination as 'City, ST'."""
    return f"{load.get('destination_city', '')}, {load.get('destination_state', '')}"


def _simulate_committed(
    committed_loads: list[dict],
    start_city: str,
    hos_state: HOSState,
    avg_speed: float = 52.0,
    dwell_time: float = 1.5,
) -> tuple[str, HOSState]:
    """Simulate driving through committed loads, returning final position and HOS.

    Args:
        committed_loads: List of committed/booked load dicts.
        start_city: Starting city.
        hos_state: Starting HOS state.
        avg_speed: Average speed for drive time calculation.
        dwell_time: Default dwell time per load.

    Returns:
        Tuple of (final_city, final_hos_state).
    """
    current_city = start_city
    current_hos = hos_state

    for load in committed_loads:
        origin = f"{load.get('origin_city', '')}, {load.get('origin_state', '')}"
        destination = _load_destination_key(load)

        # Calculate drive times
        dh_info = get_drive_info(current_city, origin, avg_speed)
        loaded_info = get_drive_info(origin, destination, avg_speed)

        total_drive = dh_info["drive_time_hours"] + loaded_info["drive_time_hours"]
        on_duty_time = total_drive + dwell_time

        # Apply leg to HOS
        current_hos = apply_leg(current_hos, total_drive, on_duty_time)
        current_city = destination

    return current_city, current_hos


def build_watchlist(
    committed_loads: list[dict],
    available_loads: list[dict],
    current_city: str = "Cleveland, OH",
    hos_state: Optional[HOSState] = None,
    home_base: str = "Cleveland, OH",
    max_days: int = 1,
    db_path: str = "loads.db",
) -> WatchlistPlan:
    """Build a watchlist plan from committed and available loads.

    Simulates driving through committed loads to determine position and HOS
    state, then generates scenarios for available loads.

    Args:
        committed_loads: Already booked load dicts.
        available_loads: Candidate load dicts to consider.
        current_city: Starting truck position.
        hos_state: Current HOS state (default: fresh driver).
        home_base: Driver's home base.
        max_days: Planning horizon in days.
        db_path: Database path for scorers.

    Returns:
        WatchlistPlan with committed legs, watchlist entries, and scenario tree.
    """
    if hos_state is None:
        hos_state = HOSState()

    # Simulate committed loads to find current position after them
    if committed_loads:
        final_city, final_hos = _simulate_committed(
            committed_loads, current_city, hos_state
        )
    else:
        final_city = current_city
        final_hos = hos_state

    # Generate scenarios from current position
    scenario_tree = generate_scenarios(
        loads=available_loads,
        current_city=final_city,
        hos_state=final_hos,
        home_base=home_base,
        max_days=max_days,
        db_path=db_path,
    )

    # Build watchlist entries from scenario recommendations
    # Track which scenarios each load appears in
    load_entries: dict[str, WatchlistEntry] = {}

    scenarios = scenario_tree.get("scenarios", {})
    for scenario_name, scenario_data in scenarios.items():
        for rec in scenario_data.get("recommendations", []):
            load = rec.get("load", {})
            # Create a key from load origin/destination/rate for dedup
            load_key = (
                f"{load.get('origin_city', '')}-{load.get('origin_state', '')}-"
                f"{load.get('destination_city', '')}-{load.get('destination_state', '')}-"
                f"{load.get('rate_total', '')}"
            )

            if load_key in load_entries:
                # Add this scenario to existing entry
                if scenario_name not in load_entries[load_key].scenarios:
                    load_entries[load_key].scenarios.append(scenario_name)
            else:
                load_entries[load_key] = WatchlistEntry(
                    load=load,
                    score=rec.get("score"),
                    profit=rec.get("profit"),
                    scenarios=[scenario_name],
                    pickup_deadline=load.get("pickup_date", ""),
                )

    return WatchlistPlan(
        committed=committed_loads,
        watchlist=list(load_entries.values()),
        scenario_tree=scenario_tree,
    )


def resolve_watchlist(actual_dwell_hours: float, scenario_tree: dict) -> list[dict]:
    """Resolve which scenario to use based on actual dwell time.

    Args:
        actual_dwell_hours: Actual dwell time experienced.
        scenario_tree: Full scenario output from generate_scenarios().

    Returns:
        List of recommendation dicts from the matching scenario.
    """
    # Determine which scenario matches
    if actual_dwell_hours < 1.0:
        scenario_name = "quick"
    elif actual_dwell_hours <= 2.0:
        scenario_name = "normal"
    elif actual_dwell_hours <= 5.0:
        scenario_name = "slow"
    else:
        scenario_name = "detention"

    scenarios = scenario_tree.get("scenarios", {})
    scenario = scenarios.get(scenario_name, {})

    return scenario.get("recommendations", [])
