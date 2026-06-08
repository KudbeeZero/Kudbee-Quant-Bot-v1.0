"""Indicators for the BTMM/PVSRA scenarios — all strictly causal (no lookahead).

EMAs use only past data by construction. Swing pivots are confirmed only
after ``right`` bars have passed, and we expose them shifted so a pivot is
known only once it could actually be seen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# BTMM EMA stack.
EMA_PERIODS = (5, 13, 50, 200, 800)


def add_emas(df: pd.DataFrame, periods=EMA_PERIODS) -> pd.DataFrame:
    """Add ema_{p} columns for each period (causal exponential MA on close)."""
    out = df.copy()
    for p in periods:
        out[f"ema_{p}"] = out["close"].ewm(span=p, adjust=False).mean()
    return out


def cross_up(fast: pd.Series, slow: pd.Series) -> pd.Series:
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))


def cross_down(fast: pd.Series, slow: pd.Series) -> pd.Series:
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))


def swing_pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    """Confirmed swing highs/lows, exposed only after confirmation (no lookahead).

    A bar i is a swing high if its high is the max of [i-left, i+right]. That
    can only be known at bar i+right, so we place the marker at i+right and
    record the pivot's price/index there. Adds: swing_high_price,
    swing_low_price (the most recent confirmed pivot, forward-filled).
    """
    out = df.copy()
    high = out["high"].to_numpy()
    low = out["low"].to_numpy()
    n = len(out)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    for i in range(left, n - right):
        window_hi = high[i - left:i + right + 1]
        window_lo = low[i - left:i + right + 1]
        if high[i] == window_hi.max() and (window_hi.argmax() == left):
            sh[i + right] = high[i]   # known only at i+right
        if low[i] == window_lo.min() and (window_lo.argmin() == left):
            sl[i + right] = low[i]
    out["new_swing_high"] = sh
    out["new_swing_low"] = sl
    out["swing_high_price"] = pd.Series(sh, index=out.index).ffill()
    out["swing_low_price"] = pd.Series(sl, index=out.index).ffill()
    out["prev_swing_high_price"] = pd.Series(sh, index=out.index).ffill().shift(1).where(
        pd.Series(sh, index=out.index).notna()).ffill()
    return out
