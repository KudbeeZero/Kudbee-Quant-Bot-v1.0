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

    # Mean-reversion / smart-money factors.
    if "dealing_mid" in df:  # ICT: favor longs in discount, shorts in premium
        out["v_pd"] = -_sign(df["close"] - df["dealing_mid"])
    if "sweep_bias" in df:
        out["v_sweep"] = _sign(df["sweep_bias"])
    if "vector" in df:
        out["v_vector"] = np.where(df["vector"] == "bull_climax", 1.0,
                                   np.where(df["vector"] == "bear_climax", -1.0, 0.0))
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
    """Add net_score (sum of votes), strength (|net|), and direction columns."""
    votes = factor_votes(df)
    out = df.copy()
    out["net_score"] = votes.sum(axis=1)
    out["strength"] = out["net_score"].abs()
    out["direction"] = np.sign(out["net_score"])
    out["n_factors"] = votes.shape[1]
    return out


def confluence_position(df: pd.DataFrame, min_strength: float = 4.0) -> pd.Series:
    """Strategy signal: take the confluence direction only when strength is high."""
    scored = confluence_score(df)
    sig = scored["direction"].where(scored["strength"] >= min_strength, 0.0)
    return sig.astype(float)


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
