"""Broker scorer — scores a load based on the broker's historical reliability.

Looks up the broker in broker_history and maps their reliability grade
to a normalized 0-1 score, enriched with operational detail metrics.
"""

from dataclasses import dataclass, field
from typing import Optional

from database import get_db, init_db, DEFAULT_DB_PATH

_GRADE_SCORES = {
    "A": 0.9,
    "B": 0.7,
    "C": 0.5,
    "D": 0.3,
    "F": 0.1,
    "U": 0.5,
}


@dataclass
class BrokerScore:
    """Result of broker reliability scoring.

    Attributes:
        score: Normalized score from 0.0 to 1.0.
        grade: Letter grade (A/B/C/D/F/U).
        loads_completed: Number of loads completed with this broker.
        detail: Operational metrics dict.
    """
    score: float
    grade: str
    loads_completed: int
    detail: dict = field(default_factory=dict)


def score_broker(
    broker_name: Optional[str],
    db_path: str = DEFAULT_DB_PATH,
) -> BrokerScore:
    """Score a broker based on their historical reliability.

    Args:
        broker_name: Name of the broker (None or empty → neutral).
        db_path: Path to the SQLite database.

    Returns:
        BrokerScore with normalized score, letter grade, and detail metrics.
    """
    if not broker_name or not broker_name.strip():
        return BrokerScore(score=0.5, grade="U", loads_completed=0, detail={})

    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT reliability_grade, loads_completed,
                      avg_detention_hours, tonu_count,
                      rate_accuracy_pct, ontime_pickup_pct
               FROM broker_history
               WHERE broker_name = ?""",
            (broker_name,),
        ).fetchone()

    if not row:
        return BrokerScore(score=0.5, grade="U", loads_completed=0, detail={})

    grade = row["reliability_grade"] or "U"
    score = _GRADE_SCORES.get(grade, 0.5)

    detail = {
        "avg_detention_hours": row["avg_detention_hours"],
        "tonu_count": row["tonu_count"],
        "rate_accuracy_pct": row["rate_accuracy_pct"],
        "ontime_pickup_pct": row["ontime_pickup_pct"],
    }

    return BrokerScore(
        score=score,
        grade=grade,
        loads_completed=row["loads_completed"] or 0,
        detail=detail,
    )
