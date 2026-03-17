"""Parser for text copy-pasted from the DAT load board dashboard.

Usage:
    from ingestion.dat_paste_parser import parse_dat_paste
    loads = parse_dat_paste(pasted_text)
"""

from __future__ import annotations

import re
from typing import List, Optional

from models import ParsedLoad

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Route: "City, ST -> City, ST" with arrow variants
_ROUTE_RE = re.compile(
    r"([A-Za-z .'-]+),\s*([A-Z]{2})\s*"
    r"(?:\u2192|->|to)\s*"
    r"([A-Za-z .'-]+),\s*([A-Z]{2})"
)

# Mileage: "240 mi"
_MILEAGE_RE = re.compile(r"(\d{1,5})\s*mi\b", re.IGNORECASE)

# Rate total: "Rate: $720.00"  — returns None for "Call"
_RATE_RE = re.compile(r"Rate:\s*\$?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_RATE_CALL_RE = re.compile(r"Rate:\s*Call", re.IGNORECASE)

# Rate per mile: "$3.00/mi"
_RPM_RE = re.compile(r"\$([\d]+(?:\.\d{1,2})?)\s*/\s*mi", re.IGNORECASE)

# Weight: "42,000 lbs"
_WEIGHT_RE = re.compile(r"([\d,]+)\s*lbs?\b", re.IGNORECASE)

# Equipment type
_EQUIPMENT_RE = re.compile(
    r"\b(Van|Reefer|Flatbed|Step\s*Deck|Power\s*Only)\b", re.IGNORECASE
)

# Pickup / Delivery date: "Pickup: 03/20/2026"
_PICKUP_DATE_RE = re.compile(
    r"Pickup:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE
)
_DELIVERY_DATE_RE = re.compile(
    r"Delivery:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE
)

# Time window: "08:00-14:00"
_TIME_WINDOW_RE = re.compile(r"\b(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\b")

# Company / broker name
_COMPANY_RE = re.compile(r"Company:\s*(.+)", re.IGNORECASE)

# MC number: "MC# 123456" or "MC-123456"
_MC_RE = re.compile(r"MC[#\-]\s*(\d{4,7})", re.IGNORECASE)

# Phone: "214-555-1234"
_PHONE_RE = re.compile(r"\b(\d{3}-\d{3}-\d{4})\b")

# Email
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(m: re.Match) -> str:
    """Convert MM/DD/YYYY match groups to YYYY-MM-DD."""
    month, day, year = m.group(1), m.group(2), m.group(3)
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _parse_block(block: str) -> Optional[ParsedLoad]:
    """Parse a single load block into a ParsedLoad, or None if insufficient data."""
    route = _ROUTE_RE.search(block)
    if route is None:
        return None

    origin_city = route.group(1).strip()
    origin_state = route.group(2).strip()
    dest_city = route.group(3).strip()
    dest_state = route.group(4).strip()

    # Mileage
    mileage_m = _MILEAGE_RE.search(block)
    mileage = int(mileage_m.group(1)) if mileage_m else 0

    # Rate
    rate_total: Optional[float] = None
    if _RATE_CALL_RE.search(block):
        rate_total = None
    else:
        rate_m = _RATE_RE.search(block)
        if rate_m:
            rate_total = float(rate_m.group(1).replace(",", ""))

    # Rate per mile
    rpm_m = _RPM_RE.search(block)
    rate_per_mile: Optional[float] = None
    if rpm_m:
        rate_per_mile = float(rpm_m.group(1))

    # Weight
    weight_m = _WEIGHT_RE.search(block)
    weight: Optional[int] = None
    if weight_m:
        weight = int(weight_m.group(1).replace(",", ""))

    # Equipment
    equip_m = _EQUIPMENT_RE.search(block)
    equipment = equip_m.group(1).strip() if equip_m else "Van"

    # Pickup date & time
    pickup_date = ""
    pickup_time = ""
    pd_m = _PICKUP_DATE_RE.search(block)
    if pd_m:
        pickup_date = _parse_date(pd_m)
        # Look for time window on the same or next line after the pickup date
        after_date = block[pd_m.end():]
        tw_m = _TIME_WINDOW_RE.search(after_date)
        if tw_m:
            pickup_time = tw_m.group(1).replace(" ", "")

    # Delivery date & time
    delivery_date = ""
    delivery_time = ""
    dd_m = _DELIVERY_DATE_RE.search(block)
    if dd_m:
        delivery_date = _parse_date(dd_m)
        after_date = block[dd_m.end():]
        tw_m = _TIME_WINDOW_RE.search(after_date)
        if tw_m:
            delivery_time = tw_m.group(1).replace(" ", "")

    # Company
    comp_m = _COMPANY_RE.search(block)
    broker_name = comp_m.group(1).strip() if comp_m else ""

    # MC number
    mc_m = _MC_RE.search(block)
    mc_number = mc_m.group(1) if mc_m else ""

    # Phone
    phone_m = _PHONE_RE.search(block)
    phone = phone_m.group(1) if phone_m else ""

    # Email
    email_m = _EMAIL_RE.search(block)
    email = email_m.group(0) if email_m else ""

    return ParsedLoad(
        origin_city=origin_city,
        origin_state=origin_state,
        destination_city=dest_city,
        destination_state=dest_state,
        mileage=mileage,
        source="paste",
        rate_total=rate_total,
        rate_per_mile=rate_per_mile,
        weight=weight,
        equipment_type=equipment,
        pickup_date=pickup_date,
        pickup_time_window=pickup_time,
        delivery_date=delivery_date,
        delivery_time_window=delivery_time,
        broker_name=broker_name,
        broker_mc_number=mc_number,
        contact_phone=phone,
        contact_email=email,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_dat_paste(text: str) -> List[ParsedLoad]:
    """Parse raw text copied from the DAT web dashboard into ParsedLoad objects.

    Blocks are separated by double newlines. Each block that contains at least
    an origin and destination is returned as a ParsedLoad with source="paste".
    """
    if not text or not text.strip():
        return []

    # Split on one or more blank lines
    blocks = re.split(r"\n\s*\n", text.strip())

    results: List[ParsedLoad] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parsed = _parse_block(block)
        if parsed is not None:
            results.append(parsed)

    return results
