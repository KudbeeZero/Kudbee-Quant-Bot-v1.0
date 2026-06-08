"""Precise BTMM / PVSRA setups from the research (docs/research/btmm_pvsra_setups.md).

Pip thresholds are re-expressed in ATR units (crypto has no pips). Every
scenario returns a RAW signal series in {-1,0,+1}. All conditions are causal;
the lookahead audit (audit.py) verifies this mechanically.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import add_emas, cross_down, cross_up, swing_pivots
from .library import _has, _in_premium, _zero


def _utc_hour(df):
    return pd.to_datetime(df["timestamp"], utc=True).dt.hour


# 1. 13/50 EMA cross + close-beyond-13 filter (BTMM Level 1).
def ema_cross_13_50(df):
    e = add_emas(df, (13, 50))
    s = _zero(df)
    s[cross_up(e["ema_13"], e["ema_50"]) & (e["close"] > e["ema_13"])] = 1.0
    s[cross_down(e["ema_13"], e["ema_50"]) & (e["close"] < e["ema_13"])] = -1.0
    return s


# 2. 50/800 trend filter as a standalone regime (BTMM Level 3).
def ema_trend(df):
    e = add_emas(df, (50, 800))
    return np.sign(e["ema_50"] - e["ema_800"]).astype(float)


# 3. Trend-pullback: 13/50 cross in the direction of the 50/800 trend.
def ema_trend_pullback(df):
    e = add_emas(df, (13, 50, 800))
    up_trend = e["ema_50"] > e["ema_800"]
    s = _zero(df)
    s[cross_up(e["ema_13"], e["ema_50"]) & up_trend] = 1.0
    s[cross_down(e["ema_13"], e["ema_50"]) & ~up_trend] = -1.0
    return s


# 4. Asian stop-hunt reversal (the REAL version; no-lookahead Asian range).
def asian_stophunt(df, smooth_mult=0.8, breach_mult=0.15):
    if not _has(df, "asian_high", "asian_low", "adr", "atr", "high", "low", "close"):
        return _zero(df)
    rng = df["asian_high"] - df["asian_low"]
    smooth = rng < smooth_mult * df["adr"]          # "smooth, < ~40 pips" range
    breach = breach_mult * df["atr"]
    s = _zero(df)
    # Swept above then closed back inside -> short.
    s[smooth & (df["high"] > df["asian_high"] + breach) & (df["close"] < df["asian_high"])] = -1.0
    s[smooth & (df["low"] < df["asian_low"] - breach) & (df["close"] > df["asian_low"])] = 1.0
    return s.where(_in_premium(df), 0.0)


# 5. Shadow-box / Brinks opening-range breakout (EU box 08:00-09:00 UTC).
def brinks_orb(df):
    if not _has(df, "brinks_high", "brinks_low", "close", "timestamp"):
        return _zero(df)
    e = add_emas(df, (50, 800))
    up_trend = e["ema_50"] > e["ema_800"]
    after_box = _utc_hour(df) >= 9          # box complete -> causal use only
    s = _zero(df)
    s[cross_up(df["close"], df["brinks_high"]) & up_trend] = 1.0
    s[cross_down(df["close"], df["brinks_low"]) & ~up_trend] = -1.0
    return s.where(after_box & _in_premium(df), 0.0)


# 6. Railroad-track reversal: two adjacent ~equal opposite candles at an extreme.
def railroad_track(df, body_mult=1.0):
    if not _has(df, "open", "close", "atr"):
        return _zero(df)
    body = (df["close"] - df["open"]).abs()
    big = body > body_mult * df["atr"]
    prev_big = big.shift(1, fill_value=False)
    prev_bear = df["close"].shift(1) < df["open"].shift(1)
    prev_bull = df["close"].shift(1) > df["open"].shift(1)
    cur_bull = df["close"] > df["open"]
    cur_bear = df["close"] < df["open"]
    ratio_ok = (body / body.shift(1)).between(0.5, 2.0)
    s = _zero(df)
    s[big & prev_big & ratio_ok & prev_bear & cur_bull] = 1.0   # down then up -> long
    s[big & prev_big & ratio_ok & prev_bull & cur_bear] = -1.0
    return s


# 7. M/W second-leg via swing pivots + neckline break.
def mw_second_leg(df, tol_atr=0.5):
    if not _has(df, "high", "low", "close", "atr"):
        return _zero(df)
    p = swing_pivots(df)
    tol = tol_atr * df["atr"]
    # M: a new confirmed swing high <= previous swing high (double top), then
    # price closes below the most recent confirmed swing low (neckline) -> short.
    new_sh = pd.Series(p["new_swing_high"], index=df.index)
    new_sl = pd.Series(p["new_swing_low"], index=df.index)
    prev_sh = new_sh.ffill().shift(1).where(new_sh.notna()).ffill()
    prev_sl = new_sl.ffill().shift(1).where(new_sl.notna()).ffill()
    # M (double top): new swing high not exceeding the prior swing high.
    is_m = new_sh.notna() & (new_sh <= prev_sh + tol)
    # W (double bottom): new swing low not exceeding the prior swing low.
    is_w = new_sl.notna() & (new_sl >= prev_sl - tol)
    s = _zero(df)
    # Neckline break confirmation on the same/next bars: close beyond swing low/high.
    s[is_m & (df["close"] < p["swing_low_price"])] = -1.0
    s[is_w & (df["close"] > p["swing_high_price"])] = 1.0
    return s


# 8. Vector-zone retest rejection: price returns to a prior climax-vector box.
def vector_zone_retest(df):
    if not _has(df, "vector", "high", "low", "close"):
        return _zero(df)
    is_climax = df["vector"].isin(["bull_climax", "bear_climax"])
    dir_ = np.where(df["vector"] == "bull_climax", 1.0,
                    np.where(df["vector"] == "bear_climax", -1.0, np.nan))
    # Most recent PRIOR vector zone (shifted so the current bar isn't its own zone).
    zlow = df["low"].where(is_climax).shift(1).ffill()
    zhigh = df["high"].where(is_climax).shift(1).ffill()
    zdir = pd.Series(dir_, index=df.index).shift(1).ffill()
    in_zone = (df["low"] <= zhigh) & (df["high"] >= zlow) & ~is_climax
    s = _zero(df)
    s[in_zone & (zdir > 0) & (df["close"] > df["open"])] = 1.0   # bull zone, bullish reject
    s[in_zone & (zdir < 0) & (df["close"] < df["open"])] = -1.0
    return s


# 9. Sweep + opposing climax vector (PVSRA Setup 6).
def sweep_plus_opposing_vector(df):
    if not _has(df, "sweep_bias", "vector"):
        return _zero(df)
    s = _zero(df)
    s[(df["sweep_bias"] > 0) & (df["vector"] == "bull_climax")] = 1.0
    s[(df["sweep_bias"] < 0) & (df["vector"] == "bear_climax")] = -1.0
    return s


# 10. Vector at the monthly open / M0 pivot (recorded from @KudbeeX call).
def vector_at_monthly_open(df, tol_atr=0.5):
    """Climax vector within tol*ATR of the monthly open -> trade its direction."""
    if not _has(df, "vector", "monthly_open", "atr", "close"):
        return _zero(df)
    near = (df["close"] - df["monthly_open"]).abs() <= tol_atr * df["atr"]
    s = _zero(df)
    s[(df["vector"] == "bull_climax") & near] = 1.0
    s[(df["vector"] == "bear_climax") & near] = -1.0
    return s


BTMM_SCENARIOS = {
    "vector_at_monthly_open": vector_at_monthly_open,
    "ema_cross_13_50": ema_cross_13_50,
    "ema_trend": ema_trend,
    "ema_trend_pullback": ema_trend_pullback,
    "asian_stophunt": asian_stophunt,
    "brinks_orb": brinks_orb,
    "railroad_track": railroad_track,
    "mw_second_leg": mw_second_leg,
    "vector_zone_retest": vector_zone_retest,
    "sweep_plus_opposing_vector": sweep_plus_opposing_vector,
}
