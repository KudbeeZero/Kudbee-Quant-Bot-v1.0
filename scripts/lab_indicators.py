"""Causal indicator helpers for the owner's confluence experiments.

Pure, no-lookahead functions used by the overnight candidate gates (Bollinger
Bands, KDJ, Fibonacci-confluence, spider/angled lines). These are NOT added to
the validated feature frame or the live confluence stack — they're computed
inside candidate callables so the harness can MEASURE whether they add edge
before anything ships. Every function uses only data up to bar t.

Honesty note (docs/MEMORY.md §2): the 10-factor stack is saturated and prior
indicator add-ons (incl. RSI divergence) diluted the edge. These exist to TEST
the owner's Bollinger/RSI/KDJ/Fib/spider ideas honestly, not to assume they help.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bollinger(df: pd.DataFrame, n: int = 20, k: float = 2.0):
    """(mid, upper, lower, pct_b, width) — causal SMA(n) ± k·std(n).

    pct_b = (close-lower)/(upper-lower): <0 below band, >1 above band.
    """
    c = df["close"]
    mid = c.rolling(n, min_periods=n).mean()
    sd = c.rolling(n, min_periods=n).std(ddof=0)
    upper, lower = mid + k * sd, mid - k * sd
    rng = (upper - lower).replace(0.0, np.nan)
    pct_b = (c - lower) / rng
    width = rng / mid.replace(0.0, np.nan)
    return mid, upper, lower, pct_b, width


def kdj(df: pd.DataFrame, n: int = 9, ks: int = 3, ds: int = 3):
    """(K, D, J) stochastic KDJ — causal. raw %K over the trailing n bars
    (inclusive of t, no future), K=SMA(rawK,ks), D=SMA(K,ds), J=3K-2D."""
    low_n = df["low"].rolling(n, min_periods=n).min()
    high_n = df["high"].rolling(n, min_periods=n).max()
    rng = (high_n - low_n).replace(0.0, np.nan)
    raw_k = 100.0 * (df["close"] - low_n) / rng
    k = raw_k.rolling(ks, min_periods=1).mean()
    d = k.rolling(ds, min_periods=1).mean()
    j = 3.0 * k - 2.0 * d
    return k, d, j


def _bars_since_change(s: pd.Series) -> pd.Series:
    """Bars since a forward-filled series last changed value (>=0, causal)."""
    grp = (s != s.shift(1)).cumsum()
    return s.groupby(grp).cumcount()


def fib_confluence(df: pd.DataFrame, tol_atr: float = 0.25):
    """(fib_count, nearest_fib_dist_atr) at each bar.

    From the most recent CONFIRMED swing high & low (the ffilled swing_high/
    swing_low columns), build the 0.382/0.5/0.618/0.786 retracements, then count
    how many existing reference levels (EMAs, pivots, daily/weekly open, VWAP,
    M-levels) sit within ``tol_atr`` ATR of ANY of those fib levels — the owner's
    "fibs line up with the averages/opens/pivots" idea. Higher count = a fib that
    is corroborated by other levels. Causal: swings are confirmed; levels are
    prior-bar derived. ``nearest_fib_dist_atr`` = |close - nearest fib| / ATR.
    """
    hi, lo = df.get("swing_high"), df.get("swing_low")
    atr = df["atr"].replace(0.0, np.nan)
    n = len(df)
    if hi is None or lo is None:
        z = pd.Series(0.0, index=df.index)
        return z, pd.Series(np.nan, index=df.index)
    rng = (hi - lo)
    fibs = {f: lo + r * rng for f, r in
            (("382", 0.382), ("5", 0.5), ("618", 0.618), ("786", 0.786))}
    ref_cols = [c for c in (
        "ema_13", "ema_50", "ema_200", "pivot_pp", "pivot_r1", "pivot_s1",
        "daily_open", "weekly_open", "vwap",
        "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4") if c in df.columns]
    refs = df[ref_cols]
    tol = (tol_atr * df["atr"]).to_numpy()
    count = np.zeros(n)
    nearest = np.full(n, np.inf)
    close = df["close"].to_numpy()
    for fib in fibs.values():
        fv = fib.to_numpy()
        nearest = np.minimum(nearest, np.abs(close - fv))
        for rc in ref_cols:
            d = np.abs(fv - refs[rc].to_numpy())
            count += (d <= tol).astype(float)
    nearest_atr = nearest / df["atr"].to_numpy()
    return pd.Series(count, index=df.index).fillna(0.0), pd.Series(nearest_atr, index=df.index)


def spider_touch(df: pd.DataFrame, slope_atr: float = 1.0, tol_atr: float = 0.2):
    """(sup_touch, res_touch) booleans — is price testing an angled (Gann-style)
    line anchored at the most recent confirmed swing?

    Support line rises from the last confirmed swing_low at +slope_atr·ATR/bar;
    resistance falls from the last confirmed swing_high at -slope_atr·ATR/bar.
    Anchor = confirmed past swing; slope fixed; uses bars-since-anchor — causal.
    """
    n = len(df)
    if "swing_low" not in df or "swing_high" not in df:
        f = pd.Series(False, index=df.index)
        return f, f
    atr = df["atr"]
    bars_lo = _bars_since_change(df["swing_low"].ffill())
    bars_hi = _bars_since_change(df["swing_high"].ffill())
    sup_line = df["swing_low"] + slope_atr * atr * bars_lo
    res_line = df["swing_high"] - slope_atr * atr * bars_hi
    tol = tol_atr * atr
    sup_touch = (df["close"] - sup_line).abs() <= tol
    res_touch = (df["close"] - res_line).abs() <= tol
    return sup_touch.fillna(False), res_touch.fillna(False)


def kdj_divergence(df: pd.DataFrame, left: int = 3, right: int = 3, persist: int = 4):
    """+1 bullish / -1 bearish KDJ divergence at confirmed swings (causal),
    mirroring the existing RSI add_divergence logic but on the KDJ %K line."""
    k, _, _ = kdj(df)
    k = k.to_numpy()
    high, low = df["high"].to_numpy(), df["low"].to_numpy()
    n = len(df)
    vote = np.zeros(n)
    p_lo_px = p_lo_k = p_hi_px = p_hi_k = None
    for i in range(left, n - right):
        win_hi = high[i - left:i + right + 1]
        win_lo = low[i - left:i + right + 1]
        conf = i + right
        if low[i] == win_lo.min() and win_lo.argmin() == left:
            if p_lo_px is not None and low[i] < p_lo_px and k[i] > p_lo_k:
                vote[conf] = 1.0
            p_lo_px, p_lo_k = low[i], k[i]
        if high[i] == win_hi.max() and win_hi.argmax() == left:
            if p_hi_px is not None and high[i] > p_hi_px and k[i] < p_hi_k:
                vote[conf] = -1.0
            p_hi_px, p_hi_k = high[i], k[i]
    return pd.Series(vote, index=df.index).replace(0.0, np.nan).ffill(limit=persist).fillna(0.0)
