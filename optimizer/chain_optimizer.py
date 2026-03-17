"""Chain optimizer with full FMCSA HOS, repositioning value, and composite scoring.

Uses beam search to find the most profitable sequence of loads while respecting
Hours of Service regulations. Supports multi-day planning with automatic rest
insertion.
"""

from __future__ import annotations

from typing import Optional

from distance_service import get_drive_info
from profitability_engine import score_load
from optimizer.hos_model import HOSState, can_complete_leg, apply_leg, apply_rest, time_with_break
from scoring.strategic_scorer import score_strategic

BEAM_WIDTH = 5
DEFAULT_DWELL_TIME = 1.5  # hours


def _get_city_key(city: str, state: str) -> str:
    """Format city and state into 'City, ST' key."""
    return f"{city}, {state}"


def _load_origin(load: dict) -> str:
    return _get_city_key(load.get("origin_city", ""), load.get("origin_state", ""))


def _load_destination(load: dict) -> str:
    return _get_city_key(load.get("destination_city", ""), load.get("destination_state", ""))


def _cost_per_mile(assumptions: dict) -> float:
    """Calculate total cost per mile from assumptions."""
    fuel_cpm = assumptions.get("fuel_price", 3.85) / assumptions.get("mpg", 6.5)
    return (
        fuel_cpm
        + assumptions.get("driver_pay", 0.55)
        + assumptions.get("truck_lease", 0.22)
        + assumptions.get("insurance", 0.08)
        + assumptions.get("maint_reserve", 0.00)
        + assumptions.get("overhead", 0.04)
    )


def optimize_chain(
    loads: list[dict],
    start_city: str = "Cleveland, OH",
    hos_state: Optional[HOSState] = None,
    home_base: str = "Cleveland, OH",
    assumptions: Optional[dict] = None,
    db_path: str = "loads.db",
    max_days: int = 1,
) -> dict:
    """Find the most profitable load chain using beam search with full HOS.

    Args:
        loads: List of parsed load dicts.
        start_city: Current truck location.
        hos_state: Current HOS state (default: fresh driver).
        home_base: Driver's home base.
        assumptions: Cost assumptions dict (optional).
        db_path: Database path for scorers.
        max_days: Maximum days to plan (1 = day trip only).

    Returns:
        Dict with 'legs' list and 'summary' dict.
    """
    if hos_state is None:
        hos_state = HOSState()

    if assumptions is None:
        assumptions = {}

    dwell_time = assumptions.get("load_unload_time", DEFAULT_DWELL_TIME)
    avg_speed = assumptions.get("avg_speed", 52.0)
    cpm = _cost_per_mile(assumptions)

    # Empty loads -> empty result
    if not loads:
        return _empty_result(hos_state)

    # Build chains via beam search
    initial_state = _SearchState(
        current_city=start_city,
        hos=hos_state,
        legs=[],
        remaining_load_indices=list(range(len(loads))),
        day=1,
        total_profit=0.0,
    )

    best_chain = _beam_search(
        loads=loads,
        initial=initial_state,
        home_base=home_base,
        assumptions=assumptions,
        db_path=db_path,
        dwell_time=dwell_time,
        avg_speed=avg_speed,
        cpm=cpm,
        max_days=max_days,
    )

    if not best_chain or not best_chain.legs:
        return _empty_result(hos_state)

    # Add return-home leg
    legs = list(best_chain.legs)
    last_city = best_chain.current_city
    return_info = get_drive_info(last_city, home_base, avg_speed)
    return_miles = return_info["distance_miles"]
    return_time = return_info["drive_time_hours"]
    return_cost = cpm * return_miles

    # Parse home base for city/state
    if ", " in home_base:
        hb_city, hb_state = home_base.rsplit(", ", 1)
    else:
        hb_city, hb_state = home_base, ""

    # Parse last destination for return origin
    last_leg = legs[-1]
    last_load = last_leg.get("load", {}) or {}
    ret_origin_city = last_load.get("destination_city", "")
    ret_origin_state = last_load.get("destination_state", "")

    return_leg = {
        "load": None,
        "deadhead": return_miles,
        "deadhead_time": return_time,
        "loaded_time": 0,
        "leg_total_time": return_time,
        "result": {
            "origin_city": ret_origin_city,
            "origin_state": ret_origin_state,
            "destination_city": hb_city,
            "destination_state": hb_state,
            "total_cost": round(return_cost, 2),
            "profit": round(-return_cost, 2),
            "total_miles": return_miles,
            "drive_hours": return_time,
            "total_hours": return_time,
        },
        "is_return_home": True,
        "day": best_chain.day,
    }
    legs.append(return_leg)

    # Build summary
    summary = _build_summary(legs, return_cost, best_chain.hos, best_chain.day)
    return {"legs": legs, "summary": summary}


