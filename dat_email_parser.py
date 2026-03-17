"""
DAT Load Board Email Parser - Phase 1
Parses raw DAT load alert emails and extracts structured load data.
"""

import re
from typing import Optional


def parse_load_email(raw_text: str) -> list[dict]:
    """
    Parse a DAT load board alert email and extract load data.

    Args:
        raw_text: The raw email text content

    Returns:
        A list of dicts, one per load found in the email.
        Even single-load emails return a list with one item.
    """
    loads = split_multi_load_email(raw_text)
    return [parse_single_load(load_text) for load_text in loads]


def split_multi_load_email(raw_text: str) -> list[str]:
    """
    Split a multi-load email into individual load sections.
    Handles "Load X of Y" pattern.
    """
    # Pattern to match "Load X of Y" headers
    load_header_pattern = r'Load\s+\d+\s+of\s+\d+'

    # Find all load header positions
    matches = list(re.finditer(load_header_pattern, raw_text, re.IGNORECASE))

    if not matches:
        # No load headers found, treat entire text as single load
        return [raw_text]

    load_sections = []
    for i, match in enumerate(matches):
        start = match.start()
        # End is either the start of next load or end of text
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(raw_text)

        load_sections.append(raw_text[start:end])

    return load_sections


def parse_single_load(load_text: str) -> dict:
    """Parse a single load section and extract all fields."""

    result = {
        "origin_city": "",
        "origin_state": "",
        "destination_city": "",
        "destination_state": "",
        "rate_total": None,
        "rate_per_mile": None,
        "mileage": None,
        "deadhead_miles": None,
        "weight": None,
        "equipment_type": "",
        "commodity": "",
        "pickup_date": "",
        "pickup_time_window": "",
        "delivery_date": "",
        "delivery_time_window": "",
        "broker_name": "",
        "broker_mc_number": "",
        "contact_phone": "",
        "contact_email": "",
        "load_number": "",
        "notes": ""
    }

    # Extract origin (city, state)
    origin = extract_origin(load_text)
    if origin:
        result["origin_city"] = origin[0]
        result["origin_state"] = origin[1]

    # Extract destination (city, state)
    destination = extract_destination(load_text)
    if destination:
        result["destination_city"] = destination[0]
        result["destination_state"] = destination[1]

    # Extract mileage (Trip: XXX mi)
    result["mileage"] = extract_mileage(load_text)

    # Extract deadhead miles
    result["deadhead_miles"] = extract_deadhead(load_text)

    # Extract equipment type
    result["equipment_type"] = extract_equipment(load_text)

    # Extract weight
    result["weight"] = extract_weight(load_text)

    # Extract commodity
    result["commodity"] = extract_commodity(load_text)

    # Extract pickup date and time
    pickup = extract_pickup(load_text)
    result["pickup_date"] = pickup[0]
    result["pickup_time_window"] = pickup[1]

    # Extract delivery date and time
    delivery = extract_delivery(load_text)
    result["delivery_date"] = delivery[0]
    result["delivery_time_window"] = delivery[1]

    # Extract rate information
    rate_info = extract_rate(load_text)
    result["rate_total"] = rate_info[0]
    result["rate_per_mile"] = rate_info[1]

    # Calculate rate_per_mile if not provided but we have total and mileage
    if result["rate_per_mile"] is None and result["rate_total"] is not None and result["mileage"]:
        result["rate_per_mile"] = round(result["rate_total"] / result["mileage"], 2)

    # Extract broker/company info
    result["broker_name"] = extract_company(load_text)
    result["broker_mc_number"] = extract_mc_number(load_text)
    result["contact_phone"] = extract_phone(load_text)
    result["contact_email"] = extract_email(load_text)

    # Extract load/reference number
    result["load_number"] = extract_ref_number(load_text)

    # Extract notes/comments
    result["notes"] = extract_comments(load_text)

    return result


