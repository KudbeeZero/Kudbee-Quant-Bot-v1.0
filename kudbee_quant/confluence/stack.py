"""Confluence-stack tester — the faithful test of the Hybrid System's real thesis.

The methodology never claims a single setup wins; it claims STACKED confluence
wins (Vol 2 sec 14 Tier system). So we give each bar a directional VOTE from
every ICT/Hybrid factor we compute, sum them into a confluence score, and then
measure: do bars where many factors agree (high |score|) actually win more,
out-of-sample, than bars where few agree? That is the methodology's hypothesis,
tested honestly with Wilson CIs and FDR control.

Every factor is causal (from build_levels, lookahead-audited), so the score is
tradeable, not hindsight.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..events.study import StudyConfig, conditional_table


def _sign(s: pd.Series) -> pd.Series:
    return np.sign(s).fillna(0.0)


def factor_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Per-bar directional vote (+1 long / -1 short / 0) from each factor."""
    out = pd.DataFrame(index=df.index)

    # NOTE: a macro cross-asset vote (DXY/ES/VIX risk-on-off, Vol 4 sec 3) was
    # tested as both a vote AND an agreement-filter and REMOVED — both hurt the
    # 1h scalp edge (walk-forward +0.151R -> +0.013R vote / +0.014R filter). The
    # confluence-R edge is structural/intraday, not macro-regime-driven; the
    # macro module (levels/macro.py) remains for possible HTF/swing use.

    # Trend / momentum factors.
    if {"ema_50", "ema_800", "close"} <= set(df.columns):
        out["v_emastack"] = np.where((df["close"] > df["ema_50"]) & (df["ema_50"] > df["ema_800"]), 1,
                                     np.where((df["close"] < df["ema_50"]) & (df["ema_50"] < df["ema_800"]), -1, 0))
    if {"ema_13", "ema_50"} <= set(df.columns):
        out["v_emafast"] = _sign(df["ema_13"] - df["ema_50"])
    if "ema_cloud_pos" in df:
        out["v_cloud"] = df["ema_cloud_pos"].astype(float)
    if {"close", "vwap"} <= set(df.columns):
        out["v_vwap"] = _sign(df["close"] - df["vwap"])
    if {"close", "daily_open"} <= set(df.columns):
        out["v_dopen"] = _sign(df["close"] - df["daily_open"])
    if {"close", "pivot_pp"} <= set(df.columns):
        out["v_pivot"] = _sign(df["close"] - df["pivot_pp"])
    # NOTE: a BOS/CHoCH structure vote (Vol 5) was tested and REMOVED — it
    # diluted the 1h edge (maker-cost OOS +0.159R -> +0.096R). It is redundant
    # with the existing trend factors (EMA stack/cloud/pivot all encode the same
    # directional bias), so it shifts the threshold without adding independent
    # signal. Third added factor (after Order Blocks, macro) to fail this way:
    # the 10-factor set is saturated. The structure features (swing_high/low,
    # bos_dir, structure_dir, eqh/eql) remain available for entry models.

    # NOTE: a contrarian funding vote (order-flow, Vol 6) was tested and REMOVED
    # — even this NON-price data diluted the edge (OOS maker +0.158R -> +0.117R)
    # and had negative standalone edge (-0.117R) in the test window. Reason:
    # contrarian funding is a counter-trend signal that fails in strong trends
    # (this OOS was a downtrend). Fourth added factor to dilute (after OB, macro,
    # structure). The orderflow module (levels/orderflow.py) is kept — funding
    # data is now accessible for regime filters / future use.

    # Mean-reversion / smart-money factors.
    if "dealing_mid" in df:  # ICT: favor longs in discount, shorts in premium
        out["v_pd"] = -_sign(df["close"] - df["dealing_mid"])
    if "sweep_bias" in df:
        out["v_sweep"] = _sign(df["sweep_bias"])
    if "vector" in df:
        out["v_vector"] = np.where(df["vector"] == "bull_climax", 1.0,
                                   np.where(df["vector"] == "bear_climax", -1.0, 0.0))
    # NOTE: an RSI-divergence vote (Vol 9) was tested and REMOVED — it diluted
    # the edge (limit-entry OOS +0.243R -> +0.068R) with ~zero standalone edge
    # (+0.019R). FIFTH added factor to dilute (after OB, macro, structure,
    # funding). The 10-factor set is conclusively saturated. RSI/divergence
    # features (levels/divergence.py) remain available.
    if {"bull_fvg_bottom", "bull_fvg_top", "bear_fvg_top", "bear_fvg_bottom"} <= set(df.columns):
        in_bull = (df["low"] <= df["bull_fvg_top"]) & (df["high"] >= df["bull_fvg_bottom"])
        in_bear = (df["high"] >= df["bear_fvg_bottom"]) & (df["low"] <= df["bear_fvg_top"])
        out["v_fvg"] = np.where(in_bull, 1.0, np.where(in_bear, -1.0, 0.0))
    # NOTE: an Order-Block vote (Vol 4 sec 2) was tested here and REMOVED — it
    # diluted the edge (walk-forward median +0.148R -> +0.125R, 75% -> 72%
    # positive). The OB zones remain available as features (build_levels) for
    # other uses; they just don't improve the confluence score. Parsimony wins.

    return out.fillna(0.0)


