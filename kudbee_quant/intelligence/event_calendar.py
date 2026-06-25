"""Binary-event calendar — a read-only gate for the paper scanner.

Tino's methodology: do NOT open a new position right before (or right after) a
known high-impact scheduled event — earnings, PCE, NFP, FOMC. Those create
*binary* moves that invalidate the technical setup, so the scanner should sit
out rather than enter into a coin-flip.

This module answers ONE question: *given the current UTC time, is a high-impact
event inside the blocking window?* It has no side effects and never touches the
journal, the signals, or the network — it's pure datetime arithmetic over two
hardcoded lists:

  * ``UPCOMING_EVENTS`` — the owner-maintained dated list (the live source of
    truth; add/remove events here as the calendar moves).
  * ``RECURRING_EVENTS`` — the standing weekly/monthly schedule, documented for
    reference. The recurring *windows the scanner actually enforces today* are
    the Friday-close and Monday-open guards below (:func:`is_friday_close_window`
    / :func:`is_monday_open_window`); a fuller recurring-calendar check can be
    built on this table later.

Every public function takes an optional ``now`` so callers (and tests) can pin
the reference time; it defaults to the real ``datetime.now(timezone.utc)``.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Standing schedule (reference). day_of_week uses Python's convention
# (Monday=0 .. Sunday=6); hours/minutes are UTC. ``months=None`` = every month.
RECURRING_EVENTS = [
    # Every week
    {"name": "NFP", "day_of_week": 4,
     "hour_utc": 12, "minute_utc": 30,
     "months": None},  # First Friday each month

    {"name": "Core PCE", "day_of_week": 4,
     "hour_utc": 12, "minute_utc": 30,
     "months": None},  # Last Friday each month

    {"name": "Weekly close", "day_of_week": 4,
     "hour_utc": 20, "minute_utc": 0,
     "months": None},  # Every Friday NY close

    {"name": "Weekly open gap risk",
     "day_of_week": 0,
     "hour_utc": 0, "minute_utc": 0,
     "months": None},  # Every Monday open
]

# Owner-maintained dated list — the live source of truth for the event gate.
# Format: ISO-8601 UTC datetime ("...Z") + name + impact.
UPCOMING_EVENTS = [
    {"name": "Micron earnings",
     "datetime_utc": "2026-06-24T20:00:00Z",
     "impact": "high"},

    {"name": "Core PCE June",
     "datetime_utc": "2026-06-27T12:30:00Z",
     "impact": "high"},
]


def _parse(iso_utc: str) -> datetime:
    """Parse an ISO-8601 UTC string (trailing ``Z`` accepted) to an aware datetime."""
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))


def hours_until_event(event: dict, now: datetime | None = None) -> float:
    """Signed hours from ``now`` until ``event`` (negative once it has passed)."""
    now = now or datetime.now(timezone.utc)
    return (_parse(event["datetime_utc"]) - now).total_seconds() / 3600.0


def get_blocking_event(
    hours_before: float = 4.0,
    hours_after: float = 1.0,
    now: datetime | None = None,
) -> dict | None:
    """Return the first high-impact event inside the blocking window, else ``None``.

    ``hours_before``: block this many hours BEFORE an event.
    ``hours_after``: keep blocking this many hours AFTER it (price stays volatile
    post-event). Only ``impact == "high"`` events are considered.
    """
    now = now or datetime.now(timezone.utc)
    for event in UPCOMING_EVENTS:
        if event.get("impact") != "high":
            continue
        delta = hours_until_event(event, now)
        if -hours_after <= delta <= hours_before:
            return event
    return None


def is_friday_close_window(
    hours_before: float = 2.0,
    now: datetime | None = None,
) -> bool:
    """True within ``hours_before`` of the Friday 20:00 UTC weekly NY close."""
    now = now or datetime.now(timezone.utc)
    return now.weekday() == 4 and now.hour >= 20 - hours_before


def is_monday_open_window(
    hours: float = 2.0,
    now: datetime | None = None,
) -> bool:
    """True within ``hours`` after the Monday 00:00 UTC weekly open (gap risk)."""
    now = now or datetime.now(timezone.utc)
    return now.weekday() == 0 and now.hour < hours