def extract_origin(text: str) -> Optional[tuple[str, str]]:
    """Extract origin city and state."""
    # Pattern: "Origin: City, ST" or "Origin: City, State"
    # Supports cities with hyphens (Winston-Salem), apostrophes (O'Fallon),
    # periods (St. Louis), and slashes (Winston/Salem)
    pattern = r"Origin:\s*([A-Za-z\s.'\-/]+),\s*([A-Z]{2})\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return (match.group(1).strip(), match.group(2).upper())
    return None


def extract_destination(text: str) -> Optional[tuple[str, str]]:
    """Extract destination city and state."""
    # Supports cities with hyphens, apostrophes, periods, and slashes
    pattern = r"Destination:\s*([A-Za-z\s.'\-/]+),\s*([A-Z]{2})\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return (match.group(1).strip(), match.group(2).upper())
    return None


def extract_mileage(text: str) -> Optional[int]:
    """Extract trip mileage."""
    # Pattern: "Trip: 456 mi" or "Trip: 456 miles"
    pattern = r'Trip:\s*([\d,]+)\s*mi'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(',', ''))
    return None


def extract_deadhead(text: str) -> Optional[int]:
    """Extract deadhead miles."""
    # Pattern: "Deadhead: 127 mi" or "Deadhead: 127 mi from City, ST"
    pattern = r'Deadhead:\s*([\d,]+)\s*mi'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(',', ''))
    return None


def extract_equipment(text: str) -> str:
    """Extract equipment type."""
    pattern = r'Equipment:\s*(\w+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_weight(text: str) -> Optional[int]:
    """Extract weight in lbs."""
    # Pattern: "Weight: 38,000 lbs" or "Weight: 38000 lbs"
    pattern = r'Weight:\s*([\d,]+)\s*lbs?'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(',', ''))
    return None


def extract_commodity(text: str) -> str:
    """Extract commodity being hauled."""
    pattern = r'Commodity:\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_pickup(text: str) -> tuple[str, str]:
    """Extract pickup date and time window."""
    date = ""
    time_window = ""

    # Date pattern: "Pick Up: 03/18/2026" or "Pickup: 03/18/2026"
    date_pattern = r'Pick\s*Up:\s*(\d{2}/\d{2}/\d{4})'
    match = re.search(date_pattern, text, re.IGNORECASE)
    if match:
        # Convert to ISO format (YYYY-MM-DD)
        date_str = match.group(1)
        parts = date_str.split('/')
        if len(parts) == 3:
            date = f"{parts[2]}-{parts[0]}-{parts[1]}"

    # Time window pattern: "Dock Hours: 08:00 - 14:00" or "Pickup Hours: ..."
    time_pattern = r'(?:Dock\s*Hours|Pickup\s*Hours):\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    match = re.search(time_pattern, text, re.IGNORECASE)
    if match:
        time_window = f"{match.group(1)}-{match.group(2)}"

    return (date, time_window)


def extract_delivery(text: str) -> tuple[str, str]:
    """Extract delivery date and time window."""
    date = ""
    time_window = ""

    # Date pattern: "Delivery: 03/19/2026"
    date_pattern = r'Delivery:\s*(\d{2}/\d{2}/\d{4})'
    match = re.search(date_pattern, text, re.IGNORECASE)
    if match:
        # Convert to ISO format
        date_str = match.group(1)
        parts = date_str.split('/')
        if len(parts) == 3:
            date = f"{parts[2]}-{parts[0]}-{parts[1]}"

    # Time window pattern: "Del Hours: 06:00 - 18:00" or "Delivery Hours: ..."
    time_pattern = r'(?:Del\s*Hours|Delivery\s*Hours):\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    match = re.search(time_pattern, text, re.IGNORECASE)
    if match:
        time_window = f"{match.group(1)}-{match.group(2)}"

    return (date, time_window)