def confluence_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add net_score (sum of votes), strength (|net|), direction, and pct.

    ``confluence_pct`` = strength / n_factors — the intuitive "X out of N"
    percentage the trader reasons in, so a threshold can be set as a percentage
    (e.g. 0.6 = "3 of 5") rather than a raw count.
    """
    votes = factor_votes(df)
    out = df.copy()
    n_factors = max(votes.shape[1], 1)
    out["net_score"] = votes.sum(axis=1)
    out["strength"] = out["net_score"].abs()
    out["direction"] = np.sign(out["net_score"])
    out["n_factors"] = n_factors
    out["confluence_pct"] = out["strength"] / n_factors
    return out


def confluence_position(df: pd.DataFrame, min_strength: float = 4.0,
                        min_pct: float | None = None) -> pd.Series:
    """Strategy signal: take the confluence direction above a threshold.

    Threshold by raw ``min_strength`` (default) OR by ``min_pct`` (fraction of
    factors aligned) when provided — the percentage the trader thinks in.
    """
    scored = confluence_score(df)
    if min_pct is not None:
        gate = scored["confluence_pct"] >= min_pct
    else:
        gate = scored["strength"] >= min_strength
    return scored["direction"].where(gate, 0.0).astype(float)


def confluence_sized_position(df: pd.DataFrame, min_pct: float = 0.5,
                              floor_size: float = 0.25) -> tuple[pd.Series, pd.Series]:
    """Directional signal + per-trade SIZE scaled by confluence percentage.

    "Give it a certain percentage": above ``min_pct``, size ramps linearly from
    ``floor_size`` (at the threshold) to 1.0 (at 100% confluence). Below the
    threshold, no trade. Returns (signal, size) where size is in [0, 1].
    """
    scored = confluence_score(df)
    gate = scored["confluence_pct"] >= min_pct
    span = max(1.0 - min_pct, 1e-9)
    ramp = floor_size + (1.0 - floor_size) * ((scored["confluence_pct"] - min_pct) / span).clip(0, 1)
    sig = scored["direction"].where(gate, 0.0).astype(float)
    size = ramp.where(gate, 0.0).astype(float)
    return sig, size


def confluence_directional_study(
    df: pd.DataFrame,
    horizon: int = 8,
    min_n: int = 50,
) -> pd.DataFrame:
    """Does forward return in the voted direction improve with confluence strength?

    For each bar: direction = sign(net_score); outcome = forward return over
    ``horizon`` IN THAT DIRECTION is positive (a 'win'). Grouped by strength
    bucket with Wilson CIs and FDR control. The thesis predicts win_rate rises
    with strength.
    """
    scored = confluence_score(df)
    close = scored["close"]
    fwd = close.shift(-horizon) / close - 1.0
    scored["dir_return"] = fwd * scored["direction"]
    scored["win"] = (scored["dir_return"] > 0).where(scored["dir_return"].notna() & (scored["direction"] != 0))
    scored = scored.dropna(subset=["win"])
    scored["strength_bucket"] = scored["strength"].astype(int)

    table = conditional_table(scored, "win", ["strength_bucket"], StudyConfig(min_n=min_n))
    # Attach mean directional return per bucket for magnitude context.
    means = scored.groupby("strength_bucket")["dir_return"].mean()
    table["mean_dir_return"] = table["strength_bucket"].map(means)
    return table.sort_values("strength_bucket").reset_index(drop=True)
