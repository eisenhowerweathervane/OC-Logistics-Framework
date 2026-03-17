"""Rebuild lane_history table from loads using exponential decay weighting.

Provides:
- rebuild_lane_history(db_path) — recalculate all lane statistics
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

from database import get_db

HALF_LIFE_DAYS = 90


def rebuild_lane_history(db_path: str) -> None:
    """Rebuild the lane_history table from the loads table.

    For each unique lane (origin_city, origin_state, destination_city,
    destination_state), calculates:
    - avg_rate: exponential-decay weighted average of rate_total
    - avg_margin_pct: exponential-decay weighted average of margin_pct
    - load_count: total loads seen
    - booked_count: loads with outcome='booked'
    - trend_direction: 'up', 'down', or 'stable'
    - last_seen: most recent created_at
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with get_db(db_path) as conn:
        # Clear existing lane history before rebuild
        conn.execute("DELETE FROM lane_history")

        # Get all loads with rate_total, grouped by lane
        rows = conn.execute(
            """SELECT origin_city, origin_state, destination_city, destination_state,
                      rate_total, margin_pct, outcome, created_at
               FROM loads
               WHERE rate_total IS NOT NULL
               ORDER BY origin_city, origin_state, destination_city, destination_state"""
        ).fetchall()

        # Group by lane
        lanes: dict[tuple, list[dict]] = {}
        for row in rows:
            key = (row["origin_city"], row["origin_state"],
                   row["destination_city"], row["destination_state"])
            lanes.setdefault(key, []).append(dict(row))

        for lane_key, load_list in lanes.items():
            origin_city, origin_state, dest_city, dest_state = lane_key

            total_weight = 0.0
            weighted_rate = 0.0
            weighted_margin = 0.0
            load_count = len(load_list)
            booked_count = 0
            last_seen = None

            # For trend calculation
            last_30_rates = []
            last_30_weights = []
            prior_60_rates = []
            prior_60_weights = []

            for load in load_list:
                # Parse created_at
                created_str = load.get("created_at")
                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        created = now
                else:
                    created = now

                days_old = max((now - created).total_seconds() / 86400, 0)
                weight = math.pow(0.5, days_old / HALF_LIFE_DAYS)

                rate = load["rate_total"]
                margin = load.get("margin_pct") or 0.0

                total_weight += weight
                weighted_rate += rate * weight
                weighted_margin += margin * weight

                if load.get("outcome") == "booked":
                    booked_count += 1

                if last_seen is None or (created_str and created_str > (last_seen or "")):
                    last_seen = created_str

                # Trend buckets
                if days_old <= 30:
                    last_30_rates.append(rate)
                    last_30_weights.append(weight)
                elif days_old <= 90:
                    prior_60_rates.append(rate)
                    prior_60_weights.append(weight)

            # Calculate weighted averages
            avg_rate = weighted_rate / total_weight if total_weight > 0 else 0
            avg_margin_pct = weighted_margin / total_weight if total_weight > 0 else 0

            # Trend direction
            trend_direction = "stable"
            if last_30_rates and prior_60_rates:
                avg_recent = sum(last_30_rates) / len(last_30_rates)
                avg_prior = sum(prior_60_rates) / len(prior_60_rates)
                if avg_prior > 0:
                    pct_change = (avg_recent - avg_prior) / avg_prior * 100
                    if pct_change > 5:
                        trend_direction = "up"
                    elif pct_change < -5:
                        trend_direction = "down"

            conn.execute(
                """INSERT OR REPLACE INTO lane_history
                   (origin_city, origin_state, destination_city, destination_state,
                    avg_rate, avg_margin_pct, load_count, booked_count,
                    trend_direction, last_seen, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (origin_city, origin_state, dest_city, dest_state,
                 round(avg_rate, 2), round(avg_margin_pct, 2),
                 load_count, booked_count,
                 trend_direction, last_seen, now_iso),
            )

        conn.commit()
