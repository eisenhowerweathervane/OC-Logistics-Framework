"""Rebuild broker_history table from loads and load_feedback.

Provides:
- rebuild_broker_history(db_path) — recalculate all broker statistics and grades
"""

from __future__ import annotations

from datetime import datetime, timezone

from database import get_db


def _calculate_grade(
    avg_detention: float,
    ontime_pct: float,
    tonu_count: int,
    has_feedback: bool,
) -> str:
    """Calculate reliability grade from broker metrics.

    Grades:
        A: detention < 1hr AND ontime > 90% AND tonu = 0
        B: detention < 2hr AND ontime > 80%
        C: detention < 3hr AND ontime > 60%
        D: detention < 5hr OR ontime > 40%
        F: everything else
        U: no feedback data
    """
    if not has_feedback:
        return "U"

    if avg_detention < 1 and ontime_pct > 90 and tonu_count == 0:
        return "A"
    if avg_detention < 2 and ontime_pct > 80:
        return "B"
    if avg_detention < 3 and ontime_pct > 60:
        return "C"
    if avg_detention < 5 or ontime_pct > 40:
        return "D"
    return "F"


def rebuild_broker_history(db_path: str) -> None:
    """Rebuild the broker_history table from loads and load_feedback.

    For each unique broker_name in loads, calculates:
    - avg_detention_hours from feedback
    - tonu_count from accessorials where type='tonu'
    - loads_completed: count where outcome='booked' and feedback exists
    - loads_seen: total loads from this broker
    - rate_accuracy_pct: AVG(actual_rate_paid / rate_total * 100)
    - ontime_pickup_pct: percentage of feedback with ontime_pickup=True
    - reliability_grade: A/B/C/D/F/U
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        # Clear existing broker history before rebuild
        conn.execute("DELETE FROM broker_history")

        # Get all unique brokers
        brokers = conn.execute(
            """SELECT DISTINCT broker_name, broker_mc_number
               FROM loads
               WHERE broker_name IS NOT NULL AND broker_name != ''"""
        ).fetchall()

        for broker_row in brokers:
            broker_name = broker_row["broker_name"]
            broker_mc = broker_row["broker_mc_number"] or ""

            # Total loads seen
            loads_seen = conn.execute(
                "SELECT COUNT(*) FROM loads WHERE broker_name = ?",
                (broker_name,),
            ).fetchone()[0]

            # Loads with feedback
            feedback_rows = conn.execute(
                """SELECT lf.detention_hours, lf.actual_rate_paid, lf.ontime_pickup,
                          l.rate_total, l.outcome
                   FROM load_feedback lf
                   JOIN loads l ON l.id = lf.load_id
                   WHERE l.broker_name = ?""",
                (broker_name,),
            ).fetchall()

            has_feedback = len(feedback_rows) > 0

            if has_feedback:
                total_detention = 0.0
                ontime_count = 0
                rate_accuracy_values = []
                loads_completed = 0

                for fb in feedback_rows:
                    total_detention += fb["detention_hours"] or 0
                    if fb["ontime_pickup"]:
                        ontime_count += 1
                    if fb["actual_rate_paid"] and fb["rate_total"] and fb["rate_total"] > 0:
                        rate_accuracy_values.append(
                            fb["actual_rate_paid"] / fb["rate_total"] * 100
                        )
                    if fb["outcome"] == "booked":
                        loads_completed += 1

                avg_detention = total_detention / len(feedback_rows)
                ontime_pct = (ontime_count / len(feedback_rows)) * 100
                rate_accuracy = (
                    sum(rate_accuracy_values) / len(rate_accuracy_values)
                    if rate_accuracy_values
                    else 100.0
                )
            else:
                avg_detention = 0.0
                ontime_pct = 100.0
                rate_accuracy = 100.0
                loads_completed = 0

            # TONU count from accessorials
            tonu_count = conn.execute(
                """SELECT COUNT(*) FROM accessorials a
                   JOIN loads l ON l.id = a.load_id
                   WHERE l.broker_name = ? AND a.type = 'tonu'""",
                (broker_name,),
            ).fetchone()[0]

            grade = _calculate_grade(avg_detention, ontime_pct, tonu_count, has_feedback)

            conn.execute(
                """INSERT OR REPLACE INTO broker_history
                   (broker_name, broker_mc_number, avg_detention_hours, tonu_count,
                    loads_completed, loads_seen, rate_accuracy_pct, ontime_pickup_pct,
                    reliability_grade, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (broker_name, broker_mc, round(avg_detention, 2), tonu_count,
                 loads_completed, loads_seen, round(rate_accuracy, 2),
                 round(ontime_pct, 2), grade, now_iso),
            )

        conn.commit()