# ---------------------------------------------------------------------------
# Internal search state
# ---------------------------------------------------------------------------

class _SearchState:
    """Mutable state carried through beam search."""

    __slots__ = (
        "current_city", "hos", "legs", "remaining_load_indices",
        "day", "total_profit",
    )

    def __init__(self, current_city, hos, legs, remaining_load_indices, day, total_profit):
        self.current_city = current_city
        self.hos = hos
        self.legs = legs
        self.remaining_load_indices = remaining_load_indices
        self.day = day
        self.total_profit = total_profit

    def copy(self):
        return _SearchState(
            current_city=self.current_city,
            hos=self.hos,
            legs=list(self.legs),
            remaining_load_indices=list(self.remaining_load_indices),
            day=self.day,
            total_profit=self.total_profit,
        )


# ---------------------------------------------------------------------------
# Beam search
# ---------------------------------------------------------------------------

def _beam_search(
    loads, initial, home_base, assumptions, db_path,
    dwell_time, avg_speed, cpm, max_days,
):
    """Run beam search and return the best _SearchState (or None)."""

    def _net_profit(state: _SearchState) -> float:
        """Total profit minus return-home cost."""
        ret = get_drive_info(state.current_city, home_base, avg_speed)
        return state.total_profit - cpm * ret["distance_miles"]

    # Expand one level from each state in the beam
    def _expand(states: list[_SearchState]) -> list[_SearchState]:
        all_next = []
        for state in states:
            candidates = _find_candidates(
                loads, state, home_base, assumptions, db_path,
                dwell_time, avg_speed, cpm, max_days,
            )
            if not candidates:
                # Terminal state — keep it as-is
                all_next.append(state)
                continue
            # Take top BEAM_WIDTH candidates per state
            candidates.sort(key=lambda c: c[0], reverse=True)
            for rank_score, new_state in candidates[:BEAM_WIDTH]:
                all_next.append(new_state)
        return all_next

    beam = [initial]
    seen_terminal = []

    for _ in range(len(loads) * max_days + 1):  # upper bound on iterations
        next_beam = _expand(beam)

        # Separate terminal (unchanged) from expanded states
        new_active = []
        for s in next_beam:
            # A state is terminal if it was already in beam and didn't grow
            is_terminal = any(s is b for b in beam) and s in beam
            if is_terminal:
                seen_terminal.append(s)
            else:
                new_active.append(s)

        if not new_active:
            # All states are terminal
            seen_terminal.extend(beam)
            break

        # Keep top BEAM_WIDTH active states
        new_active.sort(key=_net_profit, reverse=True)
        beam = new_active[:BEAM_WIDTH]

        # Also accumulate any beam members that didn't expand
        for s in beam:
            pass  # they'll either expand next round or become terminal

    # Combine all terminal + remaining active states
    all_candidates = seen_terminal + beam
    if not all_candidates:
        return None

    # Deduplicate (by identity)
    seen_ids = set()
    unique = []
    for s in all_candidates:
        if id(s) not in seen_ids:
            seen_ids.add(id(s))
            unique.append(s)

    # Pick best by net profit
    best = max(unique, key=_net_profit)
    return best if best.legs else None


