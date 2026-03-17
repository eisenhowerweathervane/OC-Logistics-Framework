"""Composite scorer — combines financial, lane, broker, and strategic sub-scorers.

Produces a single weighted score and an action recommendation for a load.
"""

from dataclasses import dataclass
from typing import Optional

from database import get_db, DEFAULT_DB_PATH
from costs.cost_model import CostBreakdown
from scoring.financial_scorer import FinancialScore, score_financial
from scoring.lane_scorer import LaneScore, score_lane
from scoring.broker_scorer import BrokerScore, score_broker
from scoring.strategic_scorer import StrategicScore, score_strategic


@dataclass
class CompositeScore:
    """Combined scoring result for a single load.

    Attributes:
        score: Weighted composite score 0.0-1.0 (None if financial score is None).
        action: Recommended action — BOOK IT, CONSIDER, NEGOTIATE, or PASS.
        financial: Sub-score from the financial scorer.
        lane: Sub-score from the lane scorer.
        broker: Sub-score from the broker scorer.
        strategic: Sub-score from the strategic scorer.
        weights: The weight configuration used for this scoring.
    """
    score: Optional[float]
    action: str
    financial: FinancialScore
    lane: LaneScore
    broker: BrokerScore
    strategic: StrategicScore
    weights: dict


def _load_weights(db_path: str) -> dict:
    """Load scorer weights from the scorer_config table."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT financial_weight, lane_weight, broker_weight, strategic_weight
               FROM scorer_config WHERE id = 1"""
        ).fetchone()

    if row:
        return {
            "financial": row["financial_weight"],
            "lane": row["lane_weight"],
            "broker": row["broker_weight"],
            "strategic": row["strategic_weight"],
        }
    # Fallback defaults
    return {
        "financial": 0.50,
        "lane": 0.15,
        "broker": 0.15,
        "strategic": 0.20,
    }


def _action_from_score(score: float) -> str:
    """Map a composite score to an action tier."""
    if score >= 0.75:
        return "BOOK IT"
    if score >= 0.55:
        return "CONSIDER"
    if score >= 0.40:
        return "NEGOTIATE"
    return "PASS"


def score_load_composite(
    load: dict,
    cost_breakdown: CostBreakdown,
    current_city: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> CompositeScore:
    """Score a load by combining all four sub-scorers with configurable weights.

    Args:
        load: Load data dict with origin_city, destination_city, rate_total, etc.
        cost_breakdown: CostBreakdown from costs/cost_model.py.
        current_city: Current truck location (for deadhead context, unused by sub-scorers directly).
        db_path: Path to the SQLite database.

    Returns:
        CompositeScore with weighted score, action, and all sub-scores.
    """
    weights = _load_weights(db_path)

    # Compute deadhead percentage from cost breakdown
    deadhead_pct = 0.0
    if cost_breakdown.total_miles and cost_breakdown.total_miles > 0:
        deadhead_pct = (cost_breakdown.deadhead_miles / cost_breakdown.total_miles) * 100.0

    # 1. Financial scorer
    fin = score_financial(
        margin_pct=cost_breakdown.margin_pct,
        all_in_rpm=cost_breakdown.all_in_rpm,
        deadhead_pct=deadhead_pct,
        loaded_miles=cost_breakdown.loaded_miles,
        detention_hours=0.0,
    )

    # 2. Lane scorer
    lane = score_lane(
        origin_city=load.get("origin_city", ""),
        origin_state=load.get("origin_state", ""),
        dest_city=load.get("destination_city", ""),
        dest_state=load.get("destination_state", ""),
        rate_total=load.get("rate_total"),
        db_path=db_path,
    )

    # 3. Broker scorer
    broker = score_broker(
        broker_name=load.get("broker_name"),
        db_path=db_path,
    )

    # 4. Strategic scorer
    strategic = score_strategic(
        dest_city=load.get("destination_city", ""),
        dest_state=load.get("destination_state", ""),
        db_path=db_path,
    )

    # If financial score is None (no rate data), return NEGOTIATE with no composite score
    if fin.score is None:
        return CompositeScore(
            score=None,
            action="NEGOTIATE",
            financial=fin,
            lane=lane,
            broker=broker,
            strategic=strategic,
            weights=weights,
        )

    # Weighted composite score
    composite = (
        fin.score * weights["financial"]
        + lane.score * weights["lane"]
        + broker.score * weights["broker"]
        + strategic.score * weights["strategic"]
    )
    composite = max(0.0, min(1.0, composite))

    action = _action_from_score(composite)

    return CompositeScore(
        score=composite,
        action=action,
        financial=fin,
        lane=lane,
        broker=broker,
        strategic=strategic,
        weights=weights,
    )
