"""Duplicate detection for incoming loads.

Checks a ParsedLoad against the database to see if an identical load
already exists, matching on route, date, broker, rate, and mileage.
"""

from dataclasses import dataclass, field
from typing import Optional

from database import get_db, DEFAULT_DB_PATH
from models import ParsedLoad


@dataclass
class DuplicateResult:
    """Result of a duplicate check."""

    is_duplicate: bool
    matching_load_id: Optional[int] = None
    message: str = ""


def check_duplicate(
    load: ParsedLoad,
    db_path: str = DEFAULT_DB_PATH,
) -> DuplicateResult:
    """Check whether *load* already exists in the database.

    Matches on: origin_city, origin_state, destination_city, destination_state,
    pickup_date, broker_name, rate_total, mileage.

    Uses COALESCE so that NULL values in the database are compared correctly
    against empty-string / zero defaults on the incoming load.
    """
    sql = """
        SELECT id FROM loads
        WHERE COALESCE(origin_city, '')      = ?
          AND COALESCE(origin_state, '')     = ?
          AND COALESCE(destination_city, '') = ?
          AND COALESCE(destination_state, '')= ?
          AND COALESCE(pickup_date, '')      = ?
          AND COALESCE(broker_name, '')      = ?
          AND COALESCE(rate_total, 0)        = ?
          AND COALESCE(mileage, 0)           = ?
        LIMIT 1
    """

    with get_db(db_path) as conn:
        row = conn.execute(
            sql,
            (
                load.origin_city,
                load.origin_state,
                load.destination_city,
                load.destination_state,
                load.pickup_date or "",
                load.broker_name or "",
                load.rate_total if load.rate_total is not None else 0,
                load.mileage or 0,
            ),
        ).fetchone()

    if row:
        row_id = row["id"]
        return DuplicateResult(
            is_duplicate=True,
            matching_load_id=row_id,
            message=f"This looks like a duplicate of Load #{row_id}",
        )

    return DuplicateResult(is_duplicate=False)
