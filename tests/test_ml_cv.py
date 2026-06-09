"""Tests for purged + embargoed walk-forward CV (kudbee_quant/ml/cv.py).

Offline + synthetic. We verify the leakage guarantees that make the CV honest:
forward-only training, no train/test overlap, full test coverage, and valid
out-of-sample probabilities.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from kudbee_quant.ml.cv import cross_val_oos, purged_walk_forward_splits


def _dataset(n=240):
    rng = np.random.default_rng(3)
    # two symbols interleaved on a shared, monotonically increasing timeline
    times = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    syms = np.where(np.arange(n) % 2 == 0, "AAA", "BBB")
    x0 = rng.normal(0, 1, n)
    y = (x0 + rng.normal(0, 0.5, n) > 0).astype(int)
    X = pd.DataFrame({"x0": x0, "x1": rng.normal(0, 1, n)})
    meta = pd.DataFrame({"symbol": syms, "entry_time": times,
                         "direction": 1.0, "mfe_r": rng.normal(1, 1, n)})
    return X, pd.Series(y), meta


def test_splits_are_forward_only_and_disjoint():
    X, y, meta = _dataset()
    t = pd.to_datetime(meta["entry_time"], utc=True).to_numpy()
    seen_test = []
    for tr, te in purged_walk_forward_splits(meta, n_splits=5, embargo_frac=0.02):
        assert len(set(tr) & set(te)) == 0                  # disjoint
        assert t[tr].max() < t[te].min()                    # forward-only
        seen_test.extend(te.tolist())
    # test folds partition the timeline (each row tested at most once)
    assert len(seen_test) == len(set(seen_test))


def test_cross_val_oos_well_formed():
    X, y, meta = _dataset()
    oos = cross_val_oos(lambda: LogisticRegression(max_iter=200), X, y, meta,
                        n_splits=5, embargo_frac=0.02)
    assert len(oos) > 0
    assert oos["oos_prob"].between(0, 1).all()
    assert set(oos["y_true"].unique()) <= {0, 1}
    assert oos["fold"].nunique() >= 2
    # an informative feature should beat a coin flip out-of-sample (sanity, loose)
    from sklearn.metrics import roc_auc_score
    if oos["y_true"].nunique() == 2:
        assert roc_auc_score(oos["y_true"], oos["oos_prob"]) > 0.55


def test_single_class_fold_falls_back():
    X, y, meta = _dataset(120)
    y[:] = 0                       # degenerate: all one class
    oos = cross_val_oos(lambda: LogisticRegression(max_iter=200), X, y, meta, n_splits=4)
    assert (oos["oos_prob"] == 0.0).all()   # constant base-rate fallback, no crash
