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
