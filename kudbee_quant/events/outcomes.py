"""Forward-outcome measurement — strictly forward-looking, no lookahead.

Given an event at bar t, outcomes are measured over bars t+1..t+k. We never
peek at the event bar's own future inside its features; the outcome columns
are explicitly the *future* and are only ever used as the thing being
predicted, never as an input.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return(close: pd.Series, k: int) -> pd.Series:
    """Return from each bar's close to the close k bars later (NaN at the tail)."""
    if k < 1:
        raise ValueError("k must be >= 1")
    fwd = close.shift(-k) / close - 1.0
    return fwd


def forward_mfe_mae(df: pd.DataFrame, k: int) -> pd.DataFrame:
    """Max favorable / adverse excursion over the next k bars (long-perspective).

    mfe = (max high over t+1..t+k) / close_t - 1
    mae = (min low  over t+1..t+k) / close_t - 1
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    mfe = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    for t in range(n - 1):
        end = min(t + k, n - 1)
        window_hi = high[t + 1:end + 1]
        window_lo = low[t + 1:end + 1]
        if window_hi.size:
            mfe[t] = window_hi.max() / close[t] - 1.0
            mae[t] = window_lo.min() / close[t] - 1.0
    return pd.DataFrame({"mfe": mfe, "mae": mae}, index=df.index)


def add_forward_outcomes(df: pd.DataFrame, horizons=(1, 4, 12, 24)) -> pd.DataFrame:
    """Add forward return columns (fwd_ret_{k}) and direction (fwd_up_{k})."""
    out = df.copy()
    for k in horizons:
        r = forward_return(out["close"], k)
        out[f"fwd_ret_{k}"] = r
        out[f"fwd_up_{k}"] = (r > 0).where(r.notna())
    return out
