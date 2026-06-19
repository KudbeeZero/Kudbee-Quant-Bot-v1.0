"""Tests for the losing-cluster analyzer (offline, read-only over the journal)."""
import json
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd

from kudbee_quant.cluster import losing_cluster_report, render_cluster_text
from kudbee_quant.events.study import StudyConfig, conditional_table
from kudbee_quant.journal import Prediction


def _trade(hour, outcome_r, *, setup="confluence_r_50pct_tf", tf="1h",
           direction=1.0, entry=100.0, stop=99.0):
    """A resolved bracket trade created at a fixed UTC hour with a set R."""
    created = datetime(2026, 6, 1, hour, 0, tzinfo=timezone.utc).isoformat()
    return Prediction(
        symbol="BTCUSDT", kind="bracket", level=entry, deadline_days=7,
        setup=setup, timeframe=tf, created_at=created,
        status="hit" if outcome_r > 0 else "miss", resolved_at=created,
        entry=entry, stop=stop, target=103.0, direction=direction,
        target_r=3.0, outcome_r=outcome_r)


def _write(tmp_path, preds):
    p = tmp_path / "journal.json"
    p.write_text(json.dumps([asdict(x) for x in preds], indent=2))
    return p


# --- harness extension: null_rate is backward-compatible --------------------

def test_conditional_table_null_rate_default_unchanged():
    df = pd.DataFrame({"b": ["x"] * 40, "win": [True] * 20 + [False] * 20})
    default = conditional_table(df, "win", ["b"], StudyConfig(min_n=10))
    explicit = conditional_table(df, "win", ["b"], StudyConfig(min_n=10, null_rate=0.5))
    assert default.loc[0, "p_value"] == explicit.loc[0, "p_value"]
    # 50% wins is right at a 0.5 null (p≈1) but far from a 0.2 null (small p).
    far = conditional_table(df, "win", ["b"], StudyConfig(min_n=10, null_rate=0.2))
    assert far.loc[0, "p_value"] < default.loc[0, "p_value"]


# --- analyzer ---------------------------------------------------------------

def test_flags_an_engineered_losing_cluster(tmp_path):
    # Hour 2 (Asia block) always loses; the rest win ~30% — a real cluster.
    preds = [_trade(2, -1.0) for _ in range(40)]
    for h in (9, 10, 14, 15, 19, 20):
        preds += [_trade(h, 3.0) for _ in range(9)]      # ~30% winners...
        preds += [_trade(h, -1.0) for _ in range(21)]    # ...the rest lose
    rep = losing_cluster_report(_write(tmp_path, preds), min_n=20)
    sessions = {c["bucket"] for c in rep["losing_clusters"] if c["dimension"] == "session"}
    assert "00-06 Asia" in sessions
    # The text report should reach the "losses concentrate" verdict.
    assert "losing cluster" in render_cluster_text(rep)


def test_uniform_book_flags_nothing(tmp_path):
    # Every hour shares the same 20% win rate → no bucket differs from baseline.
    preds = []
    for h in (1, 7, 13, 19):
        preds += [_trade(h, 3.0) for _ in range(8)]
        preds += [_trade(h, -1.0) for _ in range(32)]
    rep = losing_cluster_report(_write(tmp_path, preds), min_n=20)
    assert rep["losing_clusters"] == []
    assert "variance" in render_cluster_text(rep)


def test_read_only_does_not_touch_journal(tmp_path):
    path = _write(tmp_path, [_trade(2, -1.0) for _ in range(25)])
    before = path.read_bytes()
    losing_cluster_report(path, min_n=20)
    assert path.read_bytes() == before


def test_empty_journal_is_honest(tmp_path):
    rep = losing_cluster_report(tmp_path / "missing.json")
    assert rep["overall"]["n"] == 0
    assert "No resolved" in render_cluster_text(rep)


def test_mode_filter(tmp_path):
    preds = [_trade(2, -1.0) for _ in range(25)]
    for p in preds[:10]:
        p.mode = "live"
    path = _write(tmp_path, preds)
    assert losing_cluster_report(path, mode="live")["overall"]["n"] == 10
    assert losing_cluster_report(path, mode="paper")["overall"]["n"] == 15
