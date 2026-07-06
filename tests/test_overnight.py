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
import time
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


def test_generated_candidates_obey_the_contract(frame):
    """DMN (idea_generator): every GENERATED candidate is a well-formed filter —
    signal in {-1,0,1}, a subset of the baseline (gates only mask), dict overrides."""
    import idea_generator as gen
    scored = confluence_score(frame)
    base = confluence_position(frame, min_pct=0.50, trend_align=True)
    generated = gen.generate_candidates(skip_noop=False)
    assert generated, "generator produced nothing"
    for name, (fn, _desc) in generated.items():
        sig, size, overrides = fn(frame, scored, base)
        sig = pd.Series(sig, index=frame.index).fillna(0.0)
        assert set(np.unique(sig)) <= {-1.0, 0.0, 1.0}, f"{name}: bad signal values"
        assert ((sig != 0) & (base == 0)).sum() == 0, f"{name}: entered outside baseline"
        assert isinstance(overrides, dict), f"{name}: overrides not a dict"


def test_generation_is_deterministic_and_dedups(monkeypatch):
    """Same inputs → same candidate set (reproducible), and a combo already tested
    or already hand-written in REGISTRY is never re-proposed (the critic)."""
    import idea_generator as gen
    a = set(gen.generate_candidates())
    b = set(gen.generate_candidates())
    assert a == b and a, "generation must be deterministic + non-empty"
    # Generated names live in the `gen__` namespace — none collide with a hand-written
    # candidate (a name without the prefix).
    handwritten = {k for k in REGISTRY if not k.startswith("gen__")}
    assert a.isdisjoint(handwritten), "must not collide with hand-written candidates"
    assert all(n.startswith("gen__") for n in a)
    # A name marked as already-tested must drop out of the fresh set.
    victim = next(iter(a))
    monkeypatch.setattr(gen, "_tested_names", lambda: {victim})
    assert victim not in gen.fresh_candidates(), "tested combo must be excluded"


def test_register_generated_makes_names_resolvable():
    """After register_generated, a queued gen__* name resolves in REGISTRY (so the
    harness can actually run it)."""
    import idea_generator as gen
    reg = {k: v for k, v in REGISTRY.items() if not k.startswith("gen__")}
    added = gen.register_generated(reg)
    assert added > 0
    sample = next(n for n in reg if n.startswith("gen__"))
    fn, desc = reg[sample]
    assert callable(fn) and isinstance(desc, str)


def test_every_candidate_returns_valid_triple(frame):
    scored = confluence_score(frame)
    base = confluence_position(frame, min_pct=0.50, trend_align=True)
    for name, (fn, desc) in REGISTRY.items():
        sig, size, overrides = fn(frame, scored, base)
        sig = pd.Series(sig, index=frame.index)
        assert len(sig) == len(frame), f"{name}: signal length mismatch"
        assert set(np.unique(sig.fillna(0.0))) <= {-1.0, 0.0, 1.0}, f"{name}: non {{-1,0,1}} signal"
        # Most candidates are FILTERS (a subset of the baseline entries). Some are
        # STANDALONE signals (e.g. bb_band_reject — a fresh setup tested on its own
        # merits vs the baseline), which legitimately fire outside the baseline.
        _STANDALONE = {"bb_band_reject"}
        nonzero_outside_base = ((sig != 0) & (base == 0)).sum()
        if not overrides and size is None and name not in _STANDALONE:
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
    assert rec["verdict"] in {"WINNER", "SUGGESTIVE", "NEUTRAL", "HURTS", "THIN", "RISK-REDUCER"}
    assert isinstance(rec["delta"], float)
    # risk-adjusted metrics are now part of every record (§22 harness upgrade)
    for k in ("base_sharpe", "cand_sharpe", "sharpe_delta", "cand_maxdd_r", "cand_std"):
        assert k in rec


def test_risk_metrics_helper():
    import numpy as np
    sharpe, std, dd = orx._risk_metrics([1.0, -1.0, 1.0, -1.0, 1.0])
    assert std > 0 and sharpe != 0 and dd <= 0
    assert orx._risk_metrics([])[0] == 0.0


# --- N6: overnight cache must be stamped and REFUSED once stale ------------
# (MEMORY §86/CROSSROADS N6: "stamp/refuse stale overnight caches" — a network
# blip used to fall back to a parquet cache of any age, silently, forever.)

def _tiny_ohlcv(n=40):
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = np.linspace(100, 101, n)
    return pd.DataFrame({"timestamp": ts, "open": close, "high": close + 1,
                         "low": close - 1, "close": close,
                         "volume": np.full(n, 10.0), "quote_volume": np.full(n, 1000.0),
                         "trades": np.full(n, 5)})


def test_fresh_cache_is_used_on_fetch_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(orx, "CACHE", tmp_path)
    monkeypatch.setattr(orx, "UNIVERSE", ["BTCUSDT"])
    cache_file = tmp_path / "binance_BTCUSDT_1h.parquet"
    _tiny_ohlcv().to_parquet(cache_file)   # freshly written -> age ~0h

    def _boom(*a, **kw):
        raise ConnectionError("network blip")

    monkeypatch.setattr(orx, "load_ohlcv", _boom)
    frames = orx._load_frames("1h", 4000)
    assert "BTCUSDT" in frames, "a fresh cache must still be used as a fallback"


def test_stale_cache_is_refused_not_silently_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(orx, "CACHE", tmp_path)
    monkeypatch.setattr(orx, "UNIVERSE", ["BTCUSDT"])
    cache_file = tmp_path / "binance_BTCUSDT_1h.parquet"
    _tiny_ohlcv().to_parquet(cache_file)
    # Backdate the file's mtime past the staleness cutoff.
    stale_ts = time.time() - (orx.MAX_CACHE_AGE_HOURS + 1) * 3600
    import os
    os.utime(cache_file, (stale_ts, stale_ts))

    def _boom(*a, **kw):
        raise ConnectionError("network blip")

    monkeypatch.setattr(orx, "load_ohlcv", _boom)
    frames = orx._load_frames("1h", 4000)
    assert "BTCUSDT" not in frames, "a stale cache must be refused, not silently used"


def test_queue_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(orx, "QUEUE_PATH", tmp_path / "q.json")
    orx.enqueue(["clean_trend", "deeper_retrace"])
    q = orx._queue()
    assert q["pending"] == ["clean_trend", "deeper_retrace"]
    # 'all' should add the rest without duplicating
    orx.enqueue(["all"])
    assert len(q["pending"]) <= len(REGISTRY)
    assert len(set(orx._queue()["pending"])) == len(orx._queue()["pending"])
