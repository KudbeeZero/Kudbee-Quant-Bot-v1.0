"""Regression locks for the 2026-07-02 engine-correctness fixes
(docs/audits/security-review-2026-07-02.md engine addendum).

Each test pins a specific bug the review found, so a future change can't silently
reintroduce it. Hermetic — no network.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# --- cache: atomic write + crash/truncation tolerance ------------------------

def test_cache_roundtrip_and_truncated_meta_is_a_miss(tmp_path):
    from kudbee_quant.ingest.cache import DataCache
    c = DataCache(root=tmp_path)
    df = pd.DataFrame({"a": [1, 2, 3]})
    c.put("k", df)
    pd.testing.assert_frame_equal(c.get("k", ttl_seconds=1e9), df)

    # Corrupt the meta file (simulates a crash mid-write): must be a MISS, not a raise.
    import hashlib
    digest = hashlib.sha256(b"k").hexdigest()
    (tmp_path / f"{digest}.meta.json").write_text("{not valid json")
    assert c.get("k", ttl_seconds=1e9) is None


def test_cache_leaves_no_tmp_files(tmp_path):
    from kudbee_quant.ingest.cache import DataCache
    c = DataCache(root=tmp_path)
    c.put("k", pd.DataFrame({"a": [1]}))
    assert not list(tmp_path.glob("*.tmp")), "atomic write should leave no .tmp residue"


# --- metrics: no NaN poisoning on ruin / no false-zero Sortino ---------------

def test_cagr_finite_on_total_loss():
    from kudbee_quant.backtest.metrics import performance_metrics
    # A -100%+ terminal equity must give a finite CAGR (-1.0), never NaN.
    r = pd.Series([-0.6, -0.6, -0.6])  # compounds below zero territory
    m = performance_metrics(r, periods_per_year=252)
    assert np.isfinite(m.cagr) and m.cagr <= 0
    assert np.isfinite(m.calmar)


def test_sortino_not_zero_when_no_downside():
    from kudbee_quant.backtest.metrics import performance_metrics
    r = pd.Series([0.01, 0.02, 0.015, 0.03])  # all gains, no losing bar
    m = performance_metrics(r, periods_per_year=252)
    # Undefined downside must NOT rank a no-loss book as worst (0.0); inf is honest.
    assert m.sortino == float("inf")


# --- meta model: no positional misalignment / single-class safety ------------

def test_meta_prob_rejects_width_mismatch(monkeypatch):
    from kudbee_quant.ml import meta_model as mm
    # Stub make_features so the test doesn't need a full build_levels frame.
    monkeypatch.setattr(mm, "make_features",
                        lambda df: pd.DataFrame({"a": [1.0] * len(df), "b": [2.0] * len(df)}, index=df.index))

    class _Model:
        n_features_in_ = 5  # model expects 5 cols; the frame will have 2
        classes_ = np.array([0, 1])

        def predict_proba(self, X):  # pragma: no cover - should not be reached
            return np.zeros((len(X), 2))

    df = pd.DataFrame(index=range(20))
    with pytest.raises(ValueError, match="feature mismatch"):
        mm.meta_prob_for_frame(_Model(), df)


def test_meta_prob_single_class_is_win_probability(monkeypatch):
    from kudbee_quant.ml import meta_model as mm
    monkeypatch.setattr(mm, "make_features",
                        lambda df: pd.DataFrame({"x": [1.0] * len(df)}, index=df.index))

    class _OneClassLoss:  # only ever saw class 0 (loss)
        classes_ = np.array([0])

        def predict_proba(self, X):
            return np.ones((len(X), 1))  # P(class=0) = 1

    df = pd.DataFrame(index=range(2))
    out = mm.meta_prob_for_frame(_OneClassLoss(), df, feature_columns=["x"])
    # The only class is LOSS, so P(win) must be ~0.0 — never the raw P(loss)=1.0.
    assert (out.to_numpy() == 0.0).all()
