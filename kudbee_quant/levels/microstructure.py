"""ICT/Hybrid microstructure features from the Vol 1-3 research (price-only).

All causal (no lookahead): VWAP is cumulative within the UTC day; the dealing
range uses prior bars; FVGs are 3-candle gaps confirmed at the third bar; macro
flags are pure time-of-day. These unlock the FVG-fill, VWAP-reversion, Turtle
Soup, Silver Bullet, and Judas setups.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_session_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Session VWAP anchored to the UTC day, plus +/-1 sigma bands (causal)."""
    out = df.copy()
    if "utc_date" not in out.columns:
        out["utc_date"] = pd.to_datetime(out["timestamp"], utc=True).dt.date
    tp = (out["high"] + out["low"] + out["close"]) / 3.0
    pv = tp * out["volume"]
    grp = out.groupby("utc_date")
    cum_pv = pv.groupby(out["utc_date"]).cumsum()
    cum_v = out["volume"].groupby(out["utc_date"]).cumsum().replace(0, np.nan)
    out["vwap"] = cum_pv / cum_v
    # rolling dispersion of price around vwap, within the day
    dev2 = ((tp - out["vwap"]) ** 2 * out["volume"]).groupby(out["utc_date"]).cumsum() / cum_v
    sigma = np.sqrt(dev2)
    out["vwap_upper"] = out["vwap"] + sigma
    out["vwap_lower"] = out["vwap"] - sigma
    return out


def add_premium_discount(df: pd.DataFrame, lookback: int = 48) -> pd.DataFrame:
    """ICT dealing range: premium (upper half) vs discount (lower half).

    Uses the PRIOR ``lookback`` bars (shifted) so the range is known at the bar.
    """
    out = df.copy()
    hi = out["high"].rolling(lookback, min_periods=lookback // 2).max().shift(1)
    lo = out["low"].rolling(lookback, min_periods=lookback // 2).min().shift(1)
    mid = (hi + lo) / 2.0
    half = (hi - lo) / 2.0
    out["dealing_mid"] = mid
    out["in_premium"] = out["close"] > mid
    out["in_discount"] = out["close"] < mid
    out["pd_pos"] = (out["close"] - mid) / half.replace(0, np.nan)  # -1..+1
    return out


def add_fvg(df: pd.DataFrame) -> pd.DataFrame:
    """Fair Value Gaps (3-candle imbalance), confirmed at the 3rd candle.

    Bullish FVG: low[t] > high[t-2] (gap up). Bearish FVG: high[t] < low[t-2].
    Exposes the most recent unfilled FVG zone edges (forward-filled, cleared
    when price trades through them) for fill/retest scenarios.
    """
    out = df.copy()
    h2, l2 = out["high"].shift(2), out["low"].shift(2)
    bull = out["low"] > h2
    bear = out["high"] < l2
    out["fvg_bull"] = bull.fillna(False)
    out["fvg_bear"] = bear.fillna(False)
    # Zone edges at formation.
    bull_bottom = h2.where(bull)
    bull_top = out["low"].where(bull)
    bear_top = l2.where(bear)
    bear_bottom = out["high"].where(bear)
    # Most recent bull/bear FVG zone, carried forward (prior gaps only).
    out["bull_fvg_bottom"] = bull_bottom.shift(1).ffill()
    out["bull_fvg_top"] = bull_top.shift(1).ffill()
    out["bear_fvg_top"] = bear_top.shift(1).ffill()
    out["bear_fvg_bottom"] = bear_bottom.shift(1).ffill()
    return out


def add_macro_flags(df: pd.DataFrame) -> pd.DataFrame:
    """ICT macro-time and Silver Bullet windows from NY-local time (DST-correct).

    Requires ny_hour / ny_minute from the time-context step.
    """
    out = df.copy()
    if "ny_minute" not in out.columns:
        return out
    mod = out["ny_minute"]
    out["in_macro_best"] = mod.between(9 * 60 + 50, 10 * 60 + 10)   # 09:50-10:10 ET
    out["in_silver_bullet"] = out.get("ny_hour", pd.Series(index=out.index)).eq(10)  # 10-11 ET
    out["in_ny_brinks"] = mod.between(8 * 60 + 30, 9 * 60 + 45)     # 08:30-09:45 ET
    out["in_london_kz"] = mod.between(2 * 60, 5 * 60)               # 02:00-05:00 ET
    return out


def add_microstructure(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the full microstructure pipeline."""
    out = add_session_vwap(df)
    out = add_premium_discount(out)
    out = add_fvg(out)
    out = add_macro_flags(out)
    return out
