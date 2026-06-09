"""ICT/Hybrid setups from research Vol 1-3 (price-only, mechanically precise).

VWAP reversion, Turtle Soup (false-breakout reversal), Silver Bullet (macro-
window FVG), FVG fill, and the Judas 1/3-ADR exhaustion fade. Each returns a
raw {-1,0,+1} signal; all causal (verified by the lookahead audit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import add_emas
from .library import _has, _zero


def vwap_reversion(df, band_mult=1.0):
    """Stretched beyond the session VWAP band -> revert toward VWAP."""
    if not _has(df, "vwap", "vwap_upper", "vwap_lower", "close"):
        return _zero(df)
    s = _zero(df)
    s[df["close"] < df["vwap_lower"]] = 1.0    # discount stretch -> long back to VWAP
    s[df["close"] > df["vwap_upper"]] = -1.0   # premium stretch -> short back to VWAP
    return s


def turtle_soup(df):
    """False breakout of the prior-day high/low (liquidity sweep) -> reverse.

    Premium/discount filter: short sweeps of the high in premium, long sweeps
    of the low in discount (ICT dealing-range context).
    """
    if not _has(df, "pdh", "pdl", "high", "low", "close"):
        return _zero(df)
    s = _zero(df)
    prem = df.get("in_premium", pd.Series(True, index=df.index))
    disc = df.get("in_discount", pd.Series(True, index=df.index))
    s[(df["high"] > df["pdh"]) & (df["close"] < df["pdh"]) & prem] = -1.0
    s[(df["low"] < df["pdl"]) & (df["close"] > df["pdl"]) & disc] = 1.0
    return s


def fvg_fill(df):
    """Price returns into the most recent unfilled FVG zone -> trade its bias."""
    if not _has(df, "bull_fvg_bottom", "bull_fvg_top", "bear_fvg_top", "bear_fvg_bottom",
                "high", "low"):
        return _zero(df)
    s = _zero(df)
    in_bull = (df["low"] <= df["bull_fvg_top"]) & (df["high"] >= df["bull_fvg_bottom"])
    in_bear = (df["high"] >= df["bear_fvg_bottom"]) & (df["low"] <= df["bear_fvg_top"])
    s[in_bull & (df["close"] > df["open"])] = 1.0    # bullish FVG = support, hold
    s[in_bear & (df["close"] < df["open"])] = -1.0
    return s


def silver_bullet(df):
    """Silver Bullet: in the 10-11 ET window, take a fresh FVG in the EMA trend."""
    if not _has(df, "fvg_bull", "fvg_bear", "close"):
        return _zero(df)
    window = df.get("in_silver_bullet", pd.Series(False, index=df.index))
    e = add_emas(df, (50, 200))
    up = e["ema_50"] > e["ema_200"]
    s = _zero(df)
    s[window & df["fvg_bull"] & up] = 1.0
    s[window & df["fvg_bear"] & ~up] = -1.0
    return s


def judas_thirds(df, frac=0.33):
    """Judas swing: ~1/3 ADR move off the daily open in a killzone, then fade.

    A sharp move against the open of roughly 1/3 ADR during the London/NY
    Brinks window is the exhaustion zone -> fade back toward the daily open.
    """
    if not _has(df, "daily_open", "adr", "high", "low", "close"):
        return _zero(df)
    in_kz = df.get("in_ny_brinks", pd.Series(False, index=df.index)) | \
        df.get("in_london_kz", pd.Series(False, index=df.index))
    thresh = frac * df["adr"]
    s = _zero(df)
    # Spiked >=1/3 ADR ABOVE the open then closing back below -> short (fade up-move).
    s[in_kz & (df["high"] - df["daily_open"] >= thresh) & (df["close"] < df["high"])] = -1.0
    s[in_kz & (df["daily_open"] - df["low"] >= thresh) & (df["close"] > df["low"])] = 1.0
    return s


ICT_SCENARIOS = {
    "vwap_reversion": vwap_reversion,
    "turtle_soup": turtle_soup,
    "fvg_fill": fvg_fill,
    "silver_bullet": silver_bullet,
    "judas_thirds": judas_thirds,
}
