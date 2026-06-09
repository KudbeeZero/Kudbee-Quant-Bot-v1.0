"""Market structure — BOS / CHoCH / structure bias (Vol 5 sec 2, Vol 6).

ICT market structure rules, mechanized and causal:
  - Confirmed swing highs/lows (the 3-candle rule; known only after ``right``
    bars, so no lookahead).
  - BOS (Break of Structure): a candle BODY closes beyond the most recent
    confirmed swing in the trend direction (a WICK alone is a sweep, not a BOS).
  - structure_dir: +1 after a bullish BOS, -1 after a bearish BOS, carried
    forward — the structural trend bias.
  - Equal highs/lows: clustered confirmed swings = liquidity pools.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _confirmed_swings(high: np.ndarray, low: np.ndarray, left: int, right: int):
    """Most-recent confirmed swing high/low at each bar (causal, ffilled)."""
    n = len(high)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    for i in range(left, n - right):
        win_hi = high[i - left:i + right + 1]
        win_lo = low[i - left:i + right + 1]
        if high[i] == win_hi.max() and win_hi.argmax() == left:
            sh[i + right] = high[i]   # known only at i+right
        if low[i] == win_lo.min() and win_lo.argmin() == left:
            sl[i + right] = low[i]
    return pd.Series(sh).ffill().to_numpy(), pd.Series(sl).ffill().to_numpy()


def add_structure(df: pd.DataFrame, left: int = 3, right: int = 3,
                  eq_tol_atr: float = 0.1) -> pd.DataFrame:
    """Add BOS events, structure_dir bias, and equal-high/low liquidity flags."""
    out = df.copy()
    high = out["high"].to_numpy()
    low = out["low"].to_numpy()
    close = out["close"].to_numpy()
    sh, sl = _confirmed_swings(high, low, left, right)
    out["swing_high"] = sh
    out["swing_low"] = sl

    # BOS = BODY (close) beyond the most recent confirmed swing (not just a wick).
    bull_bos = close > sh
    bear_bos = close < sl
    out["bos_dir"] = np.where(bull_bos, 1.0, np.where(bear_bos, -1.0, 0.0))
    raw = pd.Series(np.where(bull_bos, 1.0, np.where(bear_bos, -1.0, np.nan)), index=out.index)
    out["structure_dir"] = raw.ffill().fillna(0.0)

    # Equal highs/lows: consecutive confirmed swings within tolerance = liquidity.
    if "atr" in out.columns:
        tol = (out["atr"] * eq_tol_atr).to_numpy()
        sh_s = pd.Series(sh)
        sl_s = pd.Series(sl)
        out["eqh"] = (np.abs(sh_s - sh_s.shift(1)) <= tol) & np.isfinite(sh)
        out["eql"] = (np.abs(sl_s - sl_s.shift(1)) <= tol) & np.isfinite(sl)
    return out
