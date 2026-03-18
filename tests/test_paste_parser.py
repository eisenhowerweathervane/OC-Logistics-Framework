"""Tests for ingestion.dat_paste_parser — DAT load-board paste parser."""

import pytest

from ingestion.dat_paste_parser import parse_dat_paste


# ---------------------------------------------------------------------------
# Helpers — sample paste blocks
# ---------------------------------------------------------------------------

FULL_LOAD = """\
Dallas, TX → Houston, TX
240 mi
Rate: $720.00
$3.00/mi
Van
42,000 lbs
Pickup: 03/20/2026
08:00-14:00
Company: ABC Logistics
MC# 123456
214-555-1234
broker@abclogistics.com
"""

CALL_FOR_RATE_LOAD = """\
Atlanta, GA -> Nashville, TN
250 mi
Rate: Call
Reefer
30,000 lbs
Pickup: 04/01/2026
Company: Quick Freight
MC-654321
"""

PARTIAL_LOAD = """\
Chicago, IL to Memphis, TN
530 mi
"""

TWO_LOADS = FULL_LOAD.strip() + "\n\n" + CALL_FOR_RATE_LOAD.strip()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseDatPaste:
    def test_parses_basic_load(self):
        loads = parse_dat_paste(FULL_LOAD)
        assert len(loads) == 1
        load = loads[0]

        assert load.origin_city == "Dallas"
        assert load.origin_state == "TX"
        assert load.destination_city == "Houston"
        assert load.destination_state == "TX"
        assert load.mileage == 240
        assert load.rate_total == 720.00
        assert load.rate_per_mile == 3.00
        assert load.equipment_type == "Van"
        assert load.weight == 42000
        assert load.pickup_date == "2026-03-20"
        assert load.pickup_time_window == "08:00-14:00"
        assert load.broker_name == "ABC Logistics"
        assert load.broker_mc_number == "123456"
        assert load.contact_phone == "214-555-1234"
        assert load.contact_email == "broker@abclogistics.com"
        assert load.source == "paste"

    def test_parses_call_for_rate(self):
        loads = parse_dat_paste(CALL_FOR_RATE_LOAD)
        assert len(loads) == 1
        load = loads[0]

        assert load.origin_city == "Atlanta"
        assert load.origin_state == "GA"
        assert load.destination_city == "Nashville"
        assert load.destination_state == "TN"
        assert load.rate_total is None
        assert load.rate_per_mile is None
        assert load.equipment_type == "Reefer"
        assert load.broker_mc_number == "654321"

    def test_parses_multiple_loads(self):
        loads = parse_dat_paste(TWO_LOADS)
        assert len(loads) == 2
        assert loads[0].origin_city == "Dallas"
        assert loads[1].origin_city == "Atlanta"

    def test_empty_text_returns_empty(self):
        assert parse_dat_paste("") == []
        assert parse_dat_paste("   \n\n  ") == []

    def test_partial_data_returns_what_it_can(self):
        loads = parse_dat_paste(PARTIAL_LOAD)
        assert len(loads) == 1
        load = loads[0]

        assert load.origin_city == "Chicago"
        assert load.origin_state == "IL"
        assert load.destination_city == "Memphis"
        assert load.destination_state == "TN"
        assert load.mileage == 530
        assert load.rate_total is None
        assert load.source == "paste"


# ---------------------------------------------------------------------------
# Real DAT tabular format tests
# ---------------------------------------------------------------------------

DAT_REAL_PASTE = """\
Age
Rate
Trip
Origin
DH-O
Destination
DH-D
Pick Up
Equipment
Company
Contact
CS
DTP
4m
$1,100
246
Obetz, OH
(13)
Bardstown, KY
3/17
VR
44,500 lbs
53 ft - Full
USA TRUCK LLC
loadpostings@usa-truck.com
– CS
– DTP
7m
–
189
Columbus, OH
(0)
Lexington, KY
3/17
V
44,500 lbs
53 ft - Full
Subscribe for full access
– CS
– DTP
"""

DAT_SINGLE_LOAD = """\
Age
Rate
Trip
Origin
DH-O
Destination
Pick Up
Equipment
Company
Contact
CS
DTP
4m
$1,100
246
Obetz, OH
(13)
Bardstown, KY
3/17
VR
44,500 lbs
53 ft - Full
USA TRUCK LLC
loadpostings@usa-truck.com
– CS
– DTP
"""


class TestDatTabularFormat:
    def test_parses_two_loads(self):
        loads = parse_dat_paste(DAT_REAL_PASTE)
        assert len(loads) == 2

    def test_first_load_fields(self):
        loads = parse_dat_paste(DAT_REAL_PASTE)
        load = loads[0]
        assert load.origin_city == "Obetz"
        assert load.origin_state == "OH"
        assert load.destination_city == "Bardstown"
        assert load.destination_state == "KY"
        assert load.mileage == 246
        assert load.rate_total == 1100.00
        assert load.deadhead_miles == 13
        assert load.weight == 44500
        assert load.equipment_type == "Van"  # VR maps to Van
        assert load.broker_name == "USA TRUCK LLC"
        assert load.contact_email == "loadpostings@usa-truck.com"
        assert load.source == "paste"
        assert "2026" in load.pickup_date or "2027" in load.pickup_date  # year depends on current date

    def test_second_load_no_rate(self):
        loads = parse_dat_paste(DAT_REAL_PASTE)
        load = loads[1]
        assert load.origin_city == "Columbus"
        assert load.origin_state == "OH"
        assert load.destination_city == "Lexington"
        assert load.destination_state == "KY"
        assert load.mileage == 189
        assert load.rate_total is None  # "–" means no rate
        assert load.deadhead_miles == 0

    def test_single_dat_load(self):
        loads = parse_dat_paste(DAT_SINGLE_LOAD)
        assert len(loads) == 1
        assert loads[0].origin_city == "Obetz"
        assert loads[0].rate_total == 1100.00