def _find_candidates(
    loads, state, home_base, assumptions, db_path,
    dwell_time, avg_speed, cpm, max_days,
):
    """Find all valid next-load candidates from the current state.

    Returns list of (rank_score, new_SearchState) tuples.
    """
    candidates = []
    is_day_trip = (max_days == 1)

    for idx in state.remaining_load_indices:
        load = loads[idx]
        origin = _load_origin(load)
        destination = _load_destination(load)

        # Drive info
        dh_info = get_drive_info(state.current_city, origin, avg_speed)
        loaded_info = get_drive_info(origin, destination, avg_speed)

        deadhead_time = dh_info["drive_time_hours"]
        loaded_time = loaded_info["drive_time_hours"]
        deadhead_miles = dh_info["distance_miles"]

        total_drive = deadhead_time + loaded_time
        on_duty_time = total_drive + dwell_time

        # HOS check using time_with_break for total on-duty including break
        total_on_duty = time_with_break(state.hos, total_drive, dwell_time)

        if not can_complete_leg(state.hos, total_drive, on_duty_time):
            # If multi-day and we haven't exceeded max_days, try inserting rest
            if not is_day_trip and state.day < max_days:
                rested_hos = apply_rest(state.hos)
                new_day = state.day + 1
                if can_complete_leg(rested_hos, total_drive, on_duty_time):
                    candidate = _build_candidate_after_rest(
                        load, idx, state, rested_hos, new_day,
                        dh_info, loaded_info, dwell_time, avg_speed,
                        cpm, home_base, assumptions, db_path, is_day_trip,
                    )
                    if candidate is not None:
                        candidates.append(candidate)
            continue

        # For day trips: check that driver can return home after this load
        if is_day_trip:
            return_info = get_drive_info(destination, home_base, avg_speed)
            return_time = return_info["drive_time_hours"]
            # After completing this leg, check remaining HOS
            new_hos_after = apply_leg(state.hos, total_drive, on_duty_time)
            # Return home only needs drive time check
            if return_time > new_hos_after.drive_hours_remaining:
                continue

        # Score the load
        scored = score_load(
            load,
            deadhead_miles=deadhead_miles,
            current_city=state.current_city,
            assumptions=assumptions,
        )

        profit = scored.get("profit") or 0
        profit_per_hour = scored.get("profit_per_hour") or 0

        # Strategic score for repositioning value
        dest_city = load.get("destination_city", "")
        dest_state = load.get("destination_state", "")
        try:
            strat = score_strategic(dest_city, dest_state, home_base, db_path)
            strategic_score = strat.score
        except Exception:
            strategic_score = 0.4

        # Return home time for ranking
        ret_info = get_drive_info(destination, home_base, avg_speed)
        return_home_time = ret_info["drive_time_hours"]

        # Ranking formula
        rank = (
            profit_per_hour * 10
            - deadhead_time * 50
            + strategic_score * 30
            - return_home_time * 10
        )

        # Build new search state
        new_hos = apply_leg(state.hos, total_drive, on_duty_time)
        new_state = state.copy()
        new_state.current_city = destination
        new_state.hos = new_hos
        new_state.remaining_load_indices = [
            i for i in state.remaining_load_indices if i != idx
        ]
        new_state.total_profit += profit

        leg = {
            "load": load,
            "deadhead": deadhead_miles,
            "deadhead_time": deadhead_time,
            "loaded_time": loaded_time,
            "leg_total_time": total_on_duty,
            "result": scored,
            "is_return_home": False,
            "day": state.day,
        }
        new_state.legs = list(state.legs) + [leg]

        candidates.append((rank, new_state))

    return candidates


