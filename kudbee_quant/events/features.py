"""Assemble the full context-feature frame every event study is built on.

Combines: NY-time session/killzone/day-of-week (calendar), market-maker
structure (sessions, PDH/PDL/PWH/PWL, sweeps — mm_cycle), holiday flags,
ATR, and the ICT reference opens (daily midnight-ET open, weekly Sun-18:00-ET
open). Distances to those opens are expressed in ATR units so they're
comparable across instruments.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..context.calendar import NY, add_time_context, ny_session_date, trade_date
from ..context.market_holidays import add_holiday_flags
from ..context.mm_cycle import add_mm_context
from ..signals import pvsra_vector_candles


def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-style ATR (simple rolling mean of true range)."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def _reference_opens(df: pd.DataFrame, trade_dates: bool = False) -> pd.DataFrame:
    """Add daily 'midnight ET' open and weekly 'Sun 18:00 ET' open (no lookahead)."""
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    ny = ts.dt.tz_convert(NY)
    # Session-gapped TradFi venues group days by the exchange trade date
    # (18:00-ET Globex boundary; Sunday evening belongs to Monday) so no Sunday stub
    # day forms; 24/7 crypto keeps the NY calendar date (validated default).
    out["ny_date"] = trade_date(out["timestamp"]) if trade_dates else ny_session_date(out["timestamp"])
    # UTC calendar date — the daily-open anchor (00:00 UTC), matching the
    # TradingView default the trader reads off their chart.
    out["utc_date"] = ts.dt.date

    # Daily open = open of the first bar of each UTC calendar date (00:00 UTC).
    # In trade-date mode, the first bar of the trade date instead — the actual
    # exchange daily open (Globex 18:00 ET / RTH 09:30 ET), since 00:00 UTC
    # falls mid-gap or mid-evening on session-gapped venues.
    day_key = "ny_date" if trade_dates else "utc_date"
    out["daily_open"] = out.groupby(day_key)["open"].transform("first")

    # Weekly open = open of the first bar on/after Sunday 18:00 NY each ICT week.
    # Define the ICT week id as the date of the most recent Sunday-18:00 anchor.
    anchor = ny - pd.to_timedelta((ny.dt.dayofweek + 1) % 7, unit="D")  # back to Sunday
    anchor = anchor.dt.normalize() + pd.Timedelta(hours=18)
    after = ny >= anchor
    week_anchor = anchor.where(after, anchor - pd.Timedelta(days=7))
    out["_week_id"] = week_anchor.dt.tz_convert("UTC").astype("int64")
    out["weekly_open"] = out.groupby("_week_id")["open"].transform("first")
    return out.drop(columns="_week_id")


def build_features(df: pd.DataFrame, pvsra_config=None, trade_dates: bool = False) -> pd.DataFrame:
    """Return ``df`` annotated with the full event-study context feature set.

    ``trade_dates``: anchor daily groupings (PDH/PDL, daily open, ny_date) to
    the exchange trade date instead of calendar dates — for session-gapped
    TradFi venues only (see context/calendar.trade_date). Default False keeps
    the validated 24/7 crypto behavior bit-identical.
    """
    if "timestamp" not in df.columns:
        raise ValueError("build_features requires a 'timestamp' column (UTC)")
    # mm_context first, then time_context, so the DST-correct NY 'session'
    # from the calendar overwrites mm_cycle's UTC-based label.
    out = add_mm_context(df, trade_dates=trade_dates)
    out = add_time_context(out)
    out = _reference_opens(out, trade_dates=trade_dates)
    out = add_holiday_flags(out, date_col="ny_date")
    out = pvsra_vector_candles(out, pvsra_config)

    out["atr"] = average_true_range(out)
    atr_safe = out["atr"].replace(0, np.nan)
    out["dist_daily_open_atr"] = (out["close"] - out["daily_open"]) / atr_safe
    out["dist_weekly_open_atr"] = (out["close"] - out["weekly_open"]) / atr_safe
    return out
