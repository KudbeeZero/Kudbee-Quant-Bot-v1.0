"""Tests for the binary-event gate (kudbee_quant.intelligence.event_calendar).

Pure datetime logic — every call pins ``now`` explicitly so the suite is
deterministic and never depends on the wall clock. Anchored to the seeded
``UPCOMING_EVENTS`` (Micron earnings @ 2026-06-24T20:00:00Z).
"""
from __future__ import annotations

from datetime import datetime, timezone

from kudbee_quant.intelligence.event_calendar import (
    get_blocking_event,
    is_friday_close_window,
    is_monday_open_window,
)

MICRON_UTC = datetime(2026, 6, 24, 20, 0, tzinfo=timezone.utc)  # seeded high-impact event


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# --- get_blocking_event --------------------------------------------------

def test_blocks_3h_before_event():
    """3h before Micron (inside the default 4h-before window) -> blocked."""
    now = _utc(2026, 6, 24, 17, 0)  # 3h before 20:00
    ev = get_blocking_event(hours_before=4.0, now=now)
    assert ev is not None
    assert ev["name"] == "Micron earnings"


def test_clear_6h_before_event():
    """6h before Micron (outside the 4h window, and PCE is days away) -> clear."""
    now = _utc(2026, 6, 24, 14, 0)  # 6h before 20:00
    assert get_blocking_event(hours_before=4.0, now=now) is None


def test_blocks_30min_after_event():
    """30min AFTER Micron (inside the default 1h-after window) -> still blocked."""
    now = _utc(2026, 6, 24, 20, 30)  # 0.5h after 20:00
    ev = get_blocking_event(hours_before=4.0, hours_after=1.0, now=now)
    assert ev is not None
    assert ev["name"] == "Micron earnings"


# --- is_friday_close_window ----------------------------------------------

def test_friday_close_window_true_friday_1830():
    assert is_friday_close_window(now=_utc(2026, 6, 26, 18, 30)) is True  # Fri 18:30


def test_friday_close_window_false_thursday_1830():
    assert is_friday_close_window(now=_utc(2026, 6, 25, 18, 30)) is False  # Thu 18:30


# --- is_monday_open_window -----------------------------------------------

def test_monday_open_window_true_monday_0100():
    assert is_monday_open_window(now=_utc(2026, 6, 29, 1, 0)) is True  # Mon 01:00


def test_monday_open_window_false_monday_0300():
    assert is_monday_open_window(now=_utc(2026, 6, 29, 3, 0)) is False  # Mon 03:00


# --- integration: the gate short-circuits paper_scan ---------------------

def test_paper_scan_blocks_entries_when_event_near(monkeypatch):
    """A blocking event makes paper_scan return [] BEFORE any signal work — no
    journal/client touched. (Re-patches the gate the autouse conftest pins open.)"""
    import kudbee_quant.paper.paper as pp
    monkeypatch.setattr(pp, "get_blocking_event",
                        lambda *a, **k: {"name": "FOMC", "impact": "high",
                                         "datetime_utc": "2026-06-25T18:00:00Z"})
    monkeypatch.setattr(pp, "hours_until_event", lambda *a, **k: 2.5)
    # Telegram is unconfigured in tests, so notify_scan_blocked is a silent no-op.
    assert pp.paper_scan(["BTCUSDT"]) == []
