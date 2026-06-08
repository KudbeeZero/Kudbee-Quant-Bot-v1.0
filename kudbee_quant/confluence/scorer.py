"""Confluence scoring + reaction / range-exhaustion studies."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..events.study import wilson_ci
from ..levels import LEVEL_COLUMNS


def _cluster_count(values: np.ndarray, tol: float) -> int:
    """Count distinct clusters among level values within ``tol`` of each other.

    Two levels closer than tol count as one confluence, not two — so the score
    reflects genuinely distinct levels stacked near price.
    """
    vals = np.sort(values[np.isfinite(values)])
    if vals.size == 0:
        return 0
    clusters = 1
    last = vals[0]
    for v in vals[1:]:
        if v - last > tol:
            clusters += 1
            last = v
        # else same cluster; keep `last` as cluster anchor
    return clusters


def add_confluence(df: pd.DataFrame, level_cols=None, tol_atr: float = 0.25) -> pd.DataFrame:
    """Add ``confluence_score`` = number of distinct reference levels within
    ``tol_atr`` * ATR of the bar's close.
    """
    cols = [c for c in (level_cols or LEVEL_COLUMNS) if c in df.columns]
    if "atr" not in df.columns:
        raise ValueError("add_confluence requires the 'atr' column (run build_levels)")
    out = df.copy()
    close = out["close"].to_numpy()
    atr = out["atr"].to_numpy()
    level_matrix = out[cols].to_numpy(dtype=float)

    scores = np.zeros(len(out), dtype=int)
    for i in range(len(out)):
        tol = atr[i] * tol_atr
        if not np.isfinite(tol) or tol <= 0:
            continue
        levels = level_matrix[i]
        near = levels[np.abs(levels - close[i]) <= tol]
        scores[i] = _cluster_count(near, tol)
    out["confluence_score"] = scores
    return out


def confluence_reaction_study(
    df: pd.DataFrame,
    horizon: int = 8,
    tol_atr: float = 0.25,
    momentum_lookback: int = 6,
    min_n: int = 30,
) -> pd.DataFrame:
    """Measure reaction strength and reversal rate by confluence score.

    For each bar: reaction = |forward return over ``horizon``| (in ATR units);
    reversal = forward move opposes the prior ``momentum_lookback``-bar move
    (i.e. the zone turned price). Grouped by confluence score with Wilson CIs.

    If higher scores do not show bigger reaction / higher reversal rate than
    low scores, confluence carries no edge here — and we report that.
    """
    out = add_confluence(df, tol_atr=tol_atr)
    close = out["close"]
    atr = out["atr"].replace(0, np.nan)
    fwd = close.shift(-horizon) / close - 1.0
    out["reaction_atr"] = (fwd.abs() * close) / atr
    prior = close - close.shift(momentum_lookback)
    out["reversal"] = ((np.sign(fwd) != np.sign(prior)) & fwd.notna() & (prior != 0))
    out["reversal"] = out["reversal"].where(fwd.notna())

    rows = []
    valid = out.dropna(subset=["reaction_atr"])
    for score, g in valid.groupby("confluence_score"):
        n = len(g)
        rev = g["reversal"].dropna()
        wins = int(rev.sum())
        lo, hi = wilson_ci(wins, len(rev)) if len(rev) else (float("nan"), float("nan"))
        rows.append({
            "confluence_score": int(score), "n": n,
            "mean_reaction_atr": float(g["reaction_atr"].mean()),
            "reversal_rate": float(rev.mean()) if len(rev) else float("nan"),
            "rev_ci_low": lo, "rev_ci_high": hi,
            "sufficient": n >= min_n,
        })
    return pd.DataFrame(rows).sort_values("confluence_score").reset_index(drop=True)


def range_exhaustion_study(
    df: pd.DataFrame,
    horizon: int = 12,
    used_col: str = "pct_adr_used",
    bins=(0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 10.0),
    min_n: int = 30,
) -> pd.DataFrame:
    """Does price keep moving after consuming X% of its average daily range?

    Buckets bars by % of ADR already used today, then measures the further
    range expansion over the next ``horizon`` bars (in ATR units). The
    range-exhaustion thesis predicts continuation should shrink as % used
    rises. Tests that empirically.
    """
    out = df.copy()
    if used_col not in out.columns:
        raise ValueError(f"range_exhaustion_study needs '{used_col}' (run build_levels)")
    close = out["close"].to_numpy()
    high = out["high"].to_numpy()
    low = out["low"].to_numpy()
    atr = out["atr"].replace(0, np.nan).to_numpy()
    n = len(out)
    fwd_range = np.full(n, np.nan)
    for t in range(n - 1):
        end = min(t + horizon, n - 1)
        hi = high[t + 1:end + 1]
        lo = low[t + 1:end + 1]
        if hi.size and np.isfinite(atr[t]) and atr[t] > 0:
            fwd_range[t] = (hi.max() - lo.min()) / atr[t]
    out["fwd_range_atr"] = fwd_range

    out["_bucket"] = pd.cut(out[used_col], bins=list(bins))
    rows = []
    for bucket, g in out.dropna(subset=["fwd_range_atr"]).groupby("_bucket", observed=True):
        rows.append({
            "pct_adr_used": str(bucket), "n": len(g),
            "mean_fwd_range_atr": float(g["fwd_range_atr"].mean()),
            "median_fwd_range_atr": float(g["fwd_range_atr"].median()),
            "sufficient": len(g) >= min_n,
        })
    return pd.DataFrame(rows)
