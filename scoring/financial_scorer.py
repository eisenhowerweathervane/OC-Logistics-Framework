"""Standalone financial scorer extracted from profitability_engine.py.

Provides a normalized 0-1 score based on margin, RPM, deadhead,
mileage, and detention metrics.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FinancialScore:
    """Result of financial scoring for a single load.

    Attributes:
        score: Normalized score from 0.0 to 1.0 (None if no rate data).
        raw_score: Original rubric score from -10 to +10 (None if no rate data).
        action: One of BOOK IT, CONSIDER, NEGOTIATE, PASS.
        components: Breakdown of individual score components.
    """
    score: Optional[float]
    raw_score: Optional[int]
    action: str
    components: dict = field(default_factory=dict)


def score_financial(
    margin_pct: Optional[float],
    all_in_rpm: Optional[float],
    deadhead_pct: float,
    loaded_miles: float,
    detention_hours: float,
    target_margin: float = 25.0,
    min_margin: float = 15.0,
    max_deadhead: float = 15.0,
) -> FinancialScore:
    """Score a load's financial attractiveness.

    Args:
        margin_pct: Profit margin percentage (None if no rate available).
        all_in_rpm: All-in revenue per mile (None if no rate available).
        deadhead_pct: Deadhead percentage (0-100 scale).
        loaded_miles: Loaded miles for the haul.
        detention_hours: Expected detention hours.
        target_margin: Target margin percentage (default 25%).
        min_margin: Minimum acceptable margin percentage (default 15%).
        max_deadhead: Maximum acceptable deadhead percentage (default 15%).

    Returns:
        FinancialScore with normalized score, raw score, action, and components.
    """
    # If no rate data, return None score with NEGOTIATE action
    if margin_pct is None or all_in_rpm is None:
        return FinancialScore(
            score=None,
            raw_score=None,
            action="NEGOTIATE",
            components={},
        )

    components = {}

    # --- Margin scoring ---
    if margin_pct >= target_margin:
        margin_score = 4
    elif margin_pct >= min_margin:
        margin_score = 2
    elif margin_pct >= 5:
        margin_score = 0
    elif margin_pct >= 0:
        margin_score = -2
    else:
        margin_score = -5
    components["margin"] = margin_score

    # --- All-in RPM scoring ---
    if all_in_rpm >= 3.00:
        rpm_score = 2
    elif all_in_rpm >= 2.50:
        rpm_score = 1
    elif all_in_rpm >= 2.00:
        rpm_score = 0
    else:
        rpm_score = -2
    components["rpm"] = rpm_score

    # --- Deadhead penalty ---
    if deadhead_pct <= 5:
        dh_score = 2
    elif deadhead_pct <= max_deadhead:
        dh_score = 1
    elif deadhead_pct <= 25:
        dh_score = -1
    else:
        dh_score = -3
    components["deadhead"] = dh_score

    # --- Mileage sweet spot ---
    if 150 <= loaded_miles <= 300:
        mile_score = 1
    elif loaded_miles < 80:
        mile_score = -1
    else:
        mile_score = 0
    components["mileage"] = mile_score

    # --- Detention risk ---
    if detention_hours > 2:
        det_score = -1
    else:
        det_score = 0
    components["detention"] = det_score

    # Sum and clamp to [-10, +10]
    raw = sum(components.values())
    raw = max(-10, min(10, raw))

    # Normalize to 0..1
    normalized = (raw + 10) / 20.0

    # Action tiers
    if raw >= 5:
        action = "BOOK IT"
    elif raw >= 2:
        action = "CONSIDER"
    elif raw >= 0:
        action = "NEGOTIATE"
    else:
        action = "PASS"

    return FinancialScore(
        score=normalized,
        raw_score=raw,
        action=action,
        components=components,
    )
