"""Market-maker cycle context computations (see package docstring)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Day-of-week index -> weekly MM-template phase (Tino's rough template).
# Monday/Tuesday often set the weekly extreme (accumulation / first move),
# midweek reverses, late week continues. A heuristic, labelled honestly.
_WEEKLY_PHASE = {
    0: "mon_accumulation",
    1: "tue_manipulation",
    2: "wed_reversal",
    3: "thu_continuation",
    4: "fri_distribution",
    5: "sat_weekend",
    6: "sun_weekend",
}


@dataclass(frozen=True)
class SessionWindows:
    """UTC hour windows [start, end) for each trading session.

    Defaults approximate the standard FX/crypto sessions. Asian is the
    "range box" that London/NY tend to sweep; it is allowed to wrap past
    midnight (start > end).
    """
    asian: tuple[int, int] = (23, 7)   # Tokyo, wraps midnight
    london: tuple[int, int] = (7, 16)
    new_york: tuple[int, int] = (13, 21)


def _in_window(hour: pd.Series, window: tuple[int, int]) -> pd.Series:
    start, end = window
    if start <= end:
        return (hour >= start) & (hour < end)
    # wraps past midnight, e.g. 23 -> 7
    return (hour >= start) | (hour < end)


def label_sessions(df: pd.DataFrame, windows: SessionWindows | None = None) -> pd.DataFrame:
    """Add per-bar session membership and the day's Asian-range box.

    Adds columns: in_asian, in_london, in_ny, session (primary label),
    asian_high, asian_low (that day's Asian range, available to later bars).
    """
    windows = windows or SessionWindows()
    _require_timestamp(df)
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    hour = ts.dt.hour

    out["in_asian"] = _in_window(hour, windows.asian)
    out["in_london"] = _in_window(hour, windows.london)
    out["in_ny"] = _in_window(hour, windows.new_york)

    # Primary label by priority: NY > London > Asian > off-hours.
    out["session"] = np.select(
        [out["in_ny"], out["in_london"], out["in_asian"]],
        ["new_york", "london", "asian"],
        default="off",
    )

    # Asian-range box — NO LOOKAHEAD. The completed session high/low is exposed
    # only AFTER the session ends (forward-filled through London/NY until the
    # next Asian session begins); it is NaN *during* the forming session, so a
    # bar can never see the final range before it exists. (A prior version
    # mapped the full-session max/min onto every bar of the day, which leaked
    # future info and produced absurd backtest Sharpes.)
    in_a = out["in_asian"].fillna(False).astype(bool)
    sess_id = (in_a & ~in_a.shift(fill_value=False)).cumsum()
    run_hi = out["high"].where(in_a).groupby(sess_id).cummax().ffill()
    run_lo = out["low"].where(in_a).groupby(sess_id).cummin().ffill()
    out["asian_high"] = run_hi.where(~in_a)
    out["asian_low"] = run_lo.where(~in_a)
    return out


def reference_levels(df: pd.DataFrame, trade_dates: bool = False) -> pd.DataFrame:
    """Add previous-day and previous-week high/low (PDH/PDL/PWH/PWL).

    These are the resting-liquidity levels MM cycles target. Each is the
    extreme of the *previous completed* period, so no lookahead.

    ``trade_dates``: group days by the exchange trade date (18:00-ET Globex boundary)
    instead of the UTC calendar date — for session-gapped TradFi venues, where
    the UTC Sunday holds only 1-2 bars and would otherwise become Monday's
    "previous day". Leave False for 24/7 crypto.
    """
    _require_timestamp(df)
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    # Periods are computed on explicit UTC wall-clock (tz stripped on purpose
    # so day/week boundaries are UTC midnight, not local-with-a-warning).
    naive = ts.dt.tz_localize(None)

    if trade_dates:
        from .calendar import trade_date
        day = trade_date(out["timestamp"])
    else:
        day = naive.dt.to_period("D")
    daily = (
        out.assign(_p=day)
        .groupby("_p")
        .agg(dh=("high", "max"), dl=("low", "min"))
        .sort_index()
    )
    daily["pdh"] = daily["dh"].shift(1)
    daily["pdl"] = daily["dl"].shift(1)
    out["pdh"] = day.map(daily["pdh"]).astype(float)
    out["pdl"] = day.map(daily["pdl"]).astype(float)

    week = naive.dt.to_period("W")
    weekly = (
        out.assign(_p=week)
        .groupby("_p")
        .agg(wh=("high", "max"), wl=("low", "min"))
        .sort_index()
    )
    weekly["pwh"] = weekly["wh"].shift(1)
    weekly["pwl"] = weekly["wl"].shift(1)
    out["pwh"] = week.map(weekly["pwh"]).astype(float)
    out["pwl"] = week.map(weekly["pwl"]).astype(float)
    return out


def detect_sweeps(df: pd.DataFrame) -> pd.DataFrame:
    """Detect liquidity sweeps (stop hunts) of reference levels.

    A bullish sweep: price wicks *below* a key low then closes back above it
    (sellers' stops grabbed -> potential reversal up). Bearish sweep is the
    mirror. Requires reference_levels() columns to be present.

    Adds: swept_low (bullish), swept_high (bearish), and a combined
    sweep_bias in {-1, 0, 1}.
    """
    needed = {"pdh", "pdl", "high", "low", "close"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"detect_sweeps needs columns {sorted(missing)} (run reference_levels first)")
    out = df.copy()

    low_levels = out[["pdl", "pwl", "asian_low"]] if "asian_low" in out else out[["pdl", "pwl"]]
    high_levels = out[["pdh", "pwh", "asian_high"]] if "asian_high" in out else out[["pdh", "pwh"]]

    # Bullish sweep: bar low pierced a level but close reclaimed above it.
    swept_low = ((out["low"].values[:, None] < low_levels.values)
                 & (out["close"].values[:, None] > low_levels.values))
    swept_high = ((out["high"].values[:, None] > high_levels.values)
                  & (out["close"].values[:, None] < high_levels.values))

    out["swept_low"] = np.nan_to_num(swept_low).any(axis=1)
    out["swept_high"] = np.nan_to_num(swept_high).any(axis=1)
    out["sweep_bias"] = out["swept_low"].astype(int) - out["swept_high"].astype(int)
    return out


def weekly_cycle_phase(df: pd.DataFrame) -> pd.DataFrame:
    """Add the weekly MM-template phase label from day-of-week."""
    _require_timestamp(df)
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    out["dow"] = ts.dt.dayofweek
    out["cycle_phase"] = out["dow"].map(_WEEKLY_PHASE)
    return out


def add_mm_context(df: pd.DataFrame, windows: SessionWindows | None = None,
                   trade_dates: bool = False) -> pd.DataFrame:
    """Apply the full MM-context pipeline in dependency order."""
    out = label_sessions(df, windows)
    out = reference_levels(out, trade_dates=trade_dates)
    out = detect_sweeps(out)
    out = weekly_cycle_phase(out)
    return out


def _require_timestamp(df: pd.DataFrame) -> None:
    if "timestamp" not in df.columns:
        raise ValueError("market-maker context requires a 'timestamp' column (UTC)")
