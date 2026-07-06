"""Contract tests for the meta-labeling dataset builder (kudbee_quant/ml/labels.py).

Offline + synthetic (no network). We assert the dataset is well-formed and aligned
(one feature row per labeled trade, binary labels, entry_bar in range) — NOT that
any model is accurate. Honest measurement is the meta_model/CV layer's job.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.levels import build_levels
from kudbee_quant.ml import build_dataset, make_features, make_labels


@pytest.fixture(scope="module")
def frame():
    n = 1500
    rng = np.random.default_rng(7)
    close = 100 * np.exp(rng.normal(0.0004, 0.01, n).cumsum())
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    op = np.concatenate([[close[0]], close[:-1]])
    vol = rng.lognormal(10, 0.5, n)
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    raw = pd.DataFrame({"timestamp": ts, "open": op, "high": high, "low": low,
                        "close": close, "volume": vol, "quote_volume": vol * close,
                        "trades": (vol / 10).astype(int)})
    return build_levels(raw)


def test_features_are_causal_and_numeric(frame):
    f = make_features(frame)
    assert len(f) == len(frame)
    assert f.select_dtypes(exclude="number").empty, "all meta-features must be numeric"


def test_labels_align_to_entries(frame):
    sig = confluence_position(frame, min_pct=0.5, trend_align=True)
    labels = make_labels(frame, sig, target_r=3.0)
    if labels.empty:
        pytest.skip("no trades on synthetic frame")
    assert set(labels["label"].unique()) <= {0, 1}
    assert labels["entry_bar"].between(0, len(frame) - 1).all()
    # label must equal (trade was profitable) — ties the meta-model to expectancy
    assert (labels["label"] == (labels["realized_r"] > 0).astype(int)).all()


def test_build_dataset_shapes(frame):
    sig = lambda d: confluence_position(d, min_pct=0.5, trend_align=True)
    X, y, meta = build_dataset({"SYNTH": frame}, sig, target_r=3.0)
    if len(y) == 0:
        pytest.skip("no trades on synthetic frame")
    assert len(X) == len(y) == len(meta)
    assert "n_trades" in meta.attrs and "n_signal_bars" in meta.attrs
    assert meta["entry_time"].notna().any()


def test_build_dataset_sets_label_horizon_from_bar_spacing_and_max_bars(frame):
    """MEMORY §86/N6: the CV purge (ml/cv.py) needs the longest a label can take
    to resolve, or it can only purge by entry_time and leak label-end overlap
    across the fold boundary. build_dataset must compute it: bar-interval (here
    1h, from the fixture) * max_bars, and expose it via meta.attrs."""
    sig = lambda d: confluence_position(d, min_pct=0.5, trend_align=True)
    X, y, meta = build_dataset({"SYNTH": frame}, sig, target_r=3.0, max_bars=24)
    if len(y) == 0:
        pytest.skip("no trades on synthetic frame")
    assert meta.attrs["label_horizon"] == pd.Timedelta(hours=24)
