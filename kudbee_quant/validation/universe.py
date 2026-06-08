"""Universe-level validation (see package docstring)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from ..backtest import BacktestConfig, monte_carlo, run_backtest, walk_forward
from ..ingest import BinanceClient

PositionFn = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class AssetReport:
    symbol: str
    n_bars: int
    full_return: float          # whole-sample total return (context only)
    full_sharpe: float
    max_drawdown: float
    is_sharpe: float            # walk-forward in-sample Sharpe
    oos_sharpe: float           # walk-forward OUT-OF-SAMPLE Sharpe (what counts)
    oos_return: float
    oos_prob_profit: float      # Monte Carlo on OOS returns
    is_oos_gap: float           # oos_sharpe - is_sharpe (big |gap| => unstable)

    @property
    def profitable_oos(self) -> bool:
        return self.oos_return > 0 and self.oos_sharpe > 0


@dataclass(frozen=True)
class UniverseReport:
    assets: list[AssetReport]
    frac_profitable_oos: float
    median_oos_sharpe: float
    median_oos_prob_profit: float
    median_abs_is_oos_gap: float
    median_cross_corr: float    # median pairwise return correlation
    effective_n: float          # correlation-adjusted independent asset count
    verdict: str
    robust: bool
    notes: list[str] = field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([a.__dict__ for a in self.assets])


def _assess_asset(symbol: str, df: pd.DataFrame, strategy_fn: PositionFn,
                  config: BacktestConfig, n_folds: int, mc_paths: int) -> AssetReport:
    full = run_backtest(df, strategy_fn(df), config)
    wf = walk_forward(df, strategy_fn, n_folds=n_folds, config=config)
    oos_returns = wf.oos_equity.pct_change().dropna()
    mc = monte_carlo(oos_returns, n_paths=mc_paths, block_size=24)
    return AssetReport(
        symbol=symbol,
        n_bars=full.metrics.n_bars,
        full_return=full.metrics.total_return,
        full_sharpe=full.metrics.sharpe,
        max_drawdown=full.metrics.max_drawdown,
        is_sharpe=wf.in_sample.sharpe,
        oos_sharpe=wf.out_of_sample.sharpe,
        oos_return=wf.out_of_sample.total_return,
        oos_prob_profit=mc.prob_profit,
        is_oos_gap=wf.sharpe_decay,
    )


def _effective_n(n: int, median_corr: float) -> float:
    """Correlation-adjusted independent asset count: n / (1 + (n-1)*rho).

    Highly correlated assets are not independent tests; five crypto majors
    that move together count as barely more than one bet. This keeps the
    harness from mistaking correlation for confirmation.
    """
    rho = float(np.clip(median_corr, 0.0, 1.0))
    return n / (1.0 + (n - 1) * rho) if n > 0 else 0.0


def _verdict(assets: list[AssetReport], median_corr: float = 0.0) -> UniverseReport:
    """Conservative aggregation. We only call an edge 'robust' when it holds
    across enough *independent* assets OOS, with stable IS/OOS behaviour.
    A large IS/OOS gap is treated as instability, and correlated assets are
    discounted to an effective independent count.
    """
    n = len(assets)
    frac_prof = float(np.mean([a.profitable_oos for a in assets])) if n else 0.0
    med_oos_sharpe = float(np.median([a.oos_sharpe for a in assets])) if n else 0.0
    med_prob = float(np.median([a.oos_prob_profit for a in assets])) if n else 0.0
    med_gap = float(np.median([abs(a.is_oos_gap) for a in assets])) if n else 0.0
    n_eff = _effective_n(n, median_corr)

    notes: list[str] = []
    if n < 3:
        notes.append(f"Only {n} asset(s) tested — too few to generalize; widen the universe.")
    if n >= 3 and n_eff < 3:
        notes.append(
            f"Assets are highly correlated (median rho {median_corr:.2f}): {n} assets "
            f"behave like ~{n_eff:.1f} independent bets. 'Profitable on most' is therefore "
            "much weaker evidence than the headline count, and a rising market alone can "
            "carry a long-biased strategy. Add uncorrelated assets / regimes."
        )
    if med_gap > 1.5:
        notes.append(
            f"Median |IS-OOS Sharpe gap| is {med_gap:.2f}: in-sample and out-of-sample "
            "disagree a lot, which usually means noise rather than a stable edge."
        )
    if frac_prof < 1.0 and n:
        losers = [a.symbol for a in assets if not a.profitable_oos]
        if losers:
            notes.append(f"Not profitable OOS on: {', '.join(losers)}.")
    if any(a.max_drawdown <= -0.20 for a in assets):
        worst = min(a.max_drawdown for a in assets)
        notes.append(
            f"Drawdowns are large (worst {worst:.0%}) even when profitable — this is not "
            "a 'low risk' strategy regardless of the return."
        )

    robust = (
        n >= 3
        and n_eff >= 3            # correlated majors cannot satisfy this alone
        and frac_prof >= 0.6
        and med_oos_sharpe >= 1.0
        and med_prob >= 0.6
        and med_gap <= 1.5
    )
    if robust:
        verdict = (
            f"Edge looks ROBUST so far: profitable OOS on {frac_prof:.0%} of "
            f"{n} assets (~{n_eff:.1f} independent), median OOS Sharpe "
            f"{med_oos_sharpe:.2f}, stable IS/OOS. Still validate on more "
            "history and live-paper before any capital."
        )
    else:
        verdict = (
            f"Edge NOT established: profitable OOS on {frac_prof:.0%} of {n} assets "
            f"(~{n_eff:.1f} independent), median OOS Sharpe {med_oos_sharpe:.2f}. "
            "Promising but unproven — see notes."
        )

    return UniverseReport(
        assets=assets,
        frac_profitable_oos=frac_prof,
        median_oos_sharpe=med_oos_sharpe,
        median_oos_prob_profit=med_prob,
        median_abs_is_oos_gap=med_gap,
        median_cross_corr=median_corr,
        effective_n=n_eff,
        verdict=verdict,
        robust=robust,
        notes=notes,
    )


def validate_frames(
    frames: dict[str, pd.DataFrame],
    strategy_fn: PositionFn,
    config: BacktestConfig | None = None,
    n_folds: int = 5,
    mc_paths: int = 2000,
) -> UniverseReport:
    """Validate a strategy across pre-loaded {symbol: OHLCV} frames.

    This is the network-free core; ``validate_universe`` fetches then calls it.
    """
    config = config or BacktestConfig()
    reports = [
        _assess_asset(sym, df, strategy_fn, config, n_folds, mc_paths)
        for sym, df in frames.items()
    ]
    return _verdict(reports, median_corr=_median_cross_corr(frames))


def _median_cross_corr(frames: dict[str, pd.DataFrame]) -> float:
    """Median pairwise correlation of asset close-to-close returns."""
    if len(frames) < 2:
        return 0.0
    series = {}
    for sym, df in frames.items():
        if "timestamp" in df.columns:
            s = df.set_index("timestamp")["close"]
        else:
            s = df["close"]
        series[sym] = s.astype(float).pct_change()
    rets = pd.DataFrame(series).dropna()
    if len(rets) < 3 or rets.shape[1] < 2:
        return 0.0
    corr = rets.corr().to_numpy()
    off_diag = corr[np.triu_indices(corr.shape[0], k=1)]
    off_diag = off_diag[~np.isnan(off_diag)]
    return float(np.median(off_diag)) if off_diag.size else 0.0


def validate_universe(
    symbols: list[str],
    strategy_fn: PositionFn,
    interval: str = "1h",
    limit: int = 4000,
    config: BacktestConfig | None = None,
    n_folds: int = 5,
    mc_paths: int = 2000,
    client: BinanceClient | None = None,
) -> UniverseReport:
    """Fetch each symbol's history and validate the strategy across all of them."""
    client = client or BinanceClient()
    frames = {sym: client.klines(sym, interval=interval, limit=limit) for sym in symbols}
    return validate_frames(frames, strategy_fn, config, n_folds, mc_paths)
