"""Tests for the confluence-stack tester (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.confluence import (
    confluence_directional_study,
    confluence_position,
    confluence_score,
    factor_votes,
)
from kudbee_quant.levels import build_levels
from kudbee_quant.scenarios import SCENARIOS
from kudbee_quant.scenarios.audit import lookahead_audit


def _ohlcv(n=900, seed=11):
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


def test_factor_votes_are_directional():
    f = build_levels(_ohlcv())
    votes = factor_votes(f)
    assert votes.shape[0] == len(f)
    assert set(np.unique(votes.values)).issubset({-1.0, 0.0, 1.0})
    assert votes.shape[1] >= 6  # several factors present


def test_score_strength_consistent():
    f = confluence_score(build_levels(_ohlcv()))
    assert (f["strength"] == f["net_score"].abs()).all()
    assert (f["direction"] == np.sign(f["net_score"])).all()
    assert (f["strength"] <= f["n_factors"]).all()


def test_confluence_pct_and_min_pct_threshold():
    from kudbee_quant.confluence.stack import confluence_sized_position
    f = build_levels(_ohlcv())
    scored = confluence_score(f)
    assert "confluence_pct" in scored.columns
    assert (scored["confluence_pct"] == scored["strength"] / scored["n_factors"]).all()
    assert ((scored["confluence_pct"] >= 0) & (scored["confluence_pct"] <= 1)).all()
    # min_pct gate fires only where pct >= threshold.
    pos = confluence_position(f, min_pct=0.5)
    active = pos != 0
    assert (scored.loc[active, "confluence_pct"] >= 0.5).all()
    # Sized position: size in [0,1], zero below the threshold.
    sig, size = confluence_sized_position(f, min_pct=0.5, floor_size=0.25)
    assert ((size >= 0) & (size <= 1)).all()
    assert (size[sig == 0] == 0).all()
    assert (size[sig != 0] >= 0.25 - 1e-9).all()


def test_position_only_fires_at_high_strength():
    f = build_levels(_ohlcv())
    pos = confluence_position(f, min_strength=4.0)
    scored = confluence_score(f)
    # Wherever a position is taken, strength must be >= the threshold.
    active = pos != 0
    assert (scored.loc[active, "strength"] >= 4.0).all()


def test_trend_align_drops_counter_trend_signals():
    import numpy as np
    f = build_levels(_ohlcv())
    scored = confluence_score(f)
    base = confluence_position(f, min_pct=0.5)
    filt = confluence_position(f, min_pct=0.5, trend_align=True)
    # The filter only removes signals, never adds or flips them.
    assert ((filt == base) | (filt == 0.0)).all()
    assert (filt != 0).sum() <= (base != 0).sum()
    # Every surviving signal agrees with the 800-EMA HTF trend.
    htf = np.sign(scored["close"] - scored["ema_800"])
    active = filt != 0
    assert (np.sign(filt[active]) == htf[active]).all()


def test_directional_study_table():
    f = build_levels(_ohlcv())
    table = confluence_directional_study(f, horizon=6, min_n=5)
    assert {"strength_bucket", "n", "win_rate", "mean_dir_return"} <= set(table.columns)
    # Buckets sorted ascending by strength.
    assert table["strength_bucket"].is_monotonic_increasing


def test_confluence_stack_scenario_registered_and_causal():
    assert "confluence_stack" in SCENARIOS
    df = _ohlcv(700)
    r = lookahead_audit(df, SCENARIOS["confluence_stack"], n_checks=20, min_history=300,
                        name="confluence_stack")
    assert r.clean
