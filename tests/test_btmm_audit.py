"""Tests for the BTMM scenarios, indicators, and the lookahead self-audit."""
import numpy as np
import pandas as pd

from kudbee_quant.levels import build_levels
from kudbee_quant.scenarios import SCENARIOS
from kudbee_quant.scenarios.audit import audit_all, lookahead_audit
from kudbee_quant.scenarios.btmm import BTMM_SCENARIOS
from kudbee_quant.scenarios.indicators import add_emas, cross_up, swing_pivots


def _ohlcv(n=900, seed=5):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.011, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n),
    })


def test_emas_are_causal():
    df = _ohlcv(200)
    e_full = add_emas(df, (13,))["ema_13"]
    e_trunc = add_emas(df.iloc[:120], (13,))["ema_13"]
    # EMA at bar 119 must be identical whether or not later bars exist.
    assert np.isclose(e_full.iloc[119], e_trunc.iloc[119])


def test_swing_pivots_confirmed_late():
    df = _ohlcv(200)
    p = swing_pivots(df, left=3, right=3)
    # A new pivot marker is placed at i+right, never on a future-dependent bar.
    assert "new_swing_high" in p.columns
    assert p["swing_high_price"].notna().sum() > 0


def test_all_btmm_scenarios_valid_signals():
    f = build_levels(_ohlcv())
    for name, fn in BTMM_SCENARIOS.items():
        sig = fn(f)
        assert len(sig) == len(f), name
        vals = pd.Series(sig).dropna().unique()
        assert set(np.sign(vals)).issubset({-1.0, 0.0, 1.0}), name


def test_registry_includes_btmm():
    for k in BTMM_SCENARIOS:
        assert k in SCENARIOS


def test_audit_flags_a_planted_lookahead():
    df = _ohlcv(700)

    # A deliberately cheating scenario: uses the NEXT bar's close (future).
    def cheater(levels_df):
        future = levels_df["close"].shift(-1)
        return np.sign(future - levels_df["close"]).fillna(0.0)

    r = lookahead_audit(df, cheater, n_checks=40, min_history=300, name="cheater")
    assert not r.clean and r.mismatches > 0


def test_audit_passes_causal_scenario():
    df = _ohlcv(700)

    def causal(levels_df):
        return np.sign(levels_df["close"] - levels_df["close"].shift(1)).fillna(0.0)

    r = lookahead_audit(df, causal, n_checks=40, min_history=300, name="causal")
    assert r.clean


def test_audit_all_runs_over_registry():
    df = _ohlcv(700)
    # Audit a couple of real scenarios end-to-end (full pipeline).
    subset = {k: SCENARIOS[k] for k in ["ema_cross_13_50", "asian_stophunt"]}
    table = audit_all(df, subset, n_checks=25, min_history=300)
    assert set(table["scenario"]) == set(subset)
    assert table["clean"].all()  # both must be causal after the lookahead fix
