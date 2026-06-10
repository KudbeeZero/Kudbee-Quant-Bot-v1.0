"""Rigorous validation of an R-expectancy (bracket) strategy.

The confluence-R lead beat the null on one OOS window. This is where we try to
break it properly: walk-forward across MANY consecutive windows (does it hold
through different regimes?), across UNCORRELATED assets (is it crypto-specific
beta?), and under realistic COSTS (does the thin edge survive slippage?). A
real edge is positive across most (asset x window) cells at a believable fee.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from ..backtest.bracket import bracket_backtest
from ..ingest import load_ohlcv
from ..levels import build_levels

PositionFn = Callable[[pd.DataFrame], pd.Series]


def walkforward_bracket(
    df: pd.DataFrame,
    signal: pd.Series,
    n_folds: int = 6,
    target_r: float = 2.0,
    stop_atr: float = 1.0,
    max_bars: int = 24,
    fee_r: float = 0.02,
    min_trades: int = 15,
) -> list[dict]:
    """Run a bracket backtest on each of ``n_folds`` consecutive windows."""
    n = len(df)
    bounds = np.linspace(0, n, n_folds + 1, dtype=int)
    out = []
    sig = pd.Series(signal).reset_index(drop=True)
    d = df.reset_index(drop=True)
    for i in range(n_folds):
        a, b = bounds[i], bounds[i + 1]
        fold_df = d.iloc[a:b].reset_index(drop=True)
        fold_sig = sig.iloc[a:b].reset_index(drop=True)
        r = bracket_backtest(fold_df, fold_sig, stop_atr=stop_atr, target_r=target_r,
                             max_bars=max_bars, fee_r=fee_r)
        out.append({"fold": i, "n_trades": r.n_trades, "expectancy_r": r.expectancy_r,
                    "total_r": r.total_r, "win_rate": r.win_rate,
                    "profit_factor": r.profit_factor,
                    "sufficient": r.n_trades >= min_trades})
    return out


def validate_bracket(
    specs: list[str],
    position_fn: PositionFn,
    interval: str = "1h",
    limit: int = 4000,
    n_folds: int = 6,
    target_r: float = 2.0,
    stop_atr: float = 1.0,
    max_bars: int = 24,
    fee_r: float = 0.02,
) -> tuple[pd.DataFrame, dict]:
    """Walk-forward an R strategy across a universe; return cells + a summary.

    Returns (cells_df with one row per asset x fold, summary dict with the
    fraction of sufficient cells that are positive, median expectancy, and the
    cross-asset return correlation for honesty about independence).
    """
    frames = {spec: build_levels(load_ohlcv(spec, interval=interval, limit=limit)) for spec in specs}
    rows = []
    for spec, df in frames.items():
        sig = position_fn(df)
        for cell in walkforward_bracket(df, sig, n_folds, target_r, stop_atr, max_bars, fee_r):
            cell["asset"] = spec
            rows.append(cell)
    cells = pd.DataFrame(rows)

    suff = cells[cells["sufficient"]]
    frac_pos = float((suff["expectancy_r"] > 0).mean()) if len(suff) else float("nan")
    summary = {
        "n_cells": len(cells),
        "n_sufficient": len(suff),
        "frac_positive": frac_pos,
        "median_expectancy_r": float(suff["expectancy_r"].median()) if len(suff) else float("nan"),
        "mean_expectancy_r": float(suff["expectancy_r"].mean()) if len(suff) else float("nan"),
        "median_cross_corr": _cross_corr(frames),
        "n_assets": len(frames),
    }
    return cells, summary


def cost_sensitivity(
    specs: list[str],
    position_fn: PositionFn,
    fees=(0.0, 0.02, 0.05, 0.10),
    **kw,
) -> pd.DataFrame:
    """Median OOS-cell expectancy across a range of round-trip costs (in R)."""
    rows = []
    for fee in fees:
        _, summary = validate_bracket(specs, position_fn, fee_r=fee, **kw)
        rows.append({"fee_r": fee, "frac_positive": summary["frac_positive"],
                     "median_expectancy_r": summary["median_expectancy_r"]})
    return pd.DataFrame(rows)


def _cross_corr(frames: dict) -> float:
    if len(frames) < 2:
        return 0.0
    rets = {}
    for spec, df in frames.items():
        s = df.set_index("timestamp")["close"].astype(float).pct_change()
        rets[spec] = s
    mat = pd.DataFrame(rets).dropna()
    if len(mat) < 3 or mat.shape[1] < 2:
        return 0.0
    corr = mat.corr().to_numpy()
    off = corr[np.triu_indices(corr.shape[0], k=1)]
    off = off[~np.isnan(off)]
    return float(np.median(off)) if off.size else 0.0