def extract_rate(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract rate total and rate per mile."""
    rate_total = None
    rate_per_mile = None

    # Check for "Call for rate" first
    if re.search(r'Rate:\s*Call\s+for\s+rate', text, re.IGNORECASE):
        return (None, None)

    # Pattern: "Rate: $2,052.00" or "Rate: $2,052.00 ($4.50/mi)"
    # Extract total rate
    total_pattern = r'Rate:\s*\$?([\d,]+(?:\.\d{2})?)'
    match = re.search(total_pattern, text, re.IGNORECASE)
    if match:
        rate_total = float(match.group(1).replace(',', ''))

    # Extract per-mile rate if present
    per_mile_pattern = r'\(\$?([\d.]+)/mi\)'
    match = re.search(per_mile_pattern, text, re.IGNORECASE)
    if match:
        rate_per_mile = float(match.group(1))

    return (rate_total, rate_per_mile)


def extract_company(text: str) -> str:
    """Extract company/broker name."""
    pattern = r'Company:\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_mc_number(text: str) -> str:
    """Extract MC number."""
    # Pattern: "MC#: MC-384759" or "MC#: 384759"
    pattern = r'MC#?:\s*(MC-?\d+|\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_phone(text: str) -> str:
    """Extract contact phone number."""
    # Pattern: "Contact: (614) 555-0182" or phone number format
    pattern = r'Contact:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_email(text: str) -> str:
    """Extract contact email."""
    pattern = r'Email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_ref_number(text: str) -> str:
    """Extract reference/load number."""
    # Pattern: "Ref#: TW-90284" or "Reference: ..."
    pattern = r'Ref#?:\s*([A-Za-z0-9-]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_comments(text: str) -> str:
    """Extract comments/notes."""
    pattern = r'Comments:\s*(.+?)(?:\n---|\n\n|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        # Clean up the comment text
        comment = match.group(1).strip()
        # Remove trailing separator lines or email footer markers
        comment = re.sub(r'\n+---.*$', '', comment, flags=re.DOTALL)
        comment = re.sub(r'\n+To manage your alerts.*$', '', comment, flags=re.DOTALL | re.IGNORECASE)
        return comment.strip()
    return ""


# ============================================================================
# SAMPLE EMAILS FOR TESTING
# ============================================================================

SAMPLE_EMAIL_1 = """Subject: DAT Load Alert - Van loads matching your search

DAT One Load Board Alert
Results for your saved search: Cleveland, OH → Any

Load 1 of 3

Origin: Columbus, OH
Destination: Charlotte, NC
Trip: 456 mi
Deadhead: 127 mi from Cleveland, OH

Equipment: Van
Full/Partial: Full
Length: 48 ft
Weight: 38,000 lbs
Commodity: Auto Parts

Pick Up: 03/18/2026
Dock Hours: 08:00 - 14:00
Delivery: 03/19/2026
Del Hours: 06:00 - 18:00

Rate: $2,052.00 ($4.50/mi)

Company: Transway Logistics Inc
MC#: MC-384759
Contact: (614) 555-0182
Ref#: TW-90284

Comments: No touch freight. Driver assist not required.

---

To manage your alerts, log in to DAT One at one.dat.com
You are receiving this email because you enabled alerts on your DAT account.
"""

SAMPLE_EMAIL_2 = """Subject: DAT Load Alert - Van loads matching your search

DAT One Load Board Alert
Results for your saved search: Cleveland, OH → Midwest

Load 1 of 5

Origin: Indianapolis, IN
Destination: Detroit, MI
Trip: 280 mi
Deadhead: 65 mi

Equipment: Van
Full/Partial: Full
Weight: 42,500 lbs

Pick Up: 03/17/2026
Delivery: 03/17/2026

Rate: $840.00 ($3.00/mi)

Company: ABC Freight Brokerage
MC#: MC-221087
Contact: (317) 555-0249

Comments: Appointment required. Call before 2pm.

---

To manage your alerts, log in to DAT One at one.dat.com
"""

SAMPLE_EMAIL_3 = """Subject: DAT Load Alert - Reefer loads matching your search

DAT One Load Board Alert
Results for your saved search: Cleveland, OH → Southeast

Load 1 of 2

Origin: Akron, OH
Destination: Nashville, TN
Trip: 512 mi
Deadhead: 34 mi

Equipment: Reefer
Full/Partial: Full
Length: 53 ft
Weight: 44,000 lbs
Commodity: Frozen Foods

Pick Up: 03/19/2026
Dock Hours: 06:00 - 10:00

Rate: Call for rate

Company: Summit Cold Chain LLC
Contact: (330) 555-0917
Email: dispatch@summitcoldchain.com
Ref#: SCC-2026-1148

Comments: Temp controlled 0°F. Continuous reefer required. Must have clean inspection history.

---

To manage your alerts, log in to DAT One at one.dat.com
"""

SAMPLE_EMAIL_4 = """Subject: DAT Load Alert - Van loads matching your search

DAT One Load Board Alert
Results for your saved search: Cleveland, OH → Northeast

Load 1 of 4

Origin: Erie, PA
Destination: Newark, NJ
Trip: 395 mi
Deadhead: 98 mi from Cleveland, OH

Equipment: Van
Full/Partial: Full
Weight: 35,200 lbs
Commodity: Consumer Electronics

Pick Up: 03/20/2026
Dock Hours: 10:00 - 16:00
Delivery: 03/21/2026
Del Hours: 08:00 - 12:00

Rate: $1,383.00 ($3.50/mi)

Company: Northeast Freight Partners
MC#: MC-509321
Contact: (814) 555-0733
Email: loads@nefp.com

Comments: Liftgate required at delivery. 2 pallets.

---

Load 2 of 4

Origin: Pittsburgh, PA
Destination: Boston, MA
Trip: 572 mi
Deadhead: 131 mi

Equipment: Van
Full/Partial: Full
Length: 53 ft
Weight: 40,000 lbs

Pick Up: 03/20/2026
Delivery: 03/22/2026

Rate: $1,716.00 ($3.00/mi)

Company: Bay State Logistics
MC#: MC-672143
Contact: (412) 555-0591

---

To manage your alerts, log in to DAT One at one.dat.com
"""


# ============================================================================
# UNIT TESTS
# ============================================================================

def test_sample_1():
    """Test Sample 1: Full details, verify rate_per_mile from email."""
    results = parse_load_email(SAMPLE_EMAIL_1)

    assert len(results) == 1, f"Expected 1 load, got {len(results)}"
    load = results[0]

    assert load["origin_city"] == "Columbus", f"Expected origin_city 'Columbus', got '{load['origin_city']}'"
    assert load["origin_state"] == "OH", f"Expected origin_state 'OH', got '{load['origin_state']}'"
    assert load["destination_city"] == "Charlotte", f"Expected destination_city 'Charlotte', got '{load['destination_city']}'"
    assert load["destination_state"] == "NC", f"Expected destination_state 'NC', got '{load['destination_state']}'"
    assert load["mileage"] == 456, f"Expected mileage 456, got {load['mileage']}"
    assert load["deadhead_miles"] == 127, f"Expected deadhead 127, got {load['deadhead_miles']}"
    assert load["rate_total"] == 2052.00, f"Expected rate_total 2052.00, got {load['rate_total']}"
    assert load["rate_per_mile"] == 4.50, f"Expected rate_per_mile 4.50, got {load['rate_per_mile']}"
    assert load["equipment_type"] == "Van", f"Expected equipment 'Van', got '{load['equipment_type']}'"
    assert load["weight"] == 38000, f"Expected weight 38000, got {load['weight']}"
    assert load["commodity"] == "Auto Parts", f"Expected commodity 'Auto Parts', got '{load['commodity']}'"
    assert load["pickup_date"] == "2026-03-18", f"Expected pickup_date '2026-03-18', got '{load['pickup_date']}'"
    assert load["pickup_time_window"] == "08:00-14:00", f"Expected pickup_time '08:00-14:00', got '{load['pickup_time_window']}'"
    assert load["delivery_date"] == "2026-03-19", f"Expected delivery_date '2026-03-19', got '{load['delivery_date']}'"
    assert load["delivery_time_window"] == "06:00-18:00", f"Expected delivery_time '06:00-18:00', got '{load['delivery_time_window']}'"
    assert load["broker_name"] == "Transway Logistics Inc", f"Expected broker 'Transway Logistics Inc', got '{load['broker_name']}'"
    assert load["broker_mc_number"] == "MC-384759", f"Expected MC# 'MC-384759', got '{load['broker_mc_number']}'"
    assert load["contact_phone"] == "(614) 555-0182", f"Expected phone '(614) 555-0182', got '{load['contact_phone']}'"
    assert load["load_number"] == "TW-90284", f"Expected ref 'TW-90284', got '{load['load_number']}'"
    assert "No touch freight" in load["notes"], f"Expected 'No touch freight' in notes, got '{load['notes']}'"

    print("✓ Sample 1: All tests passed")


def test_sample_2():
    """Test Sample 2: Missing fields return null/empty, same-day pickup & delivery."""
    results = parse_load_email(SAMPLE_EMAIL_2)

    assert len(results) == 1, f"Expected 1 load, got {len(results)}"
    load = results[0]

    assert load["origin_city"] == "Indianapolis", f"Expected origin_city 'Indianapolis', got '{load['origin_city']}'"
    assert load["origin_state"] == "IN", f"Expected origin_state 'IN', got '{load['origin_state']}'"
    assert load["destination_city"] == "Detroit", f"Expected destination_city 'Detroit', got '{load['destination_city']}'"
    assert load["destination_state"] == "MI", f"Expected destination_state 'MI', got '{load['destination_state']}'"
    assert load["mileage"] == 280, f"Expected mileage 280, got {load['mileage']}"
    assert load["rate_total"] == 840.00, f"Expected rate_total 840.00, got {load['rate_total']}"
    assert load["rate_per_mile"] == 3.00, f"Expected rate_per_mile 3.00, got {load['rate_per_mile']}"

    # Same-day delivery
    assert load["pickup_date"] == "2026-03-17", f"Expected pickup_date '2026-03-17', got '{load['pickup_date']}'"
    assert load["delivery_date"] == "2026-03-17", f"Expected delivery_date '2026-03-17', got '{load['delivery_date']}'"

    # Missing fields should be null/empty
    assert load["commodity"] == "", f"Expected empty commodity, got '{load['commodity']}'"
    assert load["pickup_time_window"] == "", f"Expected empty pickup_time_window, got '{load['pickup_time_window']}'"
    assert load["delivery_time_window"] == "", f"Expected empty delivery_time_window, got '{load['delivery_time_window']}'"
    assert load["contact_email"] == "", f"Expected empty contact_email, got '{load['contact_email']}'"
    assert load["load_number"] == "", f"Expected empty load_number, got '{load['load_number']}'"

    print("✓ Sample 2: All tests passed (missing fields return null/empty, same-day delivery)")


def test_sample_3():
    """Test Sample 3: 'Call for rate' results in null rate fields, reefer equipment."""
    results = parse_load_email(SAMPLE_EMAIL_3)

    assert len(results) == 1, f"Expected 1 load, got {len(results)}"
    load = results[0]

    assert load["origin_city"] == "Akron", f"Expected origin_city 'Akron', got '{load['origin_city']}'"
    assert load["origin_state"] == "OH", f"Expected origin_state 'OH', got '{load['origin_state']}'"
    assert load["destination_city"] == "Nashville", f"Expected destination_city 'Nashville', got '{load['destination_city']}'"
    assert load["destination_state"] == "TN", f"Expected destination_state 'TN', got '{load['destination_state']}'"

    # Call for rate -> null
    assert load["rate_total"] is None, f"Expected rate_total None (Call for rate), got {load['rate_total']}"
    assert load["rate_per_mile"] is None, f"Expected rate_per_mile None (Call for rate), got {load['rate_per_mile']}"

    # Equipment type = Reefer
    assert load["equipment_type"] == "Reefer", f"Expected equipment 'Reefer', got '{load['equipment_type']}'"

    # Has email
    assert load["contact_email"] == "dispatch@summitcoldchain.com", f"Expected email 'dispatch@summitcoldchain.com', got '{load['contact_email']}'"

    # No delivery date
    assert load["delivery_date"] == "", f"Expected empty delivery_date, got '{load['delivery_date']}'"

    # Has commodity
    assert load["commodity"] == "Frozen Foods", f"Expected commodity 'Frozen Foods', got '{load['commodity']}'"

    print("✓ Sample 3: All tests passed ('Call for rate' → null, Reefer equipment)")


def test_sample_4():
    """Test Sample 4: Multi-load email returns list of 2 dicts with correct data."""
    results = parse_load_email(SAMPLE_EMAIL_4)

    assert len(results) == 2, f"Expected 2 loads, got {len(results)}"

    # First load
    load1 = results[0]
    assert load1["origin_city"] == "Erie", f"Load 1: Expected origin_city 'Erie', got '{load1['origin_city']}'"
    assert load1["origin_state"] == "PA", f"Load 1: Expected origin_state 'PA', got '{load1['origin_state']}'"
    assert load1["destination_city"] == "Newark", f"Load 1: Expected destination_city 'Newark', got '{load1['destination_city']}'"
    assert load1["destination_state"] == "NJ", f"Load 1: Expected destination_state 'NJ', got '{load1['destination_state']}'"
    assert load1["mileage"] == 395, f"Load 1: Expected mileage 395, got {load1['mileage']}"
    assert load1["rate_total"] == 1383.00, f"Load 1: Expected rate_total 1383.00, got {load1['rate_total']}"
    assert load1["rate_per_mile"] == 3.50, f"Load 1: Expected rate_per_mile 3.50, got {load1['rate_per_mile']}"
    assert load1["broker_name"] == "Northeast Freight Partners", f"Load 1: Expected broker 'Northeast Freight Partners', got '{load1['broker_name']}'"
    assert load1["contact_email"] == "loads@nefp.com", f"Load 1: Expected email 'loads@nefp.com', got '{load1['contact_email']}'"
    assert load1["commodity"] == "Consumer Electronics", f"Load 1: Expected commodity 'Consumer Electronics', got '{load1['commodity']}'"

    # Second load
    load2 = results[1]
    assert load2["origin_city"] == "Pittsburgh", f"Load 2: Expected origin_city 'Pittsburgh', got '{load2['origin_city']}'"
    assert load2["origin_state"] == "PA", f"Load 2: Expected origin_state 'PA', got '{load2['origin_state']}'"
    assert load2["destination_city"] == "Boston", f"Load 2: Expected destination_city 'Boston', got '{load2['destination_city']}'"
    assert load2["destination_state"] == "MA", f"Load 2: Expected destination_state 'MA', got '{load2['destination_state']}'"
    assert load2["mileage"] == 572, f"Load 2: Expected mileage 572, got {load2['mileage']}"
    assert load2["rate_total"] == 1716.00, f"Load 2: Expected rate_total 1716.00, got {load2['rate_total']}"
    assert load2["rate_per_mile"] == 3.00, f"Load 2: Expected rate_per_mile 3.00, got {load2['rate_per_mile']}"
    assert load2["broker_name"] == "Bay State Logistics", f"Load 2: Expected broker 'Bay State Logistics', got '{load2['broker_name']}'"
    assert load2["broker_mc_number"] == "MC-672143", f"Load 2: Expected MC# 'MC-672143', got '{load2['broker_mc_number']}'"

    # Second load has no commodity or email
    assert load2["commodity"] == "", f"Load 2: Expected empty commodity, got '{load2['commodity']}'"
    assert load2["contact_email"] == "", f"Load 2: Expected empty contact_email, got '{load2['contact_email']}'"

    print("✓ Sample 4: All tests passed (multi-load email returns 2 dicts)")


def test_rate_calculation():
    """Test that rate_per_mile is calculated when not provided."""
    # Create a test email without rate_per_mile
    test_email = """
    Load 1 of 1

    Origin: Test, OH
    Destination: Test, PA
    Trip: 100 mi

    Equipment: Van

    Rate: $350.00

    Company: Test Company
    """

    results = parse_load_email(test_email)
    assert len(results) == 1
    load = results[0]

    assert load["rate_total"] == 350.00, f"Expected rate_total 350.00, got {load['rate_total']}"
    assert load["rate_per_mile"] == 3.50, f"Expected calculated rate_per_mile 3.50, got {load['rate_per_mile']}"

    print("✓ Rate calculation test passed")


def test_punctuated_cities():
    """Test cities with hyphens, apostrophes, periods, slashes."""
    test_email = """
    Load 1 of 1

    Origin: St. Louis, MO
    Destination: Winston-Salem, NC
    Trip: 650 mi

    Equipment: Van
    Rate: $1,950.00

    Company: Test Company
    """

    results = parse_load_email(test_email)
    assert len(results) == 1
    load = results[0]

    assert load["origin_city"] == "St. Louis", f"Expected 'St. Louis', got '{load['origin_city']}'"
    assert load["origin_state"] == "MO", f"Expected 'MO', got '{load['origin_state']}'"
    assert load["destination_city"] == "Winston-Salem", f"Expected 'Winston-Salem', got '{load['destination_city']}'"
    assert load["destination_state"] == "NC", f"Expected 'NC', got '{load['destination_state']}'"

    # Test apostrophe
    test_email2 = """
    Load 1 of 1

    Origin: O'Fallon, IL
    Destination: Port St. Lucie, FL
    Trip: 1100 mi

    Equipment: Van
    Rate: $3,300.00

    Company: Test Company
    """

    results2 = parse_load_email(test_email2)
    assert len(results2) == 1
    load2 = results2[0]

    assert load2["origin_city"] == "O'Fallon", f"Expected \"O'Fallon\", got '{load2['origin_city']}'"
    assert load2["destination_city"] == "Port St. Lucie", f"Expected 'Port St. Lucie', got '{load2['destination_city']}'"

    print("✓ Punctuated city names test passed")


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "=" * 60)
    print("Running Unit Tests")
    print("=" * 60 + "\n")

    test_sample_1()
    test_sample_2()
    test_sample_3()
    test_sample_4()
    test_rate_calculation()
    test_punctuated_cities()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


def demo_parse_all_samples():
    """Parse all sample emails and print results."""
    import json

    samples = [
        ("Sample 1 - Full details", SAMPLE_EMAIL_1),
        ("Sample 2 - Missing fields", SAMPLE_EMAIL_2),
        ("Sample 3 - Call for rate", SAMPLE_EMAIL_3),
        ("Sample 4 - Multi-load", SAMPLE_EMAIL_4),
    ]

    print("\n" + "=" * 60)
    print("Parsing All Sample Emails")
    print("=" * 60)

    for name, email in samples:
        print(f"\n--- {name} ---")
        results = parse_load_email(email)
        print(f"Found {len(results)} load(s):")
        for i, load in enumerate(results, 1):
            print(f"\nLoad {i}:")
            print(json.dumps(load, indent=2))


if __name__ == "__main__":
    # Run tests
    run_all_tests()

    # Demo parsing all samples
    demo_parse_all_samples()
