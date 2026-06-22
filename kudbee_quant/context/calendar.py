"""Time-of-day / session context anchored to New York local time (DST-correct).

ICT/Traders Reality sessions and killzones are defined in New York local
time. Hardcoding a single UTC offset is wrong half the year (US/EU DST switch
on different dates), so we convert UTC -> America/New_York with stdlib
zoneinfo and classify from the NY wall clock. No external dependency.

Killzones (NY local time):
  asian        20:00-22:00      london_open  02:00-05:00
  ny_forex     07:00-10:00      ny_indices   08:30-11:00
  london_close 10:00-12:00      overlap      08:00-11:00 (London-NY premium)
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

NY = ZoneInfo("America/New_York")

# Broad session windows (NY local hour, [start, end)); asian wraps midnight.
_SESSIONS = {
    "asian": (19, 2),      # Tokyo/HK evening NY-time, wraps midnight
    "london": (2, 8),
    "ny": (8, 17),
}

# Killzones as (start_minutes, end_minutes) from NY midnight.
_KILLZONES = {
    "asian": (20 * 60, 22 * 60),
    "london_open": (2 * 60, 5 * 60),
    "ny_forex": (7 * 60, 10 * 60),
    "ny_indices": (8 * 60 + 30, 11 * 60),
    "london_close": (10 * 60, 12 * 60),
}
_OVERLAP = (8 * 60, 11 * 60)  # London-NY premium window


def _ny_parts(ts_utc: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (NY hour, NY minute-of-day, NY day-of-week) for UTC timestamps."""
    ny = pd.to_datetime(ts_utc, utc=True).dt.tz_convert(NY)
    minute_of_day = ny.dt.hour * 60 + ny.dt.minute
    return ny.dt.hour, minute_of_day, ny.dt.dayofweek


def add_time_context(df: pd.DataFrame) -> pd.DataFrame:
    """Annotate bars with NY-time session/killzone/day-of-week features.

    Adds: ny_hour, ny_minute, day_of_week (0=Mon), session, killzone,
    in_overlap, minutes_into_ny (minutes since 08:00 NY open; NaN if before),
    week_phase.
    """
    if "timestamp" not in df.columns:
        raise ValueError("add_time_context requires a 'timestamp' column (UTC)")
    out = df.copy()
    hour, mod, dow = _ny_parts(out["timestamp"])
    out["ny_hour"] = hour
    out["ny_minute"] = mod
    out["day_of_week"] = dow

    def _in(window, h):
        s, e = window
        return (h >= s) | (h < e) if s > e else (h >= s) & (h < e)

    out["session"] = np.select(
        [_in(_SESSIONS["asian"], hour), _in(_SESSIONS["london"], hour), _in(_SESSIONS["ny"], hour)],
        ["asian", "london", "ny"],
        default="off",
    )

    kz = pd.Series("none", index=out.index, dtype=object)
    for name, (s, e) in _KILLZONES.items():
        kz = kz.mask((mod >= s) & (mod < e) & (kz == "none"), name)
    out["killzone"] = kz
    out["in_overlap"] = (mod >= _OVERLAP[0]) & (mod < _OVERLAP[1])

    ny_open = 8 * 60
    out["minutes_into_ny"] = (mod - ny_open).where(mod >= ny_open)

    # Weekly MM-template phase by day-of-week.
    phase = {0: "mon_range", 1: "tue_expansion", 2: "wed_expansion",
             3: "thu_expansion", 4: "fri_distribution", 5: "weekend", 6: "weekend"}
    out["week_phase"] = out["day_of_week"].map(phase)
    return out


def ny_session_date(ts_utc: pd.Series) -> pd.Series:
    """The New-York calendar date of each UTC timestamp (for daily grouping)."""
    return pd.to_datetime(ts_utc, utc=True).dt.tz_convert(NY).dt.date


# The trading DAY rolls at the NEW YORK session open — 08:00 New York, the canonical
# start of the NY window (``_SESSIONS["ny"]``). NY is the daily reference the desk
# reckons from, so anchor "today" here instead of at UTC/NY midnight. (DST-correct via
# NY; 08:00 NY = 12:00 UTC in summer, 13:00 UTC in winter.) Changing this hour is the
# ONLY lever for what "today" counts — it relabels the window; it never alters trades.
DAY_START_HOUR_NY = _SESSIONS["ny"][0]   # 8


def session_day_start(now=None):
    """Instant the current trading day began: the most recent New York open
    (08:00 NY) at or before ``now``. Returns a tz-aware UTC ``datetime``."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone.utc)
    ny_now = now.astimezone(NY)
    start = ny_now.replace(hour=DAY_START_HOUR_NY, minute=0, second=0, microsecond=0)
    if ny_now < start:                       # before 08:00 NY -> day opened yesterday 08:00
        start -= timedelta(days=1)
    return start.astimezone(timezone.utc)


def complete_period_mask(counts: pd.Series, min_frac: float = 0.5) -> pd.Series:
    """True for periods whose bar count is "full" (>= ``min_frac`` x median).

    24/7 crypto periods all pass, so this is a no-op there. TradFi session
    calendars produce STUB periods — the Globex Sunday-evening reopen (~6 1h
    bars), holiday half-days — whose truncated ranges poison any prior-period
    reference level built from them (ADR, floor pivots, PDH/PDL): measured on
    CL=F the Sunday stubs depress ADR ~17% and hand Monday a 6-bar "prior day"
    (§29). Median-based so it adapts to the instrument and bar interval.
    """
    if counts.empty:
        return counts.astype(bool)
    return counts >= min_frac * float(counts.median())
