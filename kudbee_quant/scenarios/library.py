"""A battery of mechanical, directional scenarios from vector candles + hybrid theory.

Each scenario maps a levels-annotated frame (from ``levels.build_levels``) to a
RAW signal series in {-1, 0, +1} at trigger bars. The sweep applies a holding
period to turn triggers into a target-position series and backtests it. Regime
scenarios emit a signal every bar (continuous).

All conditions use only information available at the bar (levels are
prior-period / running-shifted in build_levels), so signals are tradeable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def hold(raw: pd.Series, n: int) -> pd.Series:
    """Hold each nonzero trigger forward up to ``n`` bars (until the next signal)."""
    s = raw.replace(0, np.nan)
    return s.ffill(limit=max(1, n)).fillna(0.0).astype(float)


def _has(df: pd.DataFrame, *cols: str) -> bool:
    return all(c in df.columns for c in cols)


def _zero(df: pd.DataFrame) -> pd.Series:
    return pd.Series(0.0, index=df.index)


def _cross_up(series: pd.Series, level: pd.Series) -> pd.Series:
    return (series > level) & (series.shift(1) <= level.shift(1)) & level.notna()


def _cross_down(series: pd.Series, level: pd.Series) -> pd.Series:
    return (series < level) & (series.shift(1) >= level.shift(1)) & level.notna()


def _in_premium(df: pd.DataFrame) -> pd.Series:
    if "session" in df.columns:
        return df["session"].isin(["london", "ny"])
    return pd.Series(True, index=df.index)


# --- Vector-candle scenarios -------------------------------------------------

def vector_momentum(df):
    """Trade in the direction of a fresh climax vector (with MM momentum)."""
    if not _has(df, "vector"):
        return _zero(df)
    s = _zero(df)
    s[df["vector"] == "bull_climax"] = 1.0
    s[df["vector"] == "bear_climax"] = -1.0
    return s


def vector_momentum_premium(df):
    """Vector momentum, but only during London/NY (premium liquidity)."""
    return vector_momentum(df).where(_in_premium(df), 0.0)


def vector_fade(df):
    """Fade the climax spike (mean reversion of the vector)."""
    return -vector_momentum(df)


def vector_at_daily_open(df):
    """Vector climax occurring within 0.25 ATR of the daily open, traded in its direction."""
    if not _has(df, "vector", "daily_open", "atr", "close"):
        return _zero(df)
    near = (df["close"] - df["daily_open"]).abs() <= 0.25 * df["atr"]
    return vector_momentum(df).where(near, 0.0)


# --- Liquidity-sweep scenarios ----------------------------------------------

def sweep_reversal(df):
    """Bullish sweep of a low -> long; bearish sweep of a high -> short."""
    if not _has(df, "sweep_bias"):
        return _zero(df)
    return df["sweep_bias"].astype(float).clip(-1, 1)


def sweep_reversal_premium(df):
    return sweep_reversal(df).where(_in_premium(df), 0.0)


def sweep_plus_vector(df):
    """Sweep that coincides with a same-direction climax vector."""
    if not _has(df, "sweep_bias", "vector"):
        return _zero(df)
    s = _zero(df)
    s[(df["sweep_bias"] > 0) & (df["vector"] == "bull_climax")] = 1.0
    s[(df["sweep_bias"] < 0) & (df["vector"] == "bear_climax")] = -1.0
    return s


# --- Range scenarios (built on the one real regularity: range exhaustion) ----

def adr_band_fade(df):
    """Tag of the ADR projection -> fade back toward the daily open."""
    if not _has(df, "adr_high", "adr_low", "high", "low"):
        return _zero(df)
    s = _zero(df)
    s[df["high"] >= df["adr_high"]] = -1.0   # over-extended up -> short
    s[df["low"] <= df["adr_low"]] = 1.0      # over-extended down -> long
    return s


def adr_exhaustion_fade(df):
    """Once >100% of ADR is used, fade the side price is extended on."""
    if not _has(df, "pct_adr_used", "close", "daily_open"):
        return _zero(df)
    extended = df["pct_adr_used"] > 1.0
    s = _zero(df)
    s[extended & (df["close"] > df["daily_open"])] = -1.0
    s[extended & (df["close"] < df["daily_open"])] = 1.0
    return s


# --- Open reclaim / bias -----------------------------------------------------

def daily_open_reclaim(df):
    """Cross back above the daily open -> long; cross below -> short."""
    if not _has(df, "close", "daily_open"):
        return _zero(df)
    s = _zero(df)
    s[_cross_up(df["close"], df["daily_open"])] = 1.0
    s[_cross_down(df["close"], df["daily_open"])] = -1.0
    return s


def weekly_open_bias(df):
    """Regime: long above the weekly open, short below (continuous)."""
    if not _has(df, "close", "weekly_open"):
        return _zero(df)
    return np.sign(df["close"] - df["weekly_open"]).astype(float)


# --- Session / Asian-range scenarios (the user's example) --------------------

def asian_breakout(df):
    """Break of the Asian range during London/NY -> trade the break direction."""
    if not _has(df, "close", "asian_high", "asian_low"):
        return _zero(df)
    s = _zero(df)
    s[_cross_up(df["close"], df["asian_high"])] = 1.0
    s[_cross_down(df["close"], df["asian_low"])] = -1.0
    return s.where(_in_premium(df), 0.0)


def asian_break_fade(df):
    """Failed Asian-range break (sweep then reclaim) -> fade."""
    if not _has(df, "close", "high", "low", "asian_high", "asian_low"):
        return _zero(df)
    s = _zero(df)
    s[(df["high"] > df["asian_high"]) & (df["close"] < df["asian_high"])] = -1.0
    s[(df["low"] < df["asian_low"]) & (df["close"] > df["asian_low"])] = 1.0
    return s


def brinks_breakout(df):
    """Break of the Brinks box during NY -> trade the break direction."""
    if not _has(df, "close", "brinks_high", "brinks_low", "session"):
        return _zero(df)
    s = _zero(df)
    s[_cross_up(df["close"], df["brinks_high"])] = 1.0
    s[_cross_down(df["close"], df["brinks_low"])] = -1.0
    return s.where(df["session"] == "ny", 0.0)


def round_number_reject(df):
    """Rejection at a psychological round number -> fade."""
    if not _has(df, "high", "low", "close", "round_above", "round_below"):
        return _zero(df)
    s = _zero(df)
    s[(df["high"] >= df["round_above"]) & (df["close"] < df["round_above"])] = -1.0
    s[(df["low"] <= df["round_below"]) & (df["close"] > df["round_below"])] = 1.0
    return s


# Registry: name -> position-generating function.
SCENARIOS = {
    "vector_momentum": vector_momentum,
    "vector_momentum_premium": vector_momentum_premium,
    "vector_fade": vector_fade,
    "vector_at_daily_open": vector_at_daily_open,
    "sweep_reversal": sweep_reversal,
    "sweep_reversal_premium": sweep_reversal_premium,
    "sweep_plus_vector": sweep_plus_vector,
    "adr_band_fade": adr_band_fade,
    "adr_exhaustion_fade": adr_exhaustion_fade,
    "daily_open_reclaim": daily_open_reclaim,
    "weekly_open_bias": weekly_open_bias,
    "asian_breakout": asian_breakout,
    "asian_break_fade": asian_break_fade,
    "brinks_breakout": brinks_breakout,
    "round_number_reject": round_number_reject,
}
