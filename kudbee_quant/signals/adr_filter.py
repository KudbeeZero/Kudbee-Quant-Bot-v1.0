"""ADR exhaustion filter — don't chase a move that's already spent its daily range.

ADR = mean of the last 14 COMPLETE daily (high-low) ranges. "Consumed" = today's range
(high-low since UTC midnight) / ADR. When a large fraction of the ADR is already used,
the remaining runway for the day is thin, so a fresh entry is chasing. ``adr_gate``
returns ``True`` (allow) while consumed < ``threshold``, ``False`` (block) at/above it.

Reuses the ``pct_adr_used`` column when the frame already carries it (single source of
truth with ``levels.builder``); otherwise computes ADR from a daily resample of the raw
OHLCV.

FAIL-OPEN: ADR missing / zero / fewer than 5 complete daily bars -> consumed ``0.0`` and
the gate allows. A data gap never blocks every entry.
"""
from __future__ import annotations

import pandas as pd

ADR_DAYS = 14
_MIN_DAILY_BARS = 5


def _daily_ranges(df) -> pd.Series:
    d = df.copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.set_index("timestamp").sort_index()
    daily = pd.DataFrame({
        "high": d["high"].resample("1D").max(),
        "low": d["low"].resample("1D").min(),
    }).dropna()
    return daily["high"] - daily["low"]


def adr_consumed_pct(df) -> float:
    """Fraction of the 14-day ADR consumed by today's range so far (>= 0.0)."""
    try:
        if df is None or len(df) == 0:
            return 0.0
        cols = getattr(df, "columns", [])
        # Prefer the precomputed column (levels.builder) — single source of truth.
        if "pct_adr_used" in cols:
            v = pd.to_numeric(df["pct_adr_used"], errors="coerce").dropna()
            if len(v):
                return float(max(0.0, v.iloc[-1]))
        if "timestamp" not in cols:
            return 0.0
        ranges = _daily_ranges(df)
        if len(ranges) < _MIN_DAILY_BARS:
            return 0.0
        today_range = float(ranges.iloc[-1])           # last (possibly partial) day
        adr = float(ranges.iloc[:-1].tail(ADR_DAYS).mean())   # prior complete days
        if not adr or adr != adr or adr <= 0:
            return 0.0
        return max(0.0, today_range / adr)
    except Exception:
        return 0.0


def adr_gate(df, direction, threshold: float = 0.75) -> bool:
    """``True`` = allow (range not yet exhausted); ``False`` = block.

    ``direction`` is accepted for API symmetry / future direction-aware use; ADR
    exhaustion is currently symmetric (a spent range is spent either way).
    """
    try:
        return adr_consumed_pct(df) < float(threshold)
    except Exception:
        return True
