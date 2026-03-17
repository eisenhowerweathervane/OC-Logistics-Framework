"""FMCSA Hours of Service state machine for chain optimization.

Tracks driver HOS compliance per FMCSA regulations:
- 11-hour driving limit
- 14-hour on-duty window
- 70-hour/8-day cap
- 30-minute break after 8 consecutive hours of driving
- 10-hour off-duty rest period resets drive/duty clocks
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HOSState:
    """Immutable snapshot of a driver's Hours of Service clocks."""

    drive_hours_remaining: float = 11.0
    duty_hours_remaining: float = 14.0
    weekly_hours_remaining: float = 70.0
    consecutive_drive_hours: float = 0.0
    needs_break: bool = False
    needs_rest: bool = False


def _break_needed(state: HOSState, drive_time: float) -> bool:
    """Return True if a mandatory 30-min break is required for this leg."""
    return state.consecutive_drive_hours + drive_time > 8.0


def time_with_break(state: HOSState, drive_time: float, dwell_time: float) -> float:
    """Calculate total on-duty time including mandatory 30-min break if needed.

    If consecutive_drive_hours + drive_time > 8.0, a 0.5-hour break is added.
    Returns drive_time + dwell_time + (0.5 if break needed else 0).
    """
    extra = 0.5 if _break_needed(state, drive_time) else 0.0
    return drive_time + dwell_time + extra


def can_complete_leg(state: HOSState, drive_time: float, on_duty_time: float) -> bool:
    """Check whether the driver can complete a leg given current HOS state.

    Args:
        state: Current HOS state.
        drive_time: Hours of driving required.
        on_duty_time: Total on-duty hours (driving + dwell/loading).

    Returns:
        True if the leg fits within all HOS limits.
    """
    break_penalty = 0.5 if _break_needed(state, drive_time) else 0.0
    effective_on_duty = on_duty_time + break_penalty

    if drive_time > state.drive_hours_remaining:
        return False
    if effective_on_duty > state.duty_hours_remaining:
        return False
    if effective_on_duty > state.weekly_hours_remaining:
        return False
    return True


def apply_leg(state: HOSState, drive_time: float, on_duty_time: float) -> HOSState:
    """Return a new HOSState after completing a leg.

    Args:
        state: Current HOS state.
        drive_time: Hours of driving consumed.
        on_duty_time: Total on-duty hours consumed (driving + dwell).

    Returns:
        New HOSState with updated clocks.
    """
    took_break = _break_needed(state, drive_time)
    break_penalty = 0.5 if took_break else 0.0
    effective_on_duty = on_duty_time + break_penalty

    new_drive = state.drive_hours_remaining - drive_time
    new_duty = state.duty_hours_remaining - effective_on_duty
    new_weekly = state.weekly_hours_remaining - effective_on_duty

    # If a break was taken, consecutive resets before adding this leg's drive
    if took_break:
        new_consecutive = drive_time
    else:
        new_consecutive = state.consecutive_drive_hours + drive_time

    return HOSState(
        drive_hours_remaining=new_drive,
        duty_hours_remaining=new_duty,
        weekly_hours_remaining=new_weekly,
        consecutive_drive_hours=new_consecutive,
        needs_break=new_consecutive >= 8.0,
        needs_rest=new_drive <= 0 or new_duty <= 0,
    )


def apply_rest(state: HOSState) -> HOSState:
    """Apply a 10-hour rest period, resetting drive and duty clocks.

    Weekly hours are NOT reset (only a 34-hour restart does that).
    """
    return HOSState(
        drive_hours_remaining=11.0,
        duty_hours_remaining=14.0,
        weekly_hours_remaining=state.weekly_hours_remaining,
        consecutive_drive_hours=0.0,
        needs_break=False,
        needs_rest=False,
    )
