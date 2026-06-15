"""Tests for reference levels, confluence scoring, and range studies (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.confluence import (
    confluence_reaction_study,
    range_exhaustion_study,
)
from kudbee_quant.confluence.scorer import _cluster_count, add_confluence
from kudbee_quant.levels import LEVEL_COLUMNS, build_levels, range_stats
from kudbee_quant.levels.builder import OPTIONAL_LEVEL_COLUMNS


def _ohlcv(n=900, seed=1):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.01, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.5, n),
    })


def test_build_levels_has_catalog_columns():
    f = build_levels(_ohlcv())
    # Default frame must produce every NON-opt-in catalog column; opt-in columns
    # (volume profile, ...) only appear when their feature flag is set.
    for col in LEVEL_COLUMNS:
        if col in OPTIONAL_LEVEL_COLUMNS:
            assert col not in f.columns, f"opt-in {col} leaked into default frame"
        else:
            assert col in f.columns, col
    assert "pct_adr_used" in f.columns and "adr" in f.columns


def test_adr_projection_brackets_open():
    f = build_levels(_ohlcv())
    ok = f.dropna(subset=["adr_high", "adr_low", "daily_open"])
    assert (ok["adr_high"] >= ok["daily_open"]).all()
    assert (ok["adr_low"] <= ok["daily_open"]).all()


def test_round_levels_bracket_close():
    f = build_levels(_ohlcv())
    assert (f["round_below"] <= f["close"]).all()
    assert (f["round_above"] >= f["close"]).all()


def test_cluster_count_merges_near_levels():
    # Three values, two within tol -> 2 clusters.
    assert _cluster_count(np.array([100.0, 100.5, 110.0]), tol=1.0) == 2
    assert _cluster_count(np.array([100.0, 101.5, 103.0]), tol=1.0) == 3
    assert _cluster_count(np.array([]), tol=1.0) == 0


def test_confluence_score_nonnegative_and_bounded():
    f = build_levels(_ohlcv())
    scored = add_confluence(f, tol_atr=0.3)
    assert (scored["confluence_score"] >= 0).all()
    assert (scored["confluence_score"] <= len(LEVEL_COLUMNS)).all()


def test_confluence_study_runs():
    f = build_levels(_ohlcv())
    table = confluence_reaction_study(f, horizon=6, min_n=5)
    assert {"confluence_score", "n", "mean_reaction_atr", "reversal_rate"} <= set(table.columns)
    assert (table["n"] > 0).all()


def test_range_exhaustion_buckets_monotonic_in_definition():
    f = build_levels(_ohlcv())
    table = range_exhaustion_study(f, horizon=8, min_n=5)
    assert "mean_fwd_range_atr" in table.columns
    assert (table["n"] > 0).all()


def test_range_stats_returns_positive_ranges():
    s = range_stats(_ohlcv())
    assert s["adr"] > 0 and s["awr"] > 0 and s["amr"] > 0
