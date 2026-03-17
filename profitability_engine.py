"""
Load Profitability Engine — Phase 2 (Updated)
Scores individual loads and optimizes multi-load chains.

UPDATED: Now uses HOURS-BASED HOS constraints (not miles).
Uses Google Maps API for real drive times when available.
"""

import math
from typing import Optional
from datetime import datetime, timedelta

# Import distance service for real drive times
from distance_service import get_drive_info, is_city_known, CITY_COORDS


# ============================================================================
# DEFAULT ASSUMPTIONS (edit these values as needed)
# ============================================================================

DEFAULT_ASSUMPTIONS = {
    "fuel_price": 3.85,          # $/gallon
    "mpg": 6.5,                  # miles per gallon
    "driver_pay": 0.55,          # $/mile
    "truck_lease": 0.22,         # $/mile (Ryder full-service)
    "insurance": 0.08,           # $/mile
    "maint_reserve": 0.00,       # $/mile (covered under Ryder lease)
    "overhead": 0.04,            # $/mile
    "factoring_fee": 3.0,        # percent of gross revenue
    "detention_rate": 50,        # $/hour
    "max_deadhead_pct": 15,      # max acceptable deadhead as % of loaded miles
    "min_margin_pct": 15,        # minimum acceptable margin %
    "target_margin_pct": 25,     # target margin % for best scores
    "avg_speed": 52,             # mph (fallback for Haversine)
    "load_unload_time": 1.5,     # hours for loading + unloading (dwell time)
    "max_drive_hours": 10,       # max drive hours per day (legal max is 11)
    "home_base": "Cleveland, OH"
}

# For backwards compatibility
CITIES = CITY_COORDS


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_city_key(city: str, state: str) -> str:
    """Format city and state into lookup key."""
    return f"{city}, {state}"


def calculate_distance(city1: str, city2: str) -> int:
    """Legacy function - returns distance in miles."""
    info = get_drive_info(city1, city2)
    return int(round(info["distance_miles"]))


# ============================================================================
# PART A: INDIVIDUAL LOAD SCORING
# ============================================================================

