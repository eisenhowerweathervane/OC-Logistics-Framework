"""Lane scorer — scores a load based on historical lane rate data.

Compares the offered rate against historical averages at city-to-city level,
falling back to state-to-state aggregation when city-level data is sparse.
"""

from dataclasses import dataclass
from typing import Optional

from database import get_db, init_db, DEFAULT_DB_PATH


@dataclass
class LaneScore:
    """Result of lane-based scoring for a single load.

    Attributes:
        score: Normalized score from 0.0 to 1.0.
        data_points: Number of historical loads used for comparison.
        avg_rate: Historical average rate for the lane (None if no data).
        vs_average_pct: Percentage above/below the lane average (None if no data).
        level: Granularity of the match — "city", "state", or "none".
    """
    score: float
    data_points: int
    avg_rate: Optional[float]
    vs_average_pct: Optional[float]
    level: str


def score_lane(
    origin_city: str,
    origin_state: str,
    dest_city: str,
    dest_state: str,
    rate_total: Optional[float],
    db_path: str = DEFAULT_DB_PATH,
) -> LaneScore:
    """Score a load by comparing its rate to historical lane averages.

    Args:
        origin_city: Origin city name.
        origin_state: Origin state abbreviation.
        dest_city: Destination city name.
        dest_state: Destination state abbreviation.
        rate_total: Offered rate in dollars (None if unknown).
        db_path: Path to the SQLite database.

    Returns:
        LaneScore with normalized score, data context, and match level.
    """
    if rate_total is None:
        return LaneScore(
            score=0.5,
            data_points=0,
            avg_rate=None,
            vs_average_pct=None,
            level="none",
        )

    with get_db(db_path) as conn:
        # --- Try city-to-city lookup ---
        row = conn.execute(
            """SELECT avg_rate, load_count
               FROM lane_history
               WHERE origin_city = ? AND origin_state = ?
                 AND destination_city = ? AND destination_state = ?""",
            (origin_city, origin_state, dest_city, dest_state),
        ).fetchone()

        if row and row["load_count"] >= 3:
            return _compute_score(
                rate_total,
                avg_rate=row["avg_rate"],
                data_points=row["load_count"],
                level="city",
            )

        # --- Fall back to state-to-state ---
        agg = conn.execute(
            """SELECT AVG(avg_rate) AS avg_rate, SUM(load_count) AS total_loads
               FROM lane_history
               WHERE origin_state = ? AND destination_state = ?""",
            (origin_state, dest_state),
        ).fetchone()

        if agg and agg["total_loads"] and agg["total_loads"] >= 3:
            return _compute_score(
                rate_total,
                avg_rate=agg["avg_rate"],
                data_points=int(agg["total_loads"]),
                level="state",
            )

    # --- No usable data ---
    return LaneScore(
        score=0.5,
        data_points=0,
        avg_rate=None,
        vs_average_pct=None,
        level="none",
    )


def _compute_score(
    rate_total: float,
    avg_rate: float,
    data_points: int,
    level: str,
) -> LaneScore:
    """Compute a lane score given a rate and its historical average."""
    if avg_rate is None or avg_rate == 0:
        return LaneScore(
            score=0.5,
            data_points=data_points,
            avg_rate=avg_rate,
            vs_average_pct=None,
            level=level,
        )

    vs_average_pct = ((rate_total - avg_rate) / avg_rate) * 100.0
    score = 0.5 + (vs_average_pct / 100.0) * 1.5
    score = max(0.0, min(1.0, score))

    return LaneScore(
        score=score,
        data_points=data_points,
        avg_rate=avg_rate,
        vs_average_pct=vs_average_pct,
        level=level,
    )
