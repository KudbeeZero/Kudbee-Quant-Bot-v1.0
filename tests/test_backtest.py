"""Tests for the backtest + risk engine (deterministic, no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.backtest import (
    BacktestConfig,
    fractional_kelly,
    monte_carlo,
    pvsra_positions,
    run_backtest,
    walk_forward,
)
from kudbee_quant.backtest.metrics import max_drawdown, performance_metrics


def _trending_ohlcv(n: int = 400, drift: float = 0.001, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, 0.01, n)
    close = 100 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.003, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.003, n)))
    vol = rng.lognormal(5, 0.6, n)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": close, "high": high, "low": low, "close": close, "volume": vol,
        }
    )


def test_no_lookahead_position_is_shifted():
    df = _trending_ohlcv(50)
    pos = pd.Series(1.0, index=range(len(df)))  # always-long target
    res = run_backtest(df, pos, BacktestConfig(fee_bps=0, slippage_bps=0))
    # First held position must be 0 (we only act on the *next* bar).
    assert res.positions.iloc[0] == 0.0
    # Always-long, no costs => equity tracks buy & hold from bar 1.
    expected = (1 + df["close"].pct_change().fillna(0)).cumprod().iloc[-1]
    assert np.isclose(res.equity_curve.iloc[-1], expected, rtol=1e-9)


def test_costs_reduce_returns():
    df = _trending_ohlcv(200)
    pos = pvsra_positions(df)
    free = run_backtest(df, pos, BacktestConfig(fee_bps=0, slippage_bps=0))
    costly = run_backtest(df, pos, BacktestConfig(fee_bps=10, slippage_bps=5))
    assert costly.equity_curve.iloc[-1] < free.equity_curve.iloc[-1]


def test_max_drawdown_is_nonpositive():
    df = _trending_ohlcv(300)
    res = run_backtest(df, pvsra_positions(df))
    assert res.metrics.max_drawdown <= 0.0
    assert max_drawdown([1.0, 2.0, 1.0]) == -0.5


def test_monte_carlo_brackets_and_probabilities():
    df = _trending_ohlcv(500, drift=0.0015)
    res = run_backtest(df, pvsra_positions(df))
    mc = monte_carlo(res.returns, n_paths=1000, block_size=12, seed=1)
    assert mc.final_return_p05 <= mc.final_return_p50 <= mc.final_return_p95
    assert 0.0 <= mc.risk_of_ruin <= 1.0
    assert 0.0 <= mc.prob_profit <= 1.0
    assert mc.max_drawdown_p95 <= mc.max_drawdown_p50 <= 0.0


def test_fractional_kelly_is_capped_and_nonnegative():
    good = pd.Series(np.r_[np.full(80, 0.02), np.full(20, -0.01)])
    f = fractional_kelly(good, fraction=0.25, cap=1.0)
    assert 0.0 <= f <= 1.0
    # A pure-loss series yields zero recommended size.
    assert fractional_kelly(pd.Series([-0.01, -0.02, -0.03])) == 0.0


def test_walk_forward_scores_out_of_sample():
    df = _trending_ohlcv(1000, drift=0.0012)
    wf = walk_forward(df, pvsra_positions, n_folds=4)
    assert wf.n_folds >= 1
    assert wf.out_of_sample.n_bars > 0
    assert isinstance(wf.sharpe_decay, float)


def test_metrics_empty_series_safe():
    m = performance_metrics(pd.Series([], dtype=float), 8760)
    assert m.n_bars == 0 and m.sharpe == 0.0
