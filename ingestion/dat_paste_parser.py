"""Parser for text copy-pasted from the DAT load board dashboard.

Supports two formats:
1. DAT tabular format (real copy-paste from DAT website)
2. Freeform format ("City, ST → City, ST" with labeled fields)

Usage:
    from ingestion.dat_paste_parser import parse_dat_paste
    loads = parse_dat_paste(pasted_text)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

from models import ParsedLoad


# ---------------------------------------------------------------------------
# DAT TABULAR FORMAT PARSER
# ---------------------------------------------------------------------------
# Real DAT pastes look like this (columns separated by newlines/whitespace):
#
#   4m
#   $1,100
#   246
#   Obetz, OH
#   (13)
#   Bardstown, KY
#   3/17
#   VR
#   44,500 lbs
#   53 ft - Full
#   USA TRUCK LLC
#   loadpostings@usa-truck.com
#   – CS
#   – DTP

# Known header tokens that indicate the start of the DAT table header row
_DAT_HEADER_TOKENS = {"Age", "Rate", "Trip", "Origin", "DH-O", "Destination",
                       "DH-D", "Pick Up", "Equipment", "Company", "Contact",
                       "CS", "DTP"}


def _is_dat_tabular(text: str) -> bool:
    """Detect if the text looks like DAT tabular copy-paste."""
    # Check for header row markers
    lines = text.strip().split("\n")
    first_lines = " ".join(lines[:3])
    header_hits = sum(1 for t in _DAT_HEADER_TOKENS if t in first_lines)
    return header_hits >= 3


def _parse_dat_tabular(text: str) -> List[ParsedLoad]:
    """Parse DAT tabular format into loads.

    The DAT dashboard copies as a series of field values, one per line,
    with load boundaries separated by header-like tokens or age patterns.
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    # Remove header row tokens
    cleaned = []
    skip_headers = True
    for line in lines:
        # Skip lines that are purely header tokens
        if skip_headers and line in _DAT_HEADER_TOKENS:
            continue
        if skip_headers and line in ("Pick Up",):
            continue
        # Once we hit a non-header line, stop skipping
        skip_headers = False
        cleaned.append(line)

    # If all lines were headers, also try removing the header block
    if not cleaned:
        # Find the first line that looks like data (age pattern like "4m" or rate like "$1,100")
        for i, line in enumerate(lines):
            if re.match(r"^\d+[mhd]$", line) or re.match(r"^\$[\d,]+", line):
                cleaned = lines[i:]
                break

    if not cleaned:
        return []

    # Split into load chunks. Each load starts with an age marker (e.g., "4m", "7m", "2h")
    # or we detect load boundaries by the pattern of fields
    loads = []
    current_chunk: List[str] = []

    for line in cleaned:
        # Age markers: "4m", "7m", "2h", "1d", etc. — start of a new load
        if re.match(r"^\d+[mhd]$", line) and current_chunk:
            load = _parse_dat_chunk(current_chunk)
            if load:
                loads.append(load)
            current_chunk = [line]
        # Also detect "– CS" or "– DTP" as end-of-load markers
        elif line in ("– CS", "– DTP"):
            continue  # skip these markers
        else:
            current_chunk.append(line)

    # Don't forget the last chunk
    if current_chunk:
        load = _parse_dat_chunk(current_chunk)
        if load:
            loads.append(load)

    return loads


