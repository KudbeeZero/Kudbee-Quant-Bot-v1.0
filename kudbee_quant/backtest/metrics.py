"""Performance AND risk metrics. Risk is never optional here.

All ratios are computed from a per-bar strategy-return series. ``periods``
is the number of bars per year used for annualization (e.g. 24*365 for
hourly crypto). We annualize honestly and never hide the drawdown.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PerformanceMetrics:
    n_bars: int
    total_return: float          # cumulative, e.g. 0.25 == +25%
    cagr: float                  # annualized compound growth
    ann_volatility: float
    sharpe: float                # annualized, rf=0
    sortino: float               # annualized, downside-only
    max_drawdown: float          # most negative peak-to-trough, e.g. -0.30
    calmar: float                # cagr / |max_drawdown|
    var_95: float                # per-bar 95% Value at Risk (negative)
    cvar_95: float               # per-bar 95% Conditional VaR (negative)
    win_rate: float              # fraction of positive bars
    profit_factor: float         # gross gains / gross losses
    exposure: float              # fraction of bars holding a position

    def to_dict(self) -> dict:
        return asdict(self)


def infer_periods_per_year(df: pd.DataFrame) -> float:
    """Estimate bars-per-year from actual bar density over the calendar span.

    Uses (n_bars - 1) / (span in years) rather than the median spacing, so
    assets with regular gaps (equities closed nights/weekends) annualize
    correctly instead of being inflated as if they traded 24/7. Lets one
    universe mix continuous hourly crypto (~8766) and gappy hourly equities
    (~1600) without skewing Sharpe. Falls back to 365 when unusable.
    """
    if "timestamp" not in df.columns or len(df) < 3:
        return 365.0
    ts = pd.to_datetime(df["timestamp"], utc=True).sort_values()
    span_years = (ts.iloc[-1] - ts.iloc[0]).total_seconds() / (365.25 * 24 * 3600)
    if span_years <= 0:
        return 365.0
    return float((len(ts) - 1) / span_years)


def max_drawdown(equity: pd.Series | np.ndarray) -> float:
    equity = np.asarray(equity, dtype=float)
    if equity.size == 0:
        return 0.0
    running_max = np.maximum.accumulate(equity)
    drawdowns = equity / running_max - 1.0
    return float(drawdowns.min())


def performance_metrics(
    returns: pd.Series,
    periods_per_year: float,
    positions: pd.Series | None = None,
) -> PerformanceMetrics:
    """Compute the full metric set from a per-bar return series.

    Args:
        returns: per-bar strategy returns (already net of costs).
        periods_per_year: bars per year, for annualization.
        positions: optional per-bar position series, for exposure.
    """
    r = pd.Series(returns).dropna().astype(float)
    n = int(r.size)
    if n == 0:
        return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    equity = (1.0 + r).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    years = n / periods_per_year
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0

    ann_vol = float(r.std(ddof=1) * np.sqrt(periods_per_year)) if n > 1 else 0.0
    mean = float(r.mean())
    sharpe = float(mean / r.std(ddof=1) * np.sqrt(periods_per_year)) if n > 1 and r.std(ddof=1) > 0 else 0.0

    downside = r[r < 0]
    dstd = float(downside.std(ddof=1)) if downside.size > 1 else 0.0
    sortino = float(mean / dstd * np.sqrt(periods_per_year)) if dstd > 0 else 0.0

    mdd = max_drawdown(equity)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else 0.0

    var_95 = float(np.percentile(r, 5))
    tail = r[r <= var_95]
    cvar_95 = float(tail.mean()) if tail.size > 0 else var_95

    wins = r[r > 0]
    losses = r[r < 0]
    win_rate = float((r > 0).mean())
    gross_gain = float(wins.sum())
    gross_loss = float(-losses.sum())
    profit_factor = float(gross_gain / gross_loss) if gross_loss > 0 else float("inf")

    if positions is not None:
        exposure = float((pd.Series(positions).fillna(0) != 0).mean())
    else:
        exposure = float("nan")

    return PerformanceMetrics(
        n_bars=n,
        total_return=total_return,
        cagr=cagr,
        ann_volatility=ann_vol,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=mdd,
        calmar=calmar,
        var_95=var_95,
        cvar_95=cvar_95,
        win_rate=win_rate,
        profit_factor=profit_factor,
        exposure=exposure,
    )
