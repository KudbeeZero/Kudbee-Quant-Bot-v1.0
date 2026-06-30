"""Tests for the circuit-breaker alert (trip/reset) + the DrawdownGuard callback."""
from types import SimpleNamespace

import kudbee_quant.notifications.circuit_alert as ca
from kudbee_quant.notifications.circuit_alert import notify_state_change
from kudbee_quant.risk.drawdown_guard import DrawdownGuard


def _closed(r, i=0):
    ts = f"2026-01-{1 + i:02d}T00:00:00+00:00"
    return SimpleNamespace(status="hit", outcome_r=r, resolved_at=ts, created_at=ts)


def _guard(rolling_r=-5.0):
    return SimpleNamespace(window=5, rolling_r=rolling_r, pause_threshold_r=-3.0,
                           resume_threshold_r=-1.0)


# --- message content ---------------------------------------------------------

def test_trip_message(monkeypatch):
    sent = {}
    monkeypatch.setattr(ca, "send_telegram", lambda t, **k: sent.update(text=t, kw=k) or True)
    assert notify_state_change("active", "paused", _guard()) is True
    assert "CIRCUIT BREAKER TRIPPED" in sent["text"]
    assert "PAUSED" in sent["text"] and "-5.00R" in sent["text"]
    assert sent["kw"].get("parse_mode") == "HTML"


def test_reset_message(monkeypatch):
    sent = {}
    monkeypatch.setattr(ca, "send_telegram", lambda t, **k: sent.update(text=t) or True)
    assert notify_state_change("paused", "active", _guard(rolling_r=0.0)) is True
    assert "CIRCUIT BREAKER RESET" in sent["text"] and "ACTIVE" in sent["text"]


def test_unknown_state_noops(monkeypatch):
    monkeypatch.setattr(ca, "send_telegram", lambda *a, **k: True)
    assert notify_state_change("active", "weird", _guard()) is False


def test_send_failure_is_swallowed(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(ca, "send_telegram", _boom)
    assert notify_state_change("active", "paused", _guard()) is False   # never raises


# --- DrawdownGuard fires the callback exactly on a flip ----------------------

def test_guard_fires_callback_on_trip_and_reset(tmp_path):
    events = []
    g = DrawdownGuard(window=5, pause_threshold_r=-3.0, resume_threshold_r=-1.0,
                      state_path=str(tmp_path / "dd.json"))

    def cb(old, new, guard):
        events.append((old, new))
    # 5 × -1R -> rolling -5 -> trips paused
    g.update([_closed(-1.0, i) for i in range(5)], on_state_change=cb)
    assert events[-1] == ("active", "paused")
    # recover to 0 -> resets active
    g.update([_closed(0.0, i) for i in range(5)], on_state_change=cb)
    assert events[-1] == ("paused", "active")


def test_guard_no_callback_when_state_unchanged(tmp_path):
    events = []
    g = DrawdownGuard(window=5, state_path=str(tmp_path / "dd.json"))
    g.update([_closed(0.0, i) for i in range(5)],
             on_state_change=lambda *a: events.append(a))
    assert events == []        # stayed active -> no flip -> no callback