def _parse_dat_chunk(lines: List[str]) -> Optional[ParsedLoad]:
    """Parse a single load from DAT tabular lines.

    Expected field order (based on DAT column layout):
    0: Age (e.g., "4m")
    1: Rate (e.g., "$1,100" or "–")
    2: Trip miles (e.g., "246")
    3: Origin (e.g., "Obetz, OH")
    4: DH-O deadhead origin (e.g., "(13)")
    5: Destination (e.g., "Bardstown, KY")
    6: DH-D or Pick Up date (e.g., "3/17")
    Then variable: equipment, weight, dimensions, company, contact info
    """
    if len(lines) < 4:
        return None

    # Find key fields by pattern matching rather than fixed positions
    rate_total: Optional[float] = None
    mileage: int = 0
    origin_city = ""
    origin_state = ""
    dest_city = ""
    dest_state = ""
    deadhead_miles: int = 0
    pickup_date = ""
    weight: Optional[int] = None
    equipment = "Van"
    broker_name = ""
    contact_email = ""
    contact_phone = ""

    # Track which lines we've consumed
    city_state_re = re.compile(r"^([A-Za-z .'-]+),\s*([A-Z]{2})$")
    found_origin = False
    found_dest = False

    for line in lines:
        line = line.strip()

        # Skip age marker
        if re.match(r"^\d+[mhd]$", line):
            continue

        # Rate: "$1,100" or "$2,500.00" or "–" (no rate)
        if re.match(r"^\$[\d,]+(?:\.\d{1,2})?$", line):
            rate_total = float(line.replace("$", "").replace(",", ""))
            continue

        # "–" alone means no rate or no data
        if line == "–" or line == "-":
            continue

        # Trip miles: standalone number (3 digits typically)
        if re.match(r"^\d{2,4}$", line) and mileage == 0:
            mileage = int(line)
            continue

        # Deadhead: "(13)" or "(0)"
        dh_match = re.match(r"^\((\d+)\)$", line)
        if dh_match:
            if found_origin and not found_dest:
                deadhead_miles = int(dh_match.group(1))
            continue

        # City, State
        city_match = city_state_re.match(line)
        if city_match:
            if not found_origin:
                origin_city = city_match.group(1).strip()
                origin_state = city_match.group(2).strip()
                found_origin = True
            elif not found_dest:
                dest_city = city_match.group(1).strip()
                dest_state = city_match.group(2).strip()
                found_dest = True
            continue

        # Pickup date: "3/17" or "03/17" (short format, no year)
        date_match = re.match(r"^(\d{1,2})/(\d{1,2})$", line)
        if date_match and not pickup_date:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            # Assume current year, or next year if date has passed
            now = datetime.now()
            year = now.year
            try:
                pickup = datetime(year, month, day)
                if pickup < now - timedelta(days=30):
                    year += 1
                pickup_date = f"{year}-{month:02d}-{day:02d}"
            except ValueError:
                pass
            continue

        # Full date: "3/17/2026" or "03/17/2026"
        full_date_match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", line)
        if full_date_match and not pickup_date:
            month = full_date_match.group(1).zfill(2)
            day = full_date_match.group(2).zfill(2)
            year = full_date_match.group(3)
            pickup_date = f"{year}-{month}-{day}"
            continue

        # Weight: "44,500 lbs"
        weight_match = re.match(r"^([\d,]+)\s*lbs?$", line, re.IGNORECASE)
        if weight_match:
            weight = int(weight_match.group(1).replace(",", ""))
            continue

        # Equipment: "V", "VR", "R", "F", "Van", "Reefer", etc.
        if line in ("V", "VR", "Van"):
            equipment = "Van"
            continue
        if line in ("R", "Reefer"):
            equipment = "Reefer"
            continue
        if line in ("F", "Flatbed"):
            equipment = "Flatbed"
            continue

        # Dimensions: "53 ft - Full" or "48 ft" — skip
        if re.match(r"^\d+\s*ft", line):
            continue

        # "Subscribe for full access" — skip
        if "subscribe" in line.lower():
            continue

        # Email
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", line)
        if email_match:
            contact_email = email_match.group(0)
            continue

        # Phone
        phone_match = re.search(r"\d{3}[-.\s]\d{3}[-.\s]\d{4}", line)
        if phone_match:
            contact_phone = phone_match.group(0)
            continue

        # If we haven't matched anything else and we have origin+dest,
        # this is likely the company name
        if found_origin and found_dest and not broker_name:
            # Skip common non-company tokens
            if line not in ("– CS", "– DTP", "CS", "DTP"):
                broker_name = line

    # Must have at least origin and destination
    if not (origin_city and origin_state and dest_city and dest_state):
        return None

    return ParsedLoad(
        origin_city=origin_city,
        origin_state=origin_state,
        destination_city=dest_city,
        destination_state=dest_state,
        mileage=mileage,
        deadhead_miles=deadhead_miles,
        source="paste",
        rate_total=rate_total,
        weight=weight,
        equipment_type=equipment,
        pickup_date=pickup_date,
        broker_name=broker_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
    )


# ---------------------------------------------------------------------------
# FREEFORM FORMAT PARSER (original "City, ST → City, ST" format)
# ---------------------------------------------------------------------------

