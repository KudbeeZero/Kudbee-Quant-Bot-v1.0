"""Event-driven backtester. No lookahead, realistic costs.

Core discipline: a position decided from information available at the close
of bar *t* earns the return of bar *t+1*. We shift positions forward by one
bar so a signal can never trade on the same bar it was computed from. Costs
(commission + slippage) are charged on every change in position size.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics, performance_metrics


@dataclass(frozen=True)
class BacktestConfig:
    fee_bps: float = 5.0          # commission per side, basis points (5 = 0.05%)
    slippage_bps: float = 2.0     # assumed slippage per side, basis points
    periods_per_year: float = 24 * 365  # hourly crypto default
    allow_short: bool = True


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series            # per-bar net strategy returns
    positions: pd.Series          # per-bar position actually held (shifted)
    metrics: PerformanceMetrics

    @property
    def trade_returns(self) -> pd.Series:
        """Returns realized while holding a position (for Monte Carlo)."""
        held = self.positions != 0
        return self.returns[held]


def run_backtest(
    df: pd.DataFrame,
    positions: pd.Series,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Simulate a strategy from a target-position series.

    Args:
        df: OHLCV with a ``close`` column.
        positions: target position per bar in [-1, 1] (signal-time, i.e.
            decided at that bar's close). We shift it forward internally.
        config: costs and annualization.
    """
    config = config or BacktestConfig()
    if "close" not in df.columns:
        raise ValueError("df must contain a 'close' column")

    close = df["close"].astype(float).reset_index(drop=True)
    pos = pd.Series(positions, dtype=float).reset_index(drop=True).reindex(close.index).fillna(0.0)
    if not config.allow_short:
        pos = pos.clip(lower=0.0)
    pos = pos.clip(-1.0, 1.0)

    # No lookahead: hold position decided at t-1 over the return from t-1 -> t.
    held = pos.shift(1).fillna(0.0)
    bar_return = close.pct_change().fillna(0.0)
    gross = held * bar_return

    # Costs on every change in exposure (entry, exit, flip, resize).
    turnover = held.diff().abs().fillna(held.abs())
    cost_rate = (config.fee_bps + config.slippage_bps) / 10_000.0
    costs = turnover * cost_rate

    net = gross - costs
    equity = (1.0 + net).cumprod()

    if isinstance(df.index, pd.Index) and "timestamp" in df.columns:
        idx = pd.Index(df["timestamp"].values)
        equity.index = idx
        net.index = idx
        held.index = idx

    metrics = performance_metrics(net, config.periods_per_year, positions=held)
    return BacktestResult(equity_curve=equity, returns=net, positions=held, metrics=metrics)