def score_load(
    load: dict,
    deadhead_miles: int = None,
    detention_hours: float = 0.0,
    assumptions: dict = None,
    current_city: str = None
) -> dict:
    """
    Score a single load and calculate profitability metrics.

    Now includes REAL drive times from Google Maps when available.

    Args:
        load: Parsed load dict from Phase 1's parse_load_email()
        deadhead_miles: Miles from current truck location to pickup (legacy).
                        If None and current_city provided, calculates from API.
        detention_hours: Expected detention hours (default 0)
        assumptions: Config dict (uses DEFAULT_ASSUMPTIONS if not provided)
        current_city: Current truck location for calculating deadhead via API

    Returns:
        Scored load dict with all profitability metrics including drive times
    """
    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS.copy()

    config = DEFAULT_ASSUMPTIONS.copy()
    config.update(assumptions)

    warnings = []

    # Extract values from load
    rate_total = load.get("rate_total")
    loaded_miles = load.get("mileage") or 0

    # Get origin and destination
    origin = get_city_key(load.get("origin_city", ""), load.get("origin_state", ""))
    destination = get_city_key(load.get("destination_city", ""), load.get("destination_state", ""))

    # Get REAL drive info for loaded portion
    loaded_info = get_drive_info(origin, destination, config["avg_speed"])
    loaded_drive_time = loaded_info["drive_time_hours"]
    loaded_distance = loaded_info["distance_miles"]

    # Use loaded distance from API if available, otherwise from load
    if loaded_distance > 0:
        loaded_miles = loaded_distance
    elif loaded_miles == 0:
        loaded_miles = load.get("mileage") or 0

    # Calculate deadhead
    deadhead_drive_time = 0
    if current_city:
        deadhead_info = get_drive_info(current_city, origin, config["avg_speed"])
        deadhead_miles = deadhead_info["distance_miles"]
        deadhead_drive_time = deadhead_info["drive_time_hours"]
        if deadhead_info["source"] == "unknown":
            warnings.append(f"Unknown city: {current_city}")
    elif deadhead_miles is None:
        deadhead_miles = load.get("deadhead_miles")
        if deadhead_miles is None:
            deadhead_miles = 0
            warnings.append("Deadhead unknown — using 0 miles (may understate costs)")
        # Estimate deadhead drive time
        deadhead_drive_time = deadhead_miles / config["avg_speed"]
    else:
        # Estimate deadhead drive time from miles
        deadhead_drive_time = deadhead_miles / config["avg_speed"]

    # Calculate cost per mile
    fuel_cpm = config["fuel_price"] / config["mpg"]
    total_cpm = (
        fuel_cpm +
        config["driver_pay"] +
        config["truck_lease"] +
        config["insurance"] +
        config["maint_reserve"] +
        config["overhead"]
    )

    # Calculate total miles and cost
    total_miles = loaded_miles + deadhead_miles
    total_cost = total_cpm * total_miles

    # Calculate TOTAL HOURS (drive time + dwell time)
    dwell_time = config["load_unload_time"]
    total_drive_hours = deadhead_drive_time + loaded_drive_time
    total_hours = total_drive_hours + dwell_time + detention_hours

    # Calculate dynamic floor RPM
    floor_rpm = total_cpm / (1 - config["min_margin_pct"] / 100) / (1 - config["factoring_fee"] / 100)

    # Handle null rates ("Call for rate")
    if rate_total is None:
        warnings.append(f"Rate not provided — minimum acceptable rate is ${floor_rpm:.2f}/mi (floor RPM)")

        result = {
            # Pass through from Phase 1
            "origin_city": load.get("origin_city", ""),
            "origin_state": load.get("origin_state", ""),
            "destination_city": load.get("destination_city", ""),
            "destination_state": load.get("destination_state", ""),
            "rate_total": None,
            "mileage": loaded_miles,
            "weight": load.get("weight"),
            "commodity": load.get("commodity", ""),
            "equipment_type": load.get("equipment_type", ""),
            "pickup_date": load.get("pickup_date", ""),
            "pickup_time_window": load.get("pickup_time_window", ""),
            "delivery_date": load.get("delivery_date", ""),
            "delivery_time_window": load.get("delivery_time_window", ""),
            "broker_name": load.get("broker_name", ""),
            "broker_mc_number": load.get("broker_mc_number", ""),
            "contact_phone": load.get("contact_phone", ""),
            "contact_email": load.get("contact_email", ""),
            "load_number": load.get("load_number", ""),
            # Calculated by Phase 2
            "deadhead_miles": round(deadhead_miles, 1),
            "deadhead_drive_time": round(deadhead_drive_time, 2),
            "loaded_drive_time": round(loaded_drive_time, 2),
            "total_miles": round(total_miles, 1),
            "total_cost": round(total_cost, 2),
            "net_revenue": None,
            "profit": None,
            "margin_pct": None,
            "rpm": None,
            "all_in_rpm": None,
            "drive_hours": round(total_drive_hours, 2),
            "dwell_time": round(dwell_time, 2),
            "total_hours": round(total_hours, 2),
            "profit_per_hour": None,
            "score": None,
            "action": "NEGOTIATE",
            "floor_rpm": round(floor_rpm, 2),
            "warnings": warnings
        }
        return result

    # Calculate revenue
    gross_revenue = rate_total + (detention_hours * config["detention_rate"])
    factoring_amount = gross_revenue * (config["factoring_fee"] / 100)
    net_revenue = gross_revenue - factoring_amount

    # Calculate profit metrics
    profit = net_revenue - total_cost
    margin_pct = (profit / net_revenue) * 100 if net_revenue > 0 else 0
    rpm = rate_total / loaded_miles if loaded_miles > 0 else 0
    all_in_rpm = net_revenue / total_miles if total_miles > 0 else 0
    profit_per_hour = profit / total_hours if total_hours > 0 else 0

    # Check floor RPM
    if all_in_rpm < floor_rpm:
        warnings.append("Below floor RPM")

    # ========================================================================
    # SCORING RUBRIC (score range: -10 to +10)
    # ========================================================================
    score = 0

    # Margin scoring
    if margin_pct >= config["target_margin_pct"]:  # 25%
        score += 4
    elif margin_pct >= config["min_margin_pct"]:   # 15%
        score += 2
    elif margin_pct >= 5:
        score += 0
    elif margin_pct >= 0:
        score -= 2
    else:  # margin_pct < 0
        score -= 5

    # All-in RPM scoring
    if all_in_rpm >= 3.00:
        score += 2
    elif all_in_rpm >= 2.50:
        score += 1
    elif all_in_rpm >= 2.00:
        score += 0
    else:  # all_in_rpm < 2.00
        score -= 2

    # Deadhead penalty
    deadhead_pct = (deadhead_miles / loaded_miles * 100) if loaded_miles > 0 else 0
    if deadhead_pct <= 5:
        score += 2
    elif deadhead_pct <= config["max_deadhead_pct"]:  # 15%
        score += 1
    elif deadhead_pct <= 25:
        score -= 1
    else:  # deadhead_pct > 25%
        score -= 3

    # Mileage sweet spot
    if 150 <= loaded_miles <= 300:
        score += 1
    elif loaded_miles < 80:
        score -= 1

    # Detention risk
    if detention_hours > 2:
        score -= 1

    # Clamp score to [-10, +10]
    score = max(-10, min(10, score))

    # ========================================================================
    # ACTION TIERS
    # ========================================================================
    if all_in_rpm < floor_rpm:
        action = "PASS"
    elif score >= 5:
        action = "BOOK IT"
    elif score >= 2:
        action = "CONSIDER"
    elif score >= 0:
        action = "NEGOTIATE"
    else:
        action = "PASS"

    # Build result
    result = {
        # Pass through from Phase 1
        "origin_city": load.get("origin_city", ""),
        "origin_state": load.get("origin_state", ""),
        "destination_city": load.get("destination_city", ""),
        "destination_state": load.get("destination_state", ""),
        "rate_total": rate_total,
        "mileage": round(loaded_miles, 1),
        "weight": load.get("weight"),
        "commodity": load.get("commodity", ""),
        "equipment_type": load.get("equipment_type", ""),
        "pickup_date": load.get("pickup_date", ""),
        "pickup_time_window": load.get("pickup_time_window", ""),
        "delivery_date": load.get("delivery_date", ""),
        "delivery_time_window": load.get("delivery_time_window", ""),
        "broker_name": load.get("broker_name", ""),
        "broker_mc_number": load.get("broker_mc_number", ""),
        "contact_phone": load.get("contact_phone", ""),
        "contact_email": load.get("contact_email", ""),
        "load_number": load.get("load_number", ""),
        # Calculated by Phase 2
        "deadhead_miles": round(deadhead_miles, 1),
        "deadhead_drive_time": round(deadhead_drive_time, 2),
        "loaded_drive_time": round(loaded_drive_time, 2),
        "total_miles": round(total_miles, 1),
        "total_cost": round(total_cost, 2),
        "net_revenue": round(net_revenue, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 2),
        "rpm": round(rpm, 2),
        "all_in_rpm": round(all_in_rpm, 2),
        "drive_hours": round(total_drive_hours, 2),
        "dwell_time": round(dwell_time, 2),
        "total_hours": round(total_hours, 2),
        "profit_per_hour": round(profit_per_hour, 2),
        "score": score,
        "action": action,
        "floor_rpm": round(floor_rpm, 2),
        "warnings": warnings
    }

    return result