_ROUTE_RE = re.compile(
    r"([A-Za-z .'-]+),\s*([A-Z]{2})\s*"
    r"(?:\u2192|->|to)\s*"
    r"([A-Za-z .'-]+),\s*([A-Z]{2})"
)
_MILEAGE_RE = re.compile(r"(\d{1,5})\s*mi\b", re.IGNORECASE)
_RATE_RE = re.compile(r"Rate:\s*\$?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_RATE_CALL_RE = re.compile(r"Rate:\s*Call", re.IGNORECASE)
_RPM_RE = re.compile(r"\$([\d]+(?:\.\d{1,2})?)\s*/\s*mi", re.IGNORECASE)
_WEIGHT_RE = re.compile(r"([\d,]+)\s*lbs?\b", re.IGNORECASE)
_EQUIPMENT_RE = re.compile(
    r"\b(Van|Reefer|Flatbed|Step\s*Deck|Power\s*Only)\b", re.IGNORECASE
)
_PICKUP_DATE_RE = re.compile(
    r"Pickup:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE
)
_DELIVERY_DATE_RE = re.compile(
    r"Delivery:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE
)
_TIME_WINDOW_RE = re.compile(r"\b(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\b")
_COMPANY_RE = re.compile(r"Company:\s*(.+)", re.IGNORECASE)
_MC_RE = re.compile(r"MC[#\-]\s*(\d{4,7})", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(\d{3}-\d{3}-\d{4})\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _parse_date(m: re.Match) -> str:
    """Convert MM/DD/YYYY match groups to YYYY-MM-DD."""
    month, day, year = m.group(1), m.group(2), m.group(3)
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _parse_block(block: str) -> Optional[ParsedLoad]:
    """Parse a single freeform load block into a ParsedLoad."""
    route = _ROUTE_RE.search(block)
    if route is None:
        return None

    origin_city = route.group(1).strip()
    origin_state = route.group(2).strip()
    dest_city = route.group(3).strip()
    dest_state = route.group(4).strip()

    mileage_m = _MILEAGE_RE.search(block)
    mileage = int(mileage_m.group(1)) if mileage_m else 0

    rate_total: Optional[float] = None
    if _RATE_CALL_RE.search(block):
        rate_total = None
    else:
        rate_m = _RATE_RE.search(block)
        if rate_m:
            rate_total = float(rate_m.group(1).replace(",", ""))

    rpm_m = _RPM_RE.search(block)
    rate_per_mile: Optional[float] = None
    if rpm_m:
        rate_per_mile = float(rpm_m.group(1))

    weight_m = _WEIGHT_RE.search(block)
    weight: Optional[int] = None
    if weight_m:
        weight = int(weight_m.group(1).replace(",", ""))

    equip_m = _EQUIPMENT_RE.search(block)
    equipment = equip_m.group(1).strip() if equip_m else "Van"

    pickup_date = ""
    pickup_time = ""
    pd_m = _PICKUP_DATE_RE.search(block)
    if pd_m:
        pickup_date = _parse_date(pd_m)
        after_date = block[pd_m.end():]
        tw_m = _TIME_WINDOW_RE.search(after_date)
        if tw_m:
            pickup_time = tw_m.group(1).replace(" ", "")

    delivery_date = ""
    delivery_time = ""
    dd_m = _DELIVERY_DATE_RE.search(block)
    if dd_m:
        delivery_date = _parse_date(dd_m)
        after_date = block[dd_m.end():]
        tw_m = _TIME_WINDOW_RE.search(after_date)
        if tw_m:
            delivery_time = tw_m.group(1).replace(" ", "")

    comp_m = _COMPANY_RE.search(block)
    broker_name = comp_m.group(1).strip() if comp_m else ""

    mc_m = _MC_RE.search(block)
    mc_number = mc_m.group(1) if mc_m else ""

    phone_m = _PHONE_RE.search(block)
    phone = phone_m.group(1) if phone_m else ""

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

    Automatically detects whether the input is DAT tabular format (real
    dashboard copy-paste) or freeform format, and uses the appropriate parser.
    """
    if not text or not text.strip():
        return []

    # Auto-detect format
    if _is_dat_tabular(text):
        return _parse_dat_tabular(text)

    # Freeform format: split on blank lines
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
