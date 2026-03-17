"""Strategic scorer — scores a load based on destination demand and proximity to home.

Looks up the destination in city_demand_tiers and applies a home-proximity
bonus/penalty based on whether the destination is in the home state.
"""

from dataclasses import dataclass, field
from typing import Optional

from database import get_db, init_db, DEFAULT_DB_PATH

_TIER_SCORES = {
    1: 0.8,
    2: 0.5,
    3: 0.3,
}
_DEFAULT_TIER_SCORE = 0.4


@dataclass
class StrategicScore:
    """Result of strategic scoring for a single load.

    Attributes:
        score: Normalized score from 0.0 to 1.0.
        destination_tier: Demand tier (1/2/3) or None if unknown.
        home_distance_factor: Adjustment applied for home proximity.
        detail: Additional context dict.
    """
    score: float
    destination_tier: Optional[int]
    home_distance_factor: float
    detail: dict = field(default_factory=dict)


def score_strategic(
    dest_city: str,
    dest_state: str,
    home_base: str = "Cleveland, OH",
    db_path: str = DEFAULT_DB_PATH,
) -> StrategicScore:
    """Score a load based on destination demand tier and home proximity.

    Args:
        dest_city: Destination city name.
        dest_state: Destination state abbreviation.
        home_base: Home base in "City, ST" format (default "Cleveland, OH").
        db_path: Path to the SQLite database.

    Returns:
        StrategicScore with normalized score, tier info, and proximity factor.
    """
    # Parse home state from home_base
    home_state = _parse_state(home_base)

    # Look up destination tier
    tier = None
    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT tier FROM city_demand_tiers
               WHERE city = ? AND state = ?""",
            (dest_city, dest_state),
        ).fetchone()
        if row:
            tier = row["tier"]

    base_score = _TIER_SCORES.get(tier, _DEFAULT_TIER_SCORE) if tier else _DEFAULT_TIER_SCORE

    # Home proximity adjustment
    home_distance_factor = 0.0
    if home_state and dest_state == home_state:
        home_distance_factor = 0.05

    score = base_score + home_distance_factor
    score = max(0.0, min(1.0, score))

    detail = {
        "dest_city": dest_city,
        "dest_state": dest_state,
        "home_base": home_base,
        "tier_base_score": base_score,
    }

    return StrategicScore(
        score=score,
        destination_tier=tier,
        home_distance_factor=home_distance_factor,
        detail=detail,
    )


def _parse_state(home_base: str) -> Optional[str]:
    """Extract state abbreviation from 'City, ST' format."""
    if "," not in home_base:
        return None
    parts = home_base.rsplit(",", 1)
    return parts[1].strip() if len(parts) == 2 else None
