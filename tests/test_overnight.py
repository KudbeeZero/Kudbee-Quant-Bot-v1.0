"""Tests for the overnight research harness (scripts/overnight_research.py).

These use a small synthetic OHLCV frame so they run offline (no network) and
fast. They verify the contract the overnight loop relies on: every candidate is
callable and returns a well-formed (signal, size, overrides) triple, and the
evaluator produces an honest record with one of the known verdicts. We are NOT
asserting any candidate is profitable — that's the harness's job to MEASURE, not
the test's job to presume.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from overnight_candidates import REGISTRY  # noqa: E402
import overnight_research as orx  # noqa: E402

from kudbee_quant.confluence.stack import confluence_position, confluence_score  # noqa: E402
from kudbee_quant.levels import build_levels  # noqa: E402


@pytest.fixture(scope="module")
def frame():
    """A deterministic synthetic 1h frame with enough bars for the rolling
    windows (200/500) the candidates use."""
    n = 1200
    rng = np.random.default_rng(42)
    # a trending-with-noise close so the confluence signal actually fires
    steps = rng.normal(0.0005, 0.01, n).cumsum()
    close = 100 * np.exp(steps)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = rng.lognormal(10, 0.5, n)
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    raw = pd.DataFrame({"timestamp": ts, "open": open_, "high": high,
                        "low": low, "close": close, "volume": vol,
                        "quote_volume": vol * close, "trades": (vol / 10).astype(int)})
    return build_levels(raw)


def test_every_candidate_returns_valid_triple(frame):
    scored = confluence_score(frame)
    base = confluence_position(frame, min_pct=0.50, trend_align=True)
    for name, (fn, desc) in REGISTRY.items():
        sig, size, overrides = fn(frame, scored, base)
        sig = pd.Series(sig, index=frame.index)
        assert len(sig) == len(frame), f"{name}: signal length mismatch"
        assert set(np.unique(sig.fillna(0.0))) <= {-1.0, 0.0, 1.0}, f"{name}: non {{-1,0,1}} signal"
        # a gating candidate must be a SUBSET of the baseline entries
        nonzero_outside_base = ((sig != 0) & (base == 0)).sum()
        if not overrides and size is None:
            assert nonzero_outside_base == 0, f"{name}: introduced entries outside baseline"
        assert isinstance(overrides, dict), f"{name}: overrides must be a dict"
        if size is not None:
            s = pd.Series(size, index=frame.index).fillna(0.0)
            assert (s >= 0).all() and (s <= 1.0001).all(), f"{name}: size out of [0,1]"


def test_evaluate_produces_honest_record(frame, monkeypatch):
    # use one symbol's synthetic frame as the whole universe (offline)
    frames = {"SYNTH": frame}
    rec = orx.evaluate("clean_trend", frames)
    for key in ("name", "verdict", "delta", "h1_delta", "h2_delta",
                "n_trades", "base_exp", "cand_exp"):
        assert key in rec
    assert rec["verdict"] in {"WINNER", "SUGGESTIVE", "NEUTRAL", "HURTS", "THIN"}
    assert isinstance(rec["delta"], float)


def test_queue_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(orx, "QUEUE_PATH", tmp_path / "q.json")
    orx.enqueue(["clean_trend", "deeper_retrace"])
    q = orx._queue()
    assert q["pending"] == ["clean_trend", "deeper_retrace"]
    # 'all' should add the rest without duplicating
    orx.enqueue(["all"])
    assert len(q["pending"]) <= len(REGISTRY)
    assert len(set(orx._queue()["pending"])) == len(orx._queue()["pending"])
