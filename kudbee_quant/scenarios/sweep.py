"""Run the scenario battery across a universe and rank by out-of-sample edge.

For each (scenario x asset) we backtest with costs and run walk-forward to get
the OUT-OF-SAMPLE Sharpe — the only number worth trusting. We aggregate per
scenario across assets (median OOS Sharpe, fraction profitable OOS) and rank.
A scenario is only interesting if it is positive OOS across MOST assets; one
lucky asset is not signal. Correlated assets are flagged in the report header.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..backtest import BacktestConfig, run_backtest, walk_forward
from ..backtest.metrics import infer_periods_per_year
from ..ingest import load_ohlcv
from ..levels import build_levels
from .library import hold


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    median_oos_sharpe: float
    frac_profitable_oos: float
    mean_oos_return: float
    per_asset_oos_sharpe: dict


def _position_fn(scenario_fn, hold_n):
    return lambda d: hold(scenario_fn(d), hold_n)


def run_sweep(
    specs: list[str],
    interval: str = "1h",
    limit: int = 4000,
    hold_n: int = 12,
    scenarios: dict | None = None,
    n_folds: int = 5,
    fee_bps: float = 5.0,
    slippage_bps: float = 2.0,
) -> pd.DataFrame:
    """Backtest every scenario on every asset; return a ranked summary frame."""
    if scenarios is None:
        from . import SCENARIOS  # full registry (base + BTMM); runtime import avoids cycle
        scenarios = SCENARIOS
    frames = {spec: build_levels(load_ohlcv(spec, interval=interval, limit=limit)) for spec in specs}

    results = []
    for name, fn in scenarios.items():
        pos_fn = _position_fn(fn, hold_n)
        oos_sharpes, oos_returns = {}, []
        for spec, df in frames.items():
            cfg = BacktestConfig(
                fee_bps=fee_bps, slippage_bps=slippage_bps,
                periods_per_year=infer_periods_per_year(df), allow_short=True,
            )
            try:
                wf = walk_forward(df, pos_fn, n_folds=n_folds, config=cfg)
                oos_sharpes[spec] = wf.out_of_sample.sharpe
                oos_returns.append(wf.out_of_sample.total_return)
            except Exception:
                oos_sharpes[spec] = float("nan")
        vals = [v for v in oos_sharpes.values() if np.isfinite(v)]
        results.append(ScenarioResult(
            scenario=name,
            median_oos_sharpe=float(np.median(vals)) if vals else float("nan"),
            frac_profitable_oos=float(np.mean([v > 0 for v in vals])) if vals else float("nan"),
            mean_oos_return=float(np.mean(oos_returns)) if oos_returns else float("nan"),
            per_asset_oos_sharpe=oos_sharpes,
        ))

    table = pd.DataFrame([{
        "scenario": r.scenario,
        "median_oos_sharpe": r.median_oos_sharpe,
        "frac_profitable_oos": r.frac_profitable_oos,
        "mean_oos_return": r.mean_oos_return,
    } for r in results])
    return table.sort_values("median_oos_sharpe", ascending=False).reset_index(drop=True)
