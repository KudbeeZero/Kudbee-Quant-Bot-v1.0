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


def trade_date(ts_utc: pd.Series) -> pd.Series:
    """The exchange TRADE DATE of each UTC timestamp (CME Globex / FX rollover).

    Session-gapped venues stamp the overnight session with the date it
    SETTLES: the Globex day runs 18:00 ET -> ~17:00 ET next day, so Sunday
    18:00 opens MONDAY's trade date. Shifting the NY wall clock +6h puts the
    day boundary at 18:00 ET — the Globex open — and is the identity for
    RTH-only instruments (09:30-16:00 ET). Grouping daily levels by calendar
    date instead creates a tiny Sunday "stub day" whose range poisons Monday's
    PDH/PDL/pivots/ADR (see docs/research/tradfi_session_levels.md).
    NOT +7h (a 17:00-ET boundary): Yahoo FX prints a Friday 17:00 close bar
    that a 17:00 boundary turns into a one-bar "Saturday" — Monday's previous
    day would then have zero range. Bars in [17:00, 18:00) belong to the
    closing day. For 24/7 crypto this would move the day boundary to 18:00 ET,
    so it is OPT-IN and never the default.
    """
    ny = pd.to_datetime(ts_utc, utc=True).dt.tz_convert(NY)
    return (ny.dt.tz_localize(None) + pd.Timedelta(hours=6)).dt.date