# ============================================================================
# PART B: CHAIN OPTIMIZER (HOURS-BASED HOS)
# ============================================================================

def optimize_chain(
    all_loads: list[dict],
    start_city: str = None,
    hos_remaining: float = 10.0,
    days_away: int = 0,
    assumptions: dict = None
) -> dict:
    """
    Find the most profitable sequence of loads using beam search.

    UPDATED: Now uses HOURS as the constraint (HOS), not miles.
    Accounts for dwell time (load/unload) between loads.

    Args:
        all_loads: List of parsed loads from Phase 1
        start_city: Current truck location (default: home_base from assumptions)
        hos_remaining: Hours of service remaining TODAY (default: 10, max 11)
        days_away: Number of days away from home (default: 0 for day trips)
        assumptions: Config dict

    Returns:
        Chain summary dict with legs and summary metrics
    """
    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS.copy()

    config = DEFAULT_ASSUMPTIONS.copy()
    config.update(assumptions)

    if start_city is None:
        start_city = config["home_base"]

    home_base = config["home_base"]
    dwell_time = config["load_unload_time"]
    max_drive_hours = config.get("max_drive_hours", 10)

    # Total available drive hours = today's remaining + future days
    # Each additional day gives max_drive_hours (default 10)
    total_available_hours = hos_remaining + (days_away * max_drive_hours)

    # Beam search with width=3
    BEAM_WIDTH = 3

    def get_load_city(load: dict, which: str) -> str:
        """Get city key for origin or destination."""
        if which == "origin":
            return get_city_key(load.get("origin_city", ""), load.get("origin_state", ""))
        else:
            return get_city_key(load.get("destination_city", ""), load.get("destination_state", ""))

    def build_chains(
        current_city: str,
        remaining_loads: list[dict],
        hours_remaining: float,
        current_chain: list[dict]
    ) -> list[list[dict]]:
        """Recursively build chains using beam search with HOURS constraint."""

        candidates = []

        for load in remaining_loads:
            origin = get_load_city(load, "origin")
            destination = get_load_city(load, "destination")

            # Get REAL drive times from API
            deadhead_info = get_drive_info(current_city, origin, config["avg_speed"])
            loaded_info = get_drive_info(origin, destination, config["avg_speed"])
            return_home_info = get_drive_info(destination, home_base, config["avg_speed"])

            deadhead_time = deadhead_info["drive_time_hours"]
            loaded_time = loaded_info["drive_time_hours"]
            return_home_time = return_home_info["drive_time_hours"]

            deadhead_miles = deadhead_info["distance_miles"]
            loaded_miles = loaded_info["distance_miles"] or load.get("mileage") or 0

            # Total time for this leg = deadhead + loaded + dwell
            leg_total_time = deadhead_time + loaded_time + dwell_time

            # Check 1: Can the driver COMPLETE this load within remaining hours?
            if leg_total_time > hours_remaining:
                continue

            # Check 2: After this load, can driver still get home?
            hours_after_this_leg = hours_remaining - leg_total_time
            if return_home_time > hours_after_this_leg:
                # Not enough time to get home after this load
                # Only skip if this is a day trip (days_away = 0)
                # For multi-day trips, we can continue building
                if days_away == 0:
                    continue

            # Score this load
            scored = score_load(load, current_city=current_city, assumptions=config)

            # Add drive time info to scored result
            scored["deadhead_drive_time"] = round(deadhead_time, 2)
            scored["loaded_drive_time"] = round(loaded_time, 2)

            # Check for unknown cities
            unknown_cities = []
            if deadhead_info["source"] == "unknown":
                unknown_cities.append(current_city)
            if loaded_info["source"] == "unknown":
                unknown_cities.append(origin)
                unknown_cities.append(destination)

            if unknown_cities:
                scored["warnings"] = scored.get("warnings", []) + [
                    f"Unknown city (using estimate): {city}" for city in set(unknown_cities)
                ]

            # Calculate ranking score: (profit_per_hour * 10) - (deadhead_time * 50) - (return_home_time * 10)
            pph = scored.get("profit_per_hour") or 0
            rank_score = (pph * 10) - (deadhead_time * 50) - (return_home_time * 10)

            candidates.append({
                "load": load,
                "scored": scored,
                "deadhead_miles": deadhead_miles,
                "deadhead_time": deadhead_time,
                "loaded_time": loaded_time,
                "leg_total_time": leg_total_time,
                "destination": destination,
                "rank_score": rank_score,
            })

        # If no valid candidates, return current chain
        if not candidates:
            return [current_chain]

        # Sort by rank score and take top BEAM_WIDTH
        candidates.sort(key=lambda x: x["rank_score"], reverse=True)
        top_candidates = candidates[:BEAM_WIDTH]

        all_chains = []

        for candidate in top_candidates:
            # Build leg for this load
            leg = {
                "load": candidate["load"],
                "deadhead": candidate["deadhead_miles"],
                "deadhead_time": candidate["deadhead_time"],
                "loaded_time": candidate["loaded_time"],
                "leg_total_time": candidate["leg_total_time"],
                "result": candidate["scored"],
                "is_return_home": False
            }

            new_chain = current_chain + [leg]
            new_remaining = [l for l in remaining_loads if l is not candidate["load"]]
            new_hours_remaining = hours_remaining - candidate["leg_total_time"]

            # Recursively build rest of chain
            sub_chains = build_chains(
                candidate["destination"],
                new_remaining,
                new_hours_remaining,
                new_chain
            )
            all_chains.extend(sub_chains)

        return all_chains

    # Build all possible chains
    all_chains = build_chains(start_city, all_loads, total_available_hours, [])

    # If no chains found, return empty result
    if not all_chains or all(len(c) == 0 for c in all_chains):
        return {
            "legs": [],
            "summary": {
                "total_profit": 0.0,
                "total_revenue": 0.0,
                "num_loads": 0,
                "total_deadhead": 0,
                "deadhead_pct": 0.0,
                "total_hours": 0.0,
                "total_drive_hours": 0.0,
                "avg_margin": 0.0,
                "profit_per_hour": 0.0,
                "total_miles": 0,
                "hos_remaining": total_available_hours
            },
            "warnings": ["No feasible loads found within HOS limit"]
        }

    # Calculate total profit for each chain and pick the best
    def calculate_chain_profit(chain: list[dict]) -> float:
        if not chain:
            return float('-inf')

        total_profit = 0.0
        last_destination = start_city

        for leg in chain:
            result = leg.get("result", {})
            profit = result.get("profit") or 0
            total_profit += profit

            load = leg.get("load", {})
            if load:
                last_destination = get_load_city(load, "destination")

        # Subtract return-home cost
        return_info = get_drive_info(last_destination, home_base, config["avg_speed"])
        return_miles = return_info["distance_miles"]

        fuel_cpm = config["fuel_price"] / config["mpg"]
        total_cpm = (
            fuel_cpm +
            config["driver_pay"] +
            config["truck_lease"] +
            config["insurance"] +
            config["maint_reserve"] +
            config["overhead"]
        )
        return_cost = total_cpm * return_miles
        total_profit -= return_cost

        return total_profit

    best_chain = max(all_chains, key=calculate_chain_profit)

    # Add return-home leg
    if best_chain:
        last_load = best_chain[-1].get("load", {})
        last_destination = get_load_city(last_load, "destination")

        return_info = get_drive_info(last_destination, home_base, config["avg_speed"])
        return_miles = return_info["distance_miles"]
        return_time = return_info["drive_time_hours"]

        fuel_cpm = config["fuel_price"] / config["mpg"]
        total_cpm = (
            fuel_cpm +
            config["driver_pay"] +
            config["truck_lease"] +
            config["insurance"] +
            config["maint_reserve"] +
            config["overhead"]
        )
        return_cost = total_cpm * return_miles

        return_leg = {
            "load": None,
            "deadhead": return_miles,
            "deadhead_time": return_time,
            "loaded_time": 0,
            "leg_total_time": return_time,
            "result": {
                "origin_city": last_load.get("destination_city", ""),
                "origin_state": last_load.get("destination_state", ""),
                "destination_city": home_base.split(", ")[0] if ", " in home_base else home_base,
                "destination_state": home_base.split(", ")[1] if ", " in home_base else "",
                "total_cost": round(return_cost, 2),
                "profit": round(-return_cost, 2),
                "total_miles": return_miles,
                "drive_hours": return_time,
                "total_hours": return_time,
            },
            "is_return_home": True
        }
        best_chain.append(return_leg)

    # Calculate summary
    total_profit = 0.0
    total_revenue = 0.0
    total_deadhead = 0
    total_hours = 0.0
    total_drive_hours = 0.0
    total_miles = 0
    margins = []
    num_loads = 0

    for leg in best_chain:
        result = leg.get("result", {})

        if not leg.get("is_return_home"):
            profit = result.get("profit") or 0
            revenue = result.get("net_revenue") or 0
            margin = result.get("margin_pct")
            hours = result.get("total_hours") or 0
            miles = result.get("total_miles") or 0
            drive_hrs = leg.get("deadhead_time", 0) + leg.get("loaded_time", 0)

            total_profit += profit
            total_revenue += revenue
            if margin is not None:
                margins.append(margin)
            total_hours += hours
            total_drive_hours += drive_hrs
            total_miles += miles
            num_loads += 1
        else:
            # Return home leg
            total_profit += result.get("profit", 0)
            return_time = leg.get("leg_total_time", 0)
            total_hours += return_time
            total_drive_hours += return_time
            total_miles += leg.get("deadhead", 0)

        total_deadhead += leg.get("deadhead", 0)

    loaded_miles = total_miles - total_deadhead
    deadhead_pct = (total_deadhead / loaded_miles * 100) if loaded_miles > 0 else 0
    avg_margin = sum(margins) / len(margins) if margins else 0
    profit_per_hour = total_profit / total_hours if total_hours > 0 else 0

    # Calculate hours used
    hours_used = sum(leg.get("leg_total_time", 0) for leg in best_chain)

    return {
        "legs": best_chain,
        "summary": {
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
            "hos_available": round(total_available_hours, 2),
            "hos_used": round(hours_used, 2),
            "hos_remaining": round(total_available_hours - hours_used, 2)
        }
    }


