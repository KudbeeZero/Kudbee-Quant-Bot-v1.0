"""Backtest + risk engine — the honesty core of Kudbee Quant.

This is where a signal stops being a pretty colour and becomes a measured
edge (or, just as often, a measured non-edge). Everything here reports the
downside as loudly as the upside:

  - engine:      event-driven backtester with fees & slippage (no lookahead)
  - metrics:     return AND risk metrics (Sharpe, drawdown, CVaR, ...)
  - montecarlo:  bootstrap distribution of outcomes + risk-of-ruin
  - sizing:      fractional Kelly with hard caps
  - walkforward: in-sample vs out-of-sample, to expose overfitting
  - strategy:    a PVSRA vector-candle strategy as the worked example
"""

from .engine import BacktestConfig, BacktestResult, run_backtest
from .metrics import performance_metrics
from .montecarlo import MonteCarloResult, monte_carlo
from .sizing import fractional_kelly
from .strategy import pvsra_mm_positions, pvsra_positions
from .walkforward import WalkForwardResult, walk_forward

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "run_backtest",
    "performance_metrics",
    "MonteCarloResult",
    "monte_carlo",
    "fractional_kelly",
    "pvsra_positions",
    "pvsra_mm_positions",
    "WalkForwardResult",
    "walk_forward",
]
