"""Walk-forward analysis — the overfitting smoke detector.

A strategy that looks brilliant on the whole history may just be curve-fit.
Walk-forward splits the data into consecutive in-sample (IS) / out-of-sample
(OOS) windows and only ever scores the OOS slices. If OOS performance is far
worse than IS, the "edge" was hindsight. We report both so the gap is visible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .engine import BacktestConfig, run_backtest
from .metrics import PerformanceMetrics, performance_metrics


@dataclass(frozen=True)
class WalkForwardResult:
    n_folds: int
    in_sample: PerformanceMetrics       # metrics over concatenated IS slices
    out_of_sample: PerformanceMetrics   # metrics over concatenated OOS slices
    oos_equity: pd.Series

    @property
    def sharpe_decay(self) -> float:
        """OOS Sharpe minus IS Sharpe. Strongly negative => overfit."""
        return self.out_of_sample.sharpe - self.in_sample.sharpe


def walk_forward(
    df: pd.DataFrame,
    position_fn: Callable[[pd.DataFrame], pd.Series],
    n_folds: int = 5,
    is_oos_ratio: float = 3.0,
    config: BacktestConfig | None = None,
) -> WalkForwardResult:
    """Run rolling IS/OOS folds, scoring only the OOS portions.

    Args:
        df: full OHLCV history (chronological).
        position_fn: maps an OHLCV slice to a target-position series. (Stateless
            indicator strategies need no fitting; the IS slice is still kept
            separate so parameter-fit strategies can plug in here unchanged.)
        n_folds: number of OOS windows.
        is_oos_ratio: size of IS window relative to each OOS window.
        config: backtest costs/annualization.
    """
    config = config or BacktestConfig()
    df = df.reset_index(drop=True)
    n = len(df)
    if n < (n_folds * 4):
        raise ValueError("not enough bars for the requested number of folds")

    oos_len = int(n / (n_folds + is_oos_ratio))
    is_len = int(oos_len * is_oos_ratio)
    if oos_len < 2 or is_len < 2:
        raise ValueError("folds too small; reduce n_folds or supply more data")

    is_returns: list[pd.Series] = []
    oos_returns: list[pd.Series] = []
    oos_positions: list[pd.Series] = []

    start = 0
    for _ in range(n_folds):
        is_end = start + is_len
        oos_end = is_end + oos_len
        if oos_end > n:
            break
        is_slice = df.iloc[start:is_end]
        oos_slice = df.iloc[is_end:oos_end]

        is_res = run_backtest(is_slice, position_fn(is_slice), config)
        oos_res = run_backtest(oos_slice, position_fn(oos_slice), config)
        is_returns.append(is_res.returns)
        oos_returns.append(oos_res.returns)
        oos_positions.append(oos_res.positions)
        start += oos_len  # roll the window forward

    is_cat = pd.concat(is_returns, ignore_index=True)
    oos_cat = pd.concat(oos_returns, ignore_index=True)
    oos_pos_cat = pd.concat(oos_positions, ignore_index=True)
    oos_equity = (1.0 + oos_cat).cumprod()

    return WalkForwardResult(
        n_folds=len(oos_returns),
        in_sample=performance_metrics(is_cat, config.periods_per_year),
        out_of_sample=performance_metrics(oos_cat, config.periods_per_year, positions=oos_pos_cat),
        oos_equity=oos_equity,
    )
