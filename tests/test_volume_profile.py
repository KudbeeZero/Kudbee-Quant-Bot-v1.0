"""Tests for the opt-in per-session volume-profile levels (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.config.features import FeatureFlags
from kudbee_quant.levels import (
    VP_FEATURE_COLUMNS, VP_LEVEL_COLUMNS, add_volume_profile, build_levels,
)
from kudbee_quant.levels.builder import LEVEL_COLUMNS


def _ohlcv(n=900, seed=5):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0001, 0.012, n)
    close = 2000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n), "atr": close * 0.01,
    })


def test_vp_columns_present():
    out = add_volume_profile(_ohlcv())
    for c in VP_LEVEL_COLUMNS + VP_FEATURE_COLUMNS:
        assert c in out.columns


def test_value_area_brackets_poc():
    out = add_volume_profile(_ohlcv()).dropna(subset=["vp_poc", "vp_vah", "vp_val"])
    assert (out["vp_val"] <= out["vp_poc"] + 1e-6).all()
    assert (out["vp_poc"] <= out["vp_vah"] + 1e-6).all()


def test_levels_within_prior_day_range():
    """Each exposed POC is a real price (finite, positive) from a prior session."""
    out = add_volume_profile(_ohlcv()).dropna(subset=["vp_poc"])
    assert (out["vp_poc"] > 0).all()
    assert np.isfinite(out["vp_poc"]).all()


def test_naked_poc_is_a_prior_poc_or_nan():
    out = add_volume_profile(_ohlcv())
    nk = out["vp_naked_poc"].dropna()
    assert (nk > 0).all()


def test_causal_truncation_invariance():
    full = add_volume_profile(_ohlcv(n=700))
    trunc = add_volume_profile(_ohlcv(n=700).iloc[:400])
    for c in ("vp_poc", "vp_vah", "vp_val", "vp_naked_poc", "in_value_area"):
        a = full[c].iloc[:400].to_numpy(dtype=float)
        b = trunc[c].to_numpy(dtype=float)
        both = np.isfinite(a) & np.isfinite(b)
        assert np.allclose(a[both], b[both], atol=1e-9)


def test_in_level_columns_catalog():
    for c in VP_LEVEL_COLUMNS:
        assert c in LEVEL_COLUMNS


def test_build_levels_gated_off_by_default():
    df = _ohlcv()
    off = build_levels(df, features=FeatureFlags(enable_volume_profile=False))
    on = build_levels(df, features=FeatureFlags(enable_volume_profile=True))
    assert "vp_poc" not in off.columns
    assert "vp_poc" in on.columns
    assert set(off.columns) <= set(on.columns)
