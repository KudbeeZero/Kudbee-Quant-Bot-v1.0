"""Tests for the walk-forward R-validation harness (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.validation.bracket_validation import (
    _cross_corr,
    validate_bracket,
    walkforward_bracket,
)


def _df_with_atr(n=300, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": close + 0.6, "low": close - 0.6, "close": close,
        "atr": 0.5,
    })


def test_walkforward_returns_one_row_per_fold():
    df = _df_with_atr(300)
    sig = pd.Series(np.where(np.arange(300) % 10 == 0, 1.0, 0.0))
    folds = walkforward_bracket(df, sig, n_folds=5)
    assert len(folds) == 5
    assert all("expectancy_r" in f and "fold" in f for f in folds)
    assert [f["fold"] for f in folds] == [0, 1, 2, 3, 4]


def test_validate_bracket_summary(monkeypatch):
    import kudbee_quant.validation.bracket_validation as bv
    frames = {"A": _df_with_atr(seed=1), "B": _df_with_atr(seed=2)}
    # Patch loaders so build_levels/load_ohlcv aren't needed (frames already have atr).
    monkeypatch.setattr(bv, "load_ohlcv", lambda spec, **k: frames[spec])
    monkeypatch.setattr(bv, "build_levels", lambda df: df)
    pos = lambda d: pd.Series(np.where(np.arange(len(d)) % 8 == 0, 1.0, 0.0), index=d.index)
    cells, summary = bv.validate_bracket(["A", "B"], pos, n_folds=4)
    assert summary["n_cells"] == 8  # 2 assets x 4 folds
    assert 0.0 <= summary["frac_positive"] <= 1.0 or np.isnan(summary["frac_positive"])
    assert set(cells["asset"]) == {"A", "B"}


def test_cross_corr_perfectly_correlated():
    base = _df_with_atr(seed=3)
    frames = {"A": base, "B": base.copy()}  # identical -> corr ~1
    assert _cross_corr(frames) > 0.9
