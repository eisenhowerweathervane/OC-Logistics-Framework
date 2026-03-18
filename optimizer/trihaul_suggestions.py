"""Trihaul city suggestions based on lane history and demand tiers.

Given a current city (Point B) and home base (Point A), suggests intermediate
cities (Point C) that maximize the chance of finding profitable loads on the
way home. Uses city_demand_tiers for known hubs and lane_history for
historical rate data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database import get_db, DEFAULT_DB_PATH
from distance_service import get_drive_info


@dataclass
class TrihaulSuggestion:
    city: str
    state: str
    tier: int                          # demand tier (1/2/3)
    distance_from_current: float       # B→C miles
    distance_to_home: float            # C→A miles
    direct_home_distance: float        # B→A miles
    extra_miles: float                 # how many more miles vs direct
    extra_miles_pct: float             # extra miles as % of direct
    avg_rate_to_city: Optional[float]  # historical B→C rate if known
    avg_rate_to_home: Optional[float]  # historical C→A rate if known
    score: float                       # composite recommendation score
    reason: str                        # human-readable explanation


def suggest_trihaul_cities(
    current_city: str,
    current_state: str,
    home_city: str,
    home_state: str,
    db_path: str = DEFAULT_DB_PATH,
    max_results: int = 5,
    min_distance_mi: int = 100,
    max_distance_mi: int = 800,
) -> list[TrihaulSuggestion]:
    """Suggest the best Point C cities for a trihaul routing.

    Args:
        current_city: Point B city name (where you just delivered).
        current_state: Point B state abbreviation.
        home_city: Point A city name (home base).
        home_state: Point A state abbreviation.
        db_path: Path to the SQLite database.
        max_results: Maximum number of suggestions to return.
        min_distance_mi: Minimum B→C distance in miles.
        max_distance_mi: Maximum B→C distance in miles.

    Returns:
        List of TrihaulSuggestion sorted by score descending.
    """
    current_full = f"{current_city}, {current_state}"
    home_full = f"{home_city}, {home_state}"

    # 1. Get all cities from demand tiers
    with get_db(db_path) as conn:
        tier_rows = conn.execute(
            "SELECT city, state, tier FROM city_demand_tiers"
        ).fetchall()

        # 2. Get lane history for lookup
        lane_rows = conn.execute(
            "SELECT origin_city, origin_state, destination_city, destination_state, avg_rate "
            "FROM lane_history"
        ).fetchall()

    # Build lane rate lookup: (origin_city, origin_state, dest_city, dest_state) -> avg_rate
    lane_lookup: dict[tuple[str, str, str, str], float] = {}
    for lr in lane_rows:
        lane_lookup[(lr["origin_city"], lr["origin_state"],
                      lr["destination_city"], lr["destination_state"])] = lr["avg_rate"]

    # 3. Get direct home distance (B→A)
    direct_info = get_drive_info(current_full, home_full)
    direct_home_distance = direct_info["distance_miles"]

    suggestions: list[TrihaulSuggestion] = []

    for row in tier_rows:
        cand_city = row["city"]
        cand_state = row["state"]
        cand_tier = row["tier"]

        # Skip current city and home city
        if (cand_city.lower() == current_city.lower()
                and cand_state.upper() == current_state.upper()):
            continue
        if (cand_city.lower() == home_city.lower()
                and cand_state.upper() == home_state.upper()):
            continue

        cand_full = f"{cand_city}, {cand_state}"

        # B→C distance
        bc_info = get_drive_info(current_full, cand_full)
        bc_miles = bc_info["distance_miles"]

        # Distance filter
        if bc_miles < min_distance_mi or bc_miles > max_distance_mi:
            continue

        # C→A distance
        ca_info = get_drive_info(cand_full, home_full)
        ca_miles = ca_info["distance_miles"]

        # Extra miles
        extra_miles = (bc_miles + ca_miles) - direct_home_distance
        extra_miles_pct = (
            round(extra_miles / direct_home_distance * 100, 1)
            if direct_home_distance > 0
            else 0.0
        )

        # Lane history lookup
        avg_rate_bc = lane_lookup.get(
            (current_city, current_state, cand_city, cand_state)
        )
        avg_rate_ca = lane_lookup.get(
            (cand_city, cand_state, home_city, home_state)
        )

        # Scoring
        # Tier score: tier 1 = 30, tier 2 = 20, tier 3 = 10
        tier_score = {1: 30, 2: 20, 3: 10}.get(cand_tier, 5)

        # Lane rate score: bonus if we have historical lane data with good rates
        lane_rate_score = 0.0
        if avg_rate_bc is not None and bc_miles > 0:
            rpm_bc = avg_rate_bc / bc_miles
            lane_rate_score += min(rpm_bc * 5, 15)  # cap at 15
        if avg_rate_ca is not None and ca_miles > 0:
            rpm_ca = avg_rate_ca / ca_miles
            lane_rate_score += min(rpm_ca * 5, 15)  # cap at 15

        # Extra miles penalty: 0.05 per extra mile
        extra_miles_penalty = max(extra_miles, 0) * 0.05

        score = round(tier_score + lane_rate_score - extra_miles_penalty, 2)

        # Build reason string
        reason_parts = [f"Tier {cand_tier} hub"]
        reason_parts.append(
            f"{extra_miles:.0f} mi detour (+{extra_miles_pct:.0f}%)"
        )
        if avg_rate_ca is not None and ca_miles > 0:
            reason_parts.append(
                f"strong C→A lane avg ${avg_rate_ca / ca_miles:.2f}/mi"
            )
        elif avg_rate_bc is not None and bc_miles > 0:
            reason_parts.append(
                f"known B→C lane avg ${avg_rate_bc / bc_miles:.2f}/mi"
            )
        reason = ", ".join(reason_parts)

        suggestions.append(TrihaulSuggestion(
            city=cand_city,
            state=cand_state,
            tier=cand_tier,
            distance_from_current=round(bc_miles, 1),
            distance_to_home=round(ca_miles, 1),
            direct_home_distance=round(direct_home_distance, 1),
            extra_miles=round(extra_miles, 1),
            extra_miles_pct=round(extra_miles_pct, 1),
            avg_rate_to_city=avg_rate_bc,
            avg_rate_to_home=avg_rate_ca,
            score=score,
            reason=reason,
        ))

    # Sort by score descending
    suggestions.sort(key=lambda s: s.score, reverse=True)
    return suggestions[:max_results]