def _build_candidate_after_rest(
    load, idx, state, rested_hos, new_day,
    dh_info, loaded_info, dwell_time, avg_speed,
    cpm, home_base, assumptions, db_path, is_day_trip,
):
    """Build a candidate that includes a rest period before the load."""
    origin = _load_origin(load)
    destination = _load_destination(load)

    deadhead_time = dh_info["drive_time_hours"]
    loaded_time = loaded_info["drive_time_hours"]
    deadhead_miles = dh_info["distance_miles"]
    total_drive = deadhead_time + loaded_time
    on_duty_time = total_drive + dwell_time
    total_on_duty = time_with_break(rested_hos, total_drive, dwell_time)

    # Score load
    scored = score_load(
        load,
        deadhead_miles=deadhead_miles,
        current_city=state.current_city,
        assumptions=assumptions,
    )

    profit = scored.get("profit") or 0
    profit_per_hour = scored.get("profit_per_hour") or 0

    # Strategic score
    dest_city = load.get("destination_city", "")
    dest_state = load.get("destination_state", "")
    try:
        strat = score_strategic(dest_city, dest_state, home_base, db_path)
        strategic_score = strat.score
    except Exception:
        strategic_score = 0.4

    ret_info = get_drive_info(destination, home_base, avg_speed)
    return_home_time = ret_info["drive_time_hours"]

    rank = (
        profit_per_hour * 10
        - deadhead_time * 50
        + strategic_score * 30
        - return_home_time * 10
    )

    new_hos = apply_leg(rested_hos, total_drive, on_duty_time)
    new_state = state.copy()
    new_state.current_city = destination
    new_state.hos = new_hos
    new_state.day = new_day
    new_state.remaining_load_indices = [
        i for i in state.remaining_load_indices if i != idx
    ]
    new_state.total_profit += profit

    leg = {
        "load": load,
        "deadhead": deadhead_miles,
        "deadhead_time": deadhead_time,
        "loaded_time": loaded_time,
        "leg_total_time": total_on_duty,
        "result": scored,
        "is_return_home": False,
        "day": new_day,
    }
    new_state.legs = list(state.legs) + [leg]

    return (rank, new_state)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_result(hos_state: HOSState) -> dict:
    return {
        "legs": [],
        "summary": {
            "total_profit": 0,
            "total_revenue": 0,
            "num_loads": 0,
            "total_deadhead": 0,
            "deadhead_pct": 0.0,
            "total_hours": 0.0,
            "total_drive_hours": 0.0,
            "avg_margin": 0.0,
            "profit_per_hour": 0.0,
            "total_miles": 0,
            "hos_state": _hos_to_dict(hos_state),
            "days": 0,
        },
    }


def _hos_to_dict(hos: HOSState) -> dict:
    return {
        "drive_hours_remaining": hos.drive_hours_remaining,
        "duty_hours_remaining": hos.duty_hours_remaining,
        "weekly_hours_remaining": hos.weekly_hours_remaining,
        "consecutive_drive_hours": hos.consecutive_drive_hours,
        "needs_break": hos.needs_break,
        "needs_rest": hos.needs_rest,
    }


def _build_summary(legs: list[dict], return_cost: float, final_hos: HOSState, total_days: int) -> dict:
    """Build summary dict from completed chain legs."""
    total_profit = 0.0
    total_revenue = 0.0
    total_deadhead = 0.0
    total_hours = 0.0
    total_drive_hours = 0.0
    total_miles = 0.0
    margins = []
    num_loads = 0

    for leg in legs:
        result = leg.get("result", {})
        if not leg.get("is_return_home"):
            profit = result.get("profit") or 0
            revenue = result.get("net_revenue") or 0
            margin = result.get("margin_pct")
            miles = result.get("total_miles") or 0
            drive_hrs = leg.get("deadhead_time", 0) + leg.get("loaded_time", 0)

            total_profit += profit
            total_revenue += revenue
            if margin is not None:
                margins.append(margin)
            total_hours += leg.get("leg_total_time", 0)
            total_drive_hours += drive_hrs
            total_miles += miles
            num_loads += 1
        else:
            total_profit += result.get("profit", 0)
            return_time = leg.get("leg_total_time", 0)
            total_hours += return_time
            total_drive_hours += return_time
            total_miles += leg.get("deadhead", 0)

        total_deadhead += leg.get("deadhead", 0) if not leg.get("is_return_home") else 0
    # Add return deadhead
    return_legs = [l for l in legs if l.get("is_return_home")]
    for rl in return_legs:
        total_deadhead += rl.get("deadhead", 0)

    loaded_miles = total_miles - total_deadhead
    deadhead_pct = (total_deadhead / loaded_miles * 100) if loaded_miles > 0 else 0
    avg_margin = sum(margins) / len(margins) if margins else 0
    profit_per_hour = total_profit / total_hours if total_hours > 0 else 0

    return {
        "total_profit": round(total_profit, 2),
        "total_revenue": round(total_revenue, 2),
        "num_loads": num_loads,
        "total_deadhead": round(total_deadhead, 1),
        "deadhead_pct": round(deadhead_pct, 2),
        "total_hours": round(total_hours, 2),
        "total_drive_hours": round(total_drive_hours, 2),
        "avg_margin": round(avg_margin, 2),
        "profit_per_hour": round(profit_per_hour, 2),
        "total_miles": round(total_miles, 1),
        "hos_state": _hos_to_dict(final_hos),
        "days": total_days,
    }
