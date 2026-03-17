"""Gap resolver — identifies missing or low-confidence fields in parsed loads.

Examines a ParsedLoad and produces a GapReport detailing which required and
optional fields are absent or below the confidence threshold, and provides
a method to fill those gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import ParsedLoad

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORING_FIELDS: list[str] = [
    "rate_total",
    "deadhead_miles",
    "weight",
    "pickup_date",
    "delivery_date",
    "broker_name",
]

REQUIRED_FIELDS: list[str] = [
    "origin_city",
    "origin_state",
    "destination_city",
    "destination_state",
    "mileage",
]

CONFIDENCE_THRESHOLD: float = 0.7


# ---------------------------------------------------------------------------
# GapReport
# ---------------------------------------------------------------------------

@dataclass
class GapReport:
    """Result of gap analysis on a ParsedLoad."""

    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)
    fields_parsed: int = 0
    fields_total: int = len(SCORING_FIELDS) + len(REQUIRED_FIELDS)

    @property
    def is_complete(self) -> bool:
        """True when every required field is present."""
        return len(self.missing_required) == 0

    @property
    def summary(self) -> str:
        """Human-readable summary of the gap analysis."""
        gaps = self.missing_required + self.missing_optional + self.low_confidence
        if gaps:
            return f"Parsed {self.fields_parsed} of {self.fields_total} fields — gaps: {', '.join(gaps)}"
        return f"Parsed {self.fields_parsed} of {self.fields_total} fields — no gaps"

    @staticmethod
    def apply_fills(load: ParsedLoad, fills: dict) -> ParsedLoad:
        """Return a new ParsedLoad with *fills* merged in."""
        data = load.model_dump()
        data.update(fills)
        return ParsedLoad(**data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _is_missing(value: object) -> bool:
    """Return True if a field value should be considered missing."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (int, float)) and value == 0:
        return True
    return False


def resolve_gaps(
    load: ParsedLoad,
    field_confidence: Optional[dict[str, float]] = None,
) -> GapReport:
    """Analyse *load* and return a :class:`GapReport`.

    Parameters
    ----------
    load:
        The parsed load to inspect.
    field_confidence:
        Optional mapping of field name → confidence score (0-1).  Fields
        below ``CONFIDENCE_THRESHOLD`` are flagged.
    """
    missing_required: list[str] = []
    missing_optional: list[str] = []
    low_confidence: list[str] = []
    parsed = 0

    # --- required fields ---
    for fname in REQUIRED_FIELDS:
        val = getattr(load, fname, None)
        if _is_missing(val):
            missing_required.append(fname)
        else:
            parsed += 1

    # --- scoring (optional) fields ---
    for fname in SCORING_FIELDS:
        val = getattr(load, fname, None)
        if _is_missing(val):
            missing_optional.append(fname)
        else:
            parsed += 1

    # --- confidence check ---
    if field_confidence:
        for fname, conf in field_confidence.items():
            if conf < CONFIDENCE_THRESHOLD and fname not in low_confidence:
                low_confidence.append(fname)

    return GapReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        low_confidence=low_confidence,
        fields_parsed=parsed,
    )
