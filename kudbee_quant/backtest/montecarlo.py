"""Monte Carlo robustness — the panel the fantasy dashboards leave out.

We bootstrap-resample the strategy's per-bar returns to build a distribution
of plausible outcomes, then report the *bad* percentiles and the probability
of ruin as prominently as the median. A single backtest is one draw from
this distribution; the equity screenshot people post is the luckiest draw.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import max_drawdown


@dataclass(frozen=True)
class MonteCarloResult:
    n_paths: int
    final_return_p05: float      # 5th percentile (a bad-but-plausible outcome)
    final_return_p50: float      # median
    final_return_p95: float      # 95th percentile
    max_drawdown_p50: float      # median worst drawdown
    max_drawdown_p95: float      # 95th-percentile-worst drawdown (very bad)
    risk_of_ruin: float          # P(equity ever falls below ruin threshold)
    prob_profit: float           # P(final return > 0)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def monte_carlo(
    returns: pd.Series,
    n_paths: int = 5000,
    block_size: int = 1,
    ruin_threshold: float = -0.5,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Bootstrap the return series into many resampled equity paths.

    Args:
        returns: per-bar net strategy returns from a backtest.
        n_paths: number of simulated paths.
        block_size: >1 uses a block bootstrap to preserve short-term
            autocorrelation (recommended for real return series).
        ruin_threshold: equity drawdown counted as "ruin" (e.g. -0.5 = -50%).
        seed: RNG seed for reproducibility.
    """
    r = pd.Series(returns).dropna().astype(float).to_numpy()
    n = r.size
    if n == 0:
        return MonteCarloResult(0, 0, 0, 0, 0, 0, 0, 0)

    rng = np.random.default_rng(seed)
    block_size = max(1, int(block_size))

    final_returns = np.empty(n_paths)
    max_dds = np.empty(n_paths)
    ruined = 0

    for i in range(n_paths):
        if block_size == 1:
            sample = rng.choice(r, size=n, replace=True)
        else:
            n_blocks = int(np.ceil(n / block_size))
            starts = rng.integers(0, n, size=n_blocks)
            sample = np.concatenate([np.take(r, range(s, s + block_size), mode="wrap") for s in starts])[:n]
        equity = np.cumprod(1.0 + sample)
        final_returns[i] = equity[-1] - 1.0
        dd = max_drawdown(equity)
        max_dds[i] = dd
        if dd <= ruin_threshold:
            ruined += 1

    return MonteCarloResult(
        n_paths=n_paths,
        final_return_p05=float(np.percentile(final_returns, 5)),
        final_return_p50=float(np.percentile(final_returns, 50)),
        final_return_p95=float(np.percentile(final_returns, 95)),
        max_drawdown_p50=float(np.percentile(max_dds, 50)),
        max_drawdown_p95=float(np.percentile(max_dds, 5)),  # 5th pct = worst tail
        risk_of_ruin=float(ruined / n_paths),
        prob_profit=float((final_returns > 0).mean()),
    )
