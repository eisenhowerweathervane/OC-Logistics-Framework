"""Tests for FMCSA Hours of Service state machine."""

import pytest
from optimizer.hos_model import (
    HOSState,
    can_complete_leg,
    apply_leg,
    apply_rest,
    time_with_break,
)


def test_fresh_driver_state():
    state = HOSState()
    assert state.drive_hours_remaining == 11.0
    assert state.duty_hours_remaining == 14.0
    assert state.weekly_hours_remaining == 70.0
    assert state.consecutive_drive_hours == 0.0
    assert state.needs_break is False
    assert state.needs_rest is False


def test_can_complete_short_leg():
    state = HOSState()
    assert can_complete_leg(state, drive_time=2.0, on_duty_time=3.5) is True


def test_cannot_exceed_drive_limit():
    state = HOSState()
    assert can_complete_leg(state, drive_time=12.0, on_duty_time=12.0) is False


def test_cannot_exceed_duty_limit():
    state = HOSState()
    # 5hr drive + 10hr dwell = 15hr on-duty exceeds 14hr window
    assert can_complete_leg(state, drive_time=5.0, on_duty_time=15.0) is False


def test_apply_leg_deducts_hours():
    state = HOSState()
    new = apply_leg(state, drive_time=3.0, on_duty_time=4.5)
    assert new.drive_hours_remaining == 8.0
    assert new.duty_hours_remaining == 9.5
    assert new.weekly_hours_remaining == 65.5
    assert new.consecutive_drive_hours == 3.0


def test_mandatory_break_after_8hrs():
    # First leg: 7hr drive
    state = HOSState()
    state = apply_leg(state, drive_time=7.0, on_duty_time=7.0)
    assert state.consecutive_drive_hours == 7.0

    # Second leg: 2hr drive would push consecutive past 8, requires 30-min break
    total = time_with_break(state, drive_time=2.0, dwell_time=0.5)
    assert total == 3.0  # 2.0 drive + 0.5 dwell + 0.5 break

    # can_complete_leg accounts for the break
    assert can_complete_leg(state, drive_time=2.0, on_duty_time=2.5) is True

    new = apply_leg(state, drive_time=2.0, on_duty_time=2.5)
    # Break was taken so consecutive resets then adds 2.0
    assert new.consecutive_drive_hours == 2.0
    # duty deducted extra 0.5 for break: 7.0 - (2.5 + 0.5) = 4.0
    assert new.duty_hours_remaining == 4.0


def test_rest_resets_drive_and_duty():
    state = HOSState()
    state = apply_leg(state, drive_time=10.0, on_duty_time=13.0)
    weekly_before = state.weekly_hours_remaining

    rested = apply_rest(state)
    assert rested.drive_hours_remaining == 11.0
    assert rested.duty_hours_remaining == 14.0
    assert rested.consecutive_drive_hours == 0.0
    assert rested.needs_break is False
    assert rested.needs_rest is False
    assert rested.weekly_hours_remaining == weekly_before


def test_weekly_cap_respected():
    state = HOSState(weekly_hours_remaining=5.0)
    assert can_complete_leg(state, drive_time=6.0, on_duty_time=6.0) is False
    assert can_complete_leg(state, drive_time=4.0, on_duty_time=5.0) is True


def test_multi_leg_day():
    state = HOSState()
    # Leg 1: 3hr drive, 1hr dwell
    state = apply_leg(state, drive_time=3.0, on_duty_time=4.0)
    assert state.drive_hours_remaining == 8.0

    # Leg 2: 3hr drive, 1hr dwell
    state = apply_leg(state, drive_time=3.0, on_duty_time=4.0)
    assert state.drive_hours_remaining == 5.0

    # Leg 3: 2hr drive, 0.5hr dwell
    assert can_complete_leg(state, drive_time=2.0, on_duty_time=2.5) is True
    state = apply_leg(state, drive_time=2.0, on_duty_time=2.5)
    assert state.drive_hours_remaining == 3.0
    assert state.duty_hours_remaining == 3.5


def test_multi_day_with_rest():
    state = HOSState()
    # Day 1: drive 11 hours
    state = apply_leg(state, drive_time=11.0, on_duty_time=13.0)
    assert state.needs_rest is True
    assert state.drive_hours_remaining == 0.0

    # Rest
    state = apply_rest(state)
    assert state.drive_hours_remaining == 11.0
    assert state.duty_hours_remaining == 14.0
    assert state.weekly_hours_remaining == 56.5  # 70 - 13 - 0.5 (break)

    # Day 2: drive some more
    assert can_complete_leg(state, drive_time=5.0, on_duty_time=6.0) is True
    state = apply_leg(state, drive_time=5.0, on_duty_time=6.0)
    assert state.drive_hours_remaining == 6.0
    assert state.weekly_hours_remaining == 50.5