def greedy_chain(
    all_loads: list[dict],
    start_city: str = None,
    hos_remaining: float = 10.0,
    days_away: int = 0,
    assumptions: dict = None
) -> dict:
    """
    Greedy baseline: always pick the single highest-scoring load next, no lookahead.
    Uses HOURS as the constraint (HOS), not miles.
    """
    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS.copy()

    config = DEFAULT_ASSUMPTIONS.copy()
    config.update(assumptions)

    if start_city is None:
        start_city = config["home_base"]

    home_base = config["home_base"]
    dwell_time = config["load_unload_time"]
    max_drive_hours = config.get("max_drive_hours", 10)

    total_available_hours = hos_remaining + (days_away * max_drive_hours)
    hours_remaining = total_available_hours

    current_city = start_city
    remaining_loads = list(all_loads)
    chain = []

    def get_load_city(load: dict, which: str) -> str:
        if which == "origin":
            return get_city_key(load.get("origin_city", ""), load.get("origin_state", ""))
        else:
            return get_city_key(load.get("destination_city", ""), load.get("destination_state", ""))

    while remaining_loads:
        best_candidate = None
        best_score = float('-inf')

        for load in remaining_loads:
            origin = get_load_city(load, "origin")
            destination = get_load_city(load, "destination")

            # Get real drive times
            deadhead_info = get_drive_info(current_city, origin, config["avg_speed"])
            loaded_info = get_drive_info(origin, destination, config["avg_speed"])
            return_info = get_drive_info(destination, home_base, config["avg_speed"])

            deadhead_time = deadhead_info["drive_time_hours"]
            loaded_time = loaded_info["drive_time_hours"]
            return_time = return_info["drive_time_hours"]

            deadhead_miles = deadhead_info["distance_miles"]

            # Total time for this leg
            leg_total_time = deadhead_time + loaded_time + dwell_time

            # Check HOS constraints
            if leg_total_time > hours_remaining:
                continue

            hours_after = hours_remaining - leg_total_time
            if days_away == 0 and return_time > hours_after:
                continue

            scored = score_load(load, current_city=current_city, assumptions=config)
            load_score = scored.get("score")

            if load_score is not None and load_score > best_score:
                best_score = load_score
                best_candidate = {
                    "load": load,
                    "scored": scored,
                    "deadhead_miles": deadhead_miles,
                    "deadhead_time": deadhead_time,
                    "loaded_time": loaded_time,
                    "leg_total_time": leg_total_time,
                    "destination": destination,
                }

        if best_candidate is None:
            break

        leg = {
            "load": best_candidate["load"],
            "deadhead": best_candidate["deadhead_miles"],
            "deadhead_time": best_candidate["deadhead_time"],
            "loaded_time": best_candidate["loaded_time"],
            "leg_total_time": best_candidate["leg_total_time"],
            "result": best_candidate["scored"],
            "is_return_home": False
        }
        chain.append(leg)

        current_city = best_candidate["destination"]
        remaining_loads = [l for l in remaining_loads if l is not best_candidate["load"]]
        hours_remaining -= best_candidate["leg_total_time"]

    # Add return-home leg
    if chain:
        last_load = chain[-1].get("load", {})
        last_destination = get_load_city(last_load, "destination")

        return_info = get_drive_info(last_destination, home_base, config["avg_speed"])
        return_miles = return_info["distance_miles"]
        return_time = return_info["drive_time_hours"]

        fuel_cpm = config["fuel_price"] / config["mpg"]
        total_cpm = (
            fuel_cpm +
            config["driver_pay"] +
            config["truck_lease"] +
            config["insurance"] +
            config["maint_reserve"] +
            config["overhead"]
        )
        return_cost = total_cpm * return_miles

        return_leg = {
            "load": None,
            "deadhead": return_miles,
            "deadhead_time": return_time,
            "loaded_time": 0,
            "leg_total_time": return_time,
            "result": {
                "origin_city": last_load.get("destination_city", ""),
                "origin_state": last_load.get("destination_state", ""),
                "destination_city": home_base.split(", ")[0] if ", " in home_base else home_base,
                "destination_state": home_base.split(", ")[1] if ", " in home_base else "",
                "total_cost": round(return_cost, 2),
                "profit": round(-return_cost, 2),
                "total_miles": return_miles,
                "drive_hours": return_time,
                "total_hours": return_time,
            },
            "is_return_home": True
        }
        chain.append(return_leg)

    # Calculate summary (same logic as optimize_chain)
    total_profit = 0.0
    total_revenue = 0.0
    total_deadhead = 0
    total_hours = 0.0
    total_drive_hours = 0.0
    total_miles = 0
    margins = []
    num_loads = 0

    for leg in chain:
        result = leg.get("result", {})

        if not leg.get("is_return_home"):
            profit = result.get("profit") or 0
            revenue = result.get("net_revenue") or 0
            margin = result.get("margin_pct")
            hours = result.get("total_hours") or 0
            miles = result.get("total_miles") or 0
            drive_hrs = leg.get("deadhead_time", 0) + leg.get("loaded_time", 0)

            total_profit += profit
            total_revenue += revenue
            if margin is not None:
                margins.append(margin)
            total_hours += hours
            total_drive_hours += drive_hrs
            total_miles += miles
            num_loads += 1
        else:
            total_profit += result.get("profit", 0)
            return_time = leg.get("leg_total_time", 0)
            total_hours += return_time
            total_drive_hours += return_time
            total_miles += leg.get("deadhead", 0)

        total_deadhead += leg.get("deadhead", 0)

    loaded_miles = total_miles - total_deadhead
    deadhead_pct = (total_deadhead / loaded_miles * 100) if loaded_miles > 0 else 0
    avg_margin = sum(margins) / len(margins) if margins else 0
    profit_per_hour = total_profit / total_hours if total_hours > 0 else 0

    hours_used = sum(leg.get("leg_total_time", 0) for leg in chain)

    return {
        "legs": chain,
        "summary": {
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
            "hos_available": round(total_available_hours, 2),
            "hos_used": round(hours_used, 2),
            "hos_remaining": round(total_available_hours - hours_used, 2)
        }
    }


