"""Tests for the 6-layer memory spine (kudbee_quant/memory/). Offline + synthetic."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kudbee_quant.levels import build_levels
from kudbee_quant.memory.registry import StrategyRegistry
from kudbee_quant.memory.reflection import failure_rollup, overfit_alarms, regime_state
from kudbee_quant.memory.testing_ledger import family_ledger
from kudbee_quant.memory.working import WorkingMemory


def _results_file(tmp_path):
    # a small synthetic experiment log: one clear winner, one clear loser, noise
    recs = [
        {"name": "vol_winner", "verdict": "WINNER", "delta": 0.12, "n_trades": 800,
         "base_n": 1500, "cand_exp": 0.28, "base_exp": 0.16, "cand_win": 0.42, "base_win": 0.38,
         "h1_delta": 0.10, "h2_delta": 0.13},
        {"name": "trend_loser", "verdict": "HURTS", "delta": -0.09, "n_trades": 700,
         "base_n": 1500, "cand_exp": 0.07, "base_exp": 0.16, "cand_win": 0.34, "base_win": 0.38,
         "h1_delta": -0.08, "h2_delta": -0.10},
        {"name": "volume_thin", "verdict": "THIN", "delta": 0.02, "n_trades": 40,
         "base_n": 1500, "cand_exp": 0.18, "base_exp": 0.16, "cand_win": 0.40, "base_win": 0.38,
         "h1_delta": 0.05, "h2_delta": -0.01},
    ]
    p = tmp_path / "overnight_results.json"
    p.write_text(json.dumps({"runs": [], "results": recs}))
    return p


def _frame():
    n = 900
    rng = np.random.default_rng(1)
    close = 100 * np.exp(rng.normal(0.001, 0.01, n).cumsum())   # uptrend
    high = close * 1.003
    low = close * 0.997
    op = np.concatenate([[close[0]], close[:-1]])
    vol = rng.lognormal(10, 0.4, n)
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return build_levels(pd.DataFrame({"timestamp": ts, "open": op, "high": high, "low": low,
                                      "close": close, "volume": vol, "quote_volume": vol * close,
                                      "trades": (vol / 10).astype(int)}))


def test_family_ledger_grades_winners(tmp_path):
    p = _results_file(tmp_path)
    led = family_ledger(p)
    assert led["summary"]["n_candidates"] == 3
    assert led["summary"]["naive_winners"] == 1
    # the strong, high-n winner should have the smallest p-value
    assert led["rows"][0]["name"] == "vol_winner"


def test_overfit_and_failure_rollup(tmp_path):
    p = _results_file(tmp_path)
    led = family_ledger(p)
    alarms = overfit_alarms(led, results_path=p)
    assert alarms["n_candidates"] == 3 and alarms["naive_winners"] == 1
    roll = failure_rollup(results_path=p)
    assert roll["trend/regime"]["failed"] >= 1   # trend_loser counted as failed


def test_regime_state_detects_trend():
    r = regime_state(_frame())
    assert r["trend"] in {"up", "down", "flat"}
    assert r["vol_regime"] in {"low", "mid", "high"}
    assert isinstance(r["choppy"], bool)


def test_registry_seeds_baseline_and_candidates():
    reg = StrategyRegistry()
    assert reg.get("confluence_r_baseline").kind == "baseline"
    assert len(reg.strategies) > 5     # baseline + many candidates


def test_working_memory_snapshot(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"pending": ["a", "b"], "done": ["c"]}))
    wm = WorkingMemory(biases_path=tmp_path / "biases.json", queue_path=q)
    snap = wm.snapshot()
    assert snap["n_pending"] == 2 and snap["n_done"] == 1
    assert isinstance(snap["active_biases"], list)
