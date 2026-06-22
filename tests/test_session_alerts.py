"""Tests for session crossover alerts. No network — synthetic last-bar frames at
chosen NY times drive the firing logic, and a capture function records messages."""
from __future__ import annotations

import pandas as pd

from kudbee_quant.notifications.session_alerts import (
    build_session_alert,
    check_and_fire_session_alerts,
    _level_line,
)


def _frame_at(ny_str: str, **levels) -> pd.DataFrame:
    """One-row frame whose bar timestamp is `ny_str` (America/New_York), stored UTC
    like real klines. Level columns default to far-away so they don't show."""
    ts_utc = pd.Timestamp(ny_str, tz="America/New_York").tz_convert("UTC")
    row = {"timestamp": ts_utc, "close": 100.0, "atr": 1.0,
           "weekly_open": 98.0, "monthly_open": 50.0, "pivot_pp": 50.0,
           "adr_high": 50.0, "adr_low": 50.0, "asian_high": 50.0, "asian_low": 50.0}
    row.update(levels)
    return pd.DataFrame([row])


def _fire(df):
    sent: list[str] = []
    fired = check_and_fire_session_alerts({"BTCUSDT": df}, notify_fn=sent.append)
    return fired, sent


def test_sunday_asia_open_fires_with_week_start():
    fired, sent = _fire(_frame_at("2026-06-21 20:00"))   # Sunday 20:00 ET
    assert fired == ["asia"]
    assert "Week starts" in sent[0] and "ASIA Open" in sent[0]


def test_weekday_asia_open_fires_without_week_start():
    fired, sent = _fire(_frame_at("2026-06-22 20:00"))   # Monday 20:00 ET
    assert fired == ["asia"]
    assert "Week starts" not in sent[0]


def test_london_open_fires():
    fired, sent = _fire(_frame_at("2026-06-22 02:00"))   # Monday 02:00 ET
    assert fired == ["london"] and "LONDON Open" in sent[0]


def test_ny_open_fires():
    fired, sent = _fire(_frame_at("2026-06-22 08:00"))   # Monday 08:00 ET
    assert fired == ["ny"] and "NY Open" in sent[0]


def test_non_session_hour_fires_nothing():
    fired, sent = _fire(_frame_at("2026-06-22 10:00"))   # Monday 10:00 ET
    assert fired == [] and sent == []


def test_weekly_bias_above_and_below():
    above = build_session_alert("ny", "🇺🇸", "tip", is_week_start=False,
                                last_rows={"BTCUSDT": _frame_at("2026-06-22 08:00",
                                                                close=100.0, weekly_open=98.0).iloc[-1]})
    below = build_session_alert("ny", "🇺🇸", "tip", is_week_start=False,
                                last_rows={"BTCUSDT": _frame_at("2026-06-22 08:00",
                                                                close=100.0, weekly_open=110.0).iloc[-1]})
    assert "ABOVE weekly open" in above
    assert "BELOW weekly open" in below


def test_level_line_proximity_filter():
    # within 1.5 ATR (atr=1.0) -> shown; beyond -> omitted
    assert _level_line("M0", 100.5, current=100.0, atr=1.0) is not None
    assert _level_line("M0", 105.0, current=100.0, atr=1.0) is None
    assert _level_line("M0", None, current=100.0, atr=1.0) is None


def test_nearby_level_appears_in_message():
    df = _frame_at("2026-06-22 08:00", close=100.0, monthly_open=100.4)  # within 1.5 ATR
    _, sent = _fire(df)
    assert "M0 Monthly open" in sent[0]


def test_price_format_no_scientific_notation():
    # big price near a level -> uses _g (comma thousands), never "e+04"
    df = _frame_at("2026-06-22 08:00", close=64170.0, atr=200.0,
                   weekly_open=64000.0, monthly_open=64100.0)
    _, sent = _fire(df)
    assert "64,170" in sent[0]
    assert "e+0" not in sent[0].lower()


def test_empty_input_is_safe():
    assert check_and_fire_session_alerts({}, notify_fn=lambda m: None) == []


def test_nan_atr_suppresses_levels_not_crash():
    # NaN atr must not slip every level past the 1.5-ATR proximity gate (or crash).
    df = _frame_at("2026-06-22 08:00", close=100.0, atr=float("nan"), monthly_open=100.4)
    fired, sent = _fire(df)
    assert fired == ["ny"]
    assert "M0 Monthly open" not in sent[0]   # atr unknown -> no proximity claim