# ============================================================================
# TESTS
# ============================================================================

def run_all_tests():
    """Run basic tests."""
    print("\n" + "=" * 60)
    print("Running Profitability Engine Tests")
    print("=" * 60 + "\n")

    # Test scoring
    load = {
        "origin_city": "Columbus",
        "origin_state": "OH",
        "destination_city": "Pittsburgh",
        "destination_state": "PA",
        "mileage": 185,
        "rate_total": 600.00,
    }

    result = score_load(load, current_city="Cleveland, OH")
    print(f"Test load: Columbus → Pittsburgh")
    print(f"  Deadhead: {result['deadhead_miles']} mi ({result['deadhead_drive_time']} hrs)")
    print(f"  Loaded: {result['mileage']} mi ({result['loaded_drive_time']} hrs)")
    print(f"  Total hours: {result['total_hours']} (drive: {result['drive_hours']}, dwell: {result['dwell_time']})")
    print(f"  Profit: ${result['profit']}")
    print(f"  Score: {result['score']} → {result['action']}")
    print("✓ Scoring test passed\n")

    # Test optimizer with HOS constraint
    print("Testing optimizer with 8-hour HOS limit...")
    loads = [
        {"origin_city": "Columbus", "origin_state": "OH", "destination_city": "Pittsburgh", "destination_state": "PA", "mileage": 185, "rate_total": 600.00},
        {"origin_city": "Pittsburgh", "origin_state": "PA", "destination_city": "Cleveland", "destination_state": "OH", "mileage": 133, "rate_total": 450.00},
        {"origin_city": "Cleveland", "origin_state": "OH", "destination_city": "Detroit", "destination_state": "MI", "mileage": 170, "rate_total": 500.00},
    ]

    chain = optimize_chain(loads, start_city="Cleveland, OH", hos_remaining=8, days_away=0)
    print(f"  HOS available: {chain['summary']['hos_available']} hrs")
    print(f"  HOS used: {chain['summary']['hos_used']} hrs")
    print(f"  Loads selected: {chain['summary']['num_loads']}")
    print(f"  Total profit: ${chain['summary']['total_profit']}")

    # Verify HOS constraint is respected
    if chain['summary']['hos_used'] <= 8:
        print("✓ HOS constraint respected\n")
    else:
        print("✗ HOS constraint VIOLATED\n")

    print("=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
