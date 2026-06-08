"""Tests for the scenario battery + sweep (deterministic, no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.levels import build_levels
from kudbee_quant.scenarios import SCENARIOS, hold, run_sweep


def _ohlcv(n=1000, seed=3):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.012, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n),
    })


def test_hold_extends_signal():
    raw = pd.Series([0, 1, 0, 0, 0, -1, 0, 0], dtype=float)
    held = hold(raw, 2)
    # 1 persists for 2 bars then stops; -1 starts at its bar.
    assert held.tolist() == [0, 1, 1, 1, 0, -1, -1, -1]


def test_all_scenarios_return_valid_signals():
    f = build_levels(_ohlcv())
    for name, fn in SCENARIOS.items():
        sig = fn(f)
        assert len(sig) == len(f), name
        vals = sig.dropna().unique()
        assert set(np.sign(vals)).issubset({-1.0, 0.0, 1.0}), name


def test_scenarios_are_not_all_empty():
    f = build_levels(_ohlcv())
    active = {name: int((fn(f).fillna(0) != 0).sum()) for name, fn in SCENARIOS.items()}
    # Most scenarios should fire at least once on 1000 bars of random-ish data.
    assert sum(v > 0 for v in active.values()) >= len(SCENARIOS) // 2


def test_run_sweep_ranks_scenarios(monkeypatch):
    # Patch the loader so the sweep uses synthetic frames (no network).
    import kudbee_quant.scenarios.sweep as sweepmod
    frames = {"A": _ohlcv(seed=1), "B": _ohlcv(seed=2)}
    monkeypatch.setattr(sweepmod, "load_ohlcv", lambda spec, **k: frames[spec])
    table = run_sweep(["A", "B"], hold_n=8, n_folds=3)
    assert {"scenario", "median_oos_sharpe", "frac_profitable_oos"} <= set(table.columns)
    assert len(table) == len(SCENARIOS)
    # Sorted descending by median OOS Sharpe.
    s = table["median_oos_sharpe"].dropna().tolist()
    assert s == sorted(s, reverse=True)
