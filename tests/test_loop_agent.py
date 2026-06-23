"""Tests for L7 — the self-improving loop agent (kudbee_quant/memory/loop_agent.py).

Offline + synthetic: builds a journal of resolved paper trades on a temp path, runs
loop-agent cycles against a temp ledger, and asserts the OBSERVE→GRADE→DETECT→PERSIST
loop (including the self-calibration) behaves. Non-bracket ('touch') trades carry a
zero fee, so net == gross and the expectancy math is exact.
"""
from __future__ import annotations

import json

from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.memory.loop_agent import LoopAgent, format_cycle


def _journal(tmp_path, trades, name="journal.json"):
    """trades = list of (setup, outcome_r). Writes a journal file, returns its path."""
    p = tmp_path / name
    j = TradeJournal(path=p)
    for i, (setup, r) in enumerate(trades):
        j.predictions.append(Prediction(
            symbol="BTCUSDT", kind="touch", level=100.0, deadline_days=1.0,
            setup=setup, timeframe="1h", status=("hit" if r > 0 else "miss"),
            outcome_r=float(r), resolved_at=f"2026-06-{(i % 27) + 1:02d}T00:00:00+00:00",
            mode="paper", source="bot"))
    j.save()
    return p


def _agent(journal_path, state_path):
    return LoopAgent(journal=TradeJournal(path=journal_path), state_path=state_path)


def test_negative_book_proposes_revert(tmp_path):
    jp = _journal(tmp_path, [("core", -1.0)] * 30)
    sp = tmp_path / "loop.json"
    cycle = _agent(jp, sp).run_cycle()
    revert = [p for p in cycle["proposals"] if p["type"] == "book_negative"]
    assert len(revert) == 1
    assert revert[0]["severity"] == "act"
    assert revert[0]["book"] == "core"
    assert revert[0]["reliability"] is None          # nothing graded yet
    assert sp.exists()                                # ledger persisted


def test_healthy_book_first_cycle_has_no_proposals(tmp_path):
    jp = _journal(tmp_path, [("core", 1.0)] * 30)     # all winners -> KEEP
    sp = tmp_path / "loop.json"
    cycle = _agent(jp, sp).run_cycle()
    assert cycle["proposals"] == []
    assert "No drift" in format_cycle(cycle)


def test_grading_vindicated_updates_calibration(tmp_path):
    sp = tmp_path / "loop.json"
    jp = _journal(tmp_path, [("core", -1.0)] * 30)
    _agent(jp, sp).run_cycle()                         # cycle 1: REVERT proposal
    # more losers arrive -> book still bleeds, n grows
    jp = _journal(tmp_path, [("core", -1.0)] * 35)
    cycle2 = _agent(jp, sp).run_cycle()               # cycle 2: grades cycle 1
    graded = {g["key"]: g for g in cycle2["graded"]}
    assert graded["book_negative::core"]["verdict"] == "vindicated"
    state = json.loads(sp.read_text())
    assert state["calibration"]["book_negative"] == {"vindicated": 1, "false_alarm": 0}
    # the freshly re-emitted proposal now carries the learned reliability
    revert = [p for p in cycle2["proposals"] if p["type"] == "book_negative"][0]
    assert revert["reliability"] == 1.0


def test_grading_false_alarm_on_recovery(tmp_path):
    sp = tmp_path / "loop.json"
    jp = _journal(tmp_path, [("core", -1.0)] * 30)
    _agent(jp, sp).run_cycle()                         # cycle 1: REVERT (net -1.0)
    # a flood of winners flips the book net-positive
    jp = _journal(tmp_path, [("core", -1.0)] * 30 + [("core", 5.0)] * 40)
    cycle2 = _agent(jp, sp).run_cycle()
    graded = {g["key"]: g for g in cycle2["graded"]}
    assert graded["book_negative::core"]["verdict"] == "false_alarm"
    state = json.loads(sp.read_text())
    assert state["calibration"]["book_negative"] == {"vindicated": 0, "false_alarm": 1}


def test_pending_when_no_new_trades(tmp_path):
    sp = tmp_path / "loop.json"
    jp = _journal(tmp_path, [("core", -1.0)] * 30)
    _agent(jp, sp).run_cycle()
    cycle2 = _agent(jp, sp).run_cycle()               # identical journal -> nothing to judge
    graded = {g["key"]: g for g in cycle2["graded"]}
    assert graded["book_negative::core"]["verdict"] == "pending"
    state = json.loads(sp.read_text())
    assert "book_negative" not in state["calibration"]   # pending never calibrates


def test_decay_detected_on_slipping_book(tmp_path):
    sp = tmp_path / "loop.json"
    jp = _journal(tmp_path, [("core", 0.30)] * 30)    # KEEP at +0.30R/t
    _agent(jp, sp).run_cycle()
    # add losers: expectancy drops well past DECAY_DROP but stays positive (still KEEP)
    jp = _journal(tmp_path, [("core", 0.30)] * 30 + [("core", -0.50)] * 10)
    cycle2 = _agent(jp, sp).run_cycle()
    decay = [p for p in cycle2["proposals"] if p["type"] == "book_decay"]
    assert len(decay) == 1
    assert decay[0]["book"] == "core" and decay[0]["severity"] == "watch"


def test_dry_run_does_not_persist(tmp_path):
    jp = _journal(tmp_path, [("core", -1.0)] * 30)
    sp = tmp_path / "loop.json"
    _agent(jp, sp).run_cycle(persist=False)
    assert not sp.exists()


def test_injected_regime_shift_and_overfit(tmp_path):
    sp = tmp_path / "loop.json"
    jp = _journal(tmp_path, [("core", 1.0)] * 30)
    # cycle 1 carries a regime; cycle 2 a different one -> regime_shift fires
    _agent(jp, sp).run_cycle(regime={"trend": "up", "vol_regime": "low"})
    cycle2 = _agent(jp, sp).run_cycle(
        regime={"trend": "down", "vol_regime": "low"},
        overfit={"n_candidates": 60, "naive_winners": 3, "fdr_survivors": 0})
    types = {p["type"] for p in cycle2["proposals"]}
    assert "regime_shift" in types
    assert "overfit" in types


def test_multiple_books_tracked_independently(tmp_path):
    jp = _journal(tmp_path, [("core", 1.0)] * 30 + [("strat_cts", -1.0)] * 30)
    sp = tmp_path / "loop.json"
    cycle = _agent(jp, sp).run_cycle()
    books = {p["book"] for p in cycle["proposals"]}
    assert "trend(_cts)" in books          # the losing _cts book is flagged
    assert "core" not in books             # the healthy core book is not
