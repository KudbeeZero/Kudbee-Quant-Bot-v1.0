"""Tests for the read-only Telegram event + delta layer (notifications.events).

These exercise the PURE core (snapshot / diff_events / delta_summary /
format_event) over hand-built report dicts, plus state round-trip and the
format_summary header integration. Nothing here touches the trading path.
"""
from __future__ import annotations

from kudbee_quant.notifications import events as ev
from kudbee_quant.notifications.notify import format_summary


def _report(trades):
    """Minimal open_trades_report-shaped dict from a list of trade dicts."""
    winners = sum(1 for t in trades if (t.get("unrealized_r") or 0) > 0)
    losers = sum(1 for t in trades if (t.get("unrealized_r") or 0) < 0)
    total_r = sum(t.get("unrealized_r") or 0 for t in trades)
    return {
        "trades": trades,
        "portfolio": {
            "total_open": len(trades),
            "winners_open": winners,
            "losers_open": losers,
            "total_unrealized_r": round(total_r, 4),
            "total_open_risk_pct": 1.0 * len(trades),
        },
    }


def _t(tid, symbol, ur, health="healthy", tp1_filled=False, stop_touched=False,
       status="open", tp1_touched=False, hours_to_deadline=None):
    return {"id": tid, "symbol": symbol, "unrealized_r": ur, "health": health,
            "tp1": 1.0, "tp1_touched": tp1_touched, "tp1_filled": tp1_filled,
            "tp2_touched": False, "stop_touched": stop_touched,
            "hours_to_deadline": hours_to_deadline, "status": status}


# --- snapshot ----------------------------------------------------------------

def test_snapshot_reduces_report():
    snap = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5, health="winning")]))
    assert set(snap) == {"trades", "agg"}
    assert snap["trades"]["a"] == {
        "symbol": "BTCUSDT", "ur": 0.5, "health": "winning",
        "tp1_touched": False, "tp1_filled": False, "stop_touched": False,
        "dl_soon": False, "status": "open",
    }
    assert snap["agg"]["n"] == 1 and snap["agg"]["winners"] == 1


def test_snapshot_skips_trades_without_id():
    snap = ev.snapshot({"trades": [{"symbol": "X", "unrealized_r": 1.0}],
                        "portfolio": {}})
    assert snap["trades"] == {}


# --- diff_events: each transition --------------------------------------------

def test_no_prev_yields_no_events():
    curr = ev.snapshot(_report([_t("a", "BTCUSDT", -0.2, health="near stop")]))
    assert ev.diff_events(None, curr) == []


def test_approaching_stop_fires_on_health_into_trouble():
    prev = ev.snapshot(_report([_t("a", "ADAUSDT", -0.2, health="warning?")]))
    curr = ev.snapshot(_report([_t("a", "ADAUSDT", -0.6, health="near stop")]))
    evs = ev.diff_events(prev, curr)
    assert [e["type"] for e in evs] == ["approaching_stop"]
    assert evs[0]["symbol"] == "ADAUSDT"


def test_warning_cleared_fires_on_recovery_of_health():
    prev = ev.snapshot(_report([_t("a", "ADAUSDT", -0.6, health="near stop")]))
    curr = ev.snapshot(_report([_t("a", "ADAUSDT", -0.1, health="healthy")]))
    types = {e["type"] for e in ev.diff_events(prev, curr)}
    assert "warning_cleared" in types


def test_recovered_fires_on_red_to_green():
    prev = ev.snapshot(_report([_t("a", "SOLUSDT", -0.3)]))
    curr = ev.snapshot(_report([_t("a", "SOLUSDT", 0.2)]))
    types = {e["type"] for e in ev.diff_events(prev, curr)}
    assert "recovered" in types


def test_flipped_red_fires_on_green_to_red():
    prev = ev.snapshot(_report([_t("a", "SOLUSDT", 0.4)]))
    curr = ev.snapshot(_report([_t("a", "SOLUSDT", -0.2)]))
    evs = ev.diff_events(prev, curr)
    assert [e["type"] for e in evs] == ["flipped_red"]
    assert evs[0]["r"] == -0.2


def test_tp1_banked_fires_once_on_latch():
    prev = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5, tp1_filled=False)]))
    curr = ev.snapshot(_report([_t("a", "BTCUSDT", 0.6, tp1_filled=True)]))
    assert "tp1_banked" in {e["type"] for e in ev.diff_events(prev, curr)}
    # Already banked → no re-fire.
    again = ev.snapshot(_report([_t("a", "BTCUSDT", 0.7, tp1_filled=True)]))
    assert "tp1_banked" not in {e["type"] for e in ev.diff_events(curr, again)}


def test_tp1_touched_fires_when_reached_not_banked():
    prev = ev.snapshot(_report([_t("a", "DOTUSDT", 0.8, tp1_touched=False)]))
    curr = ev.snapshot(_report([_t("a", "DOTUSDT", 1.0, tp1_touched=True,
                                   tp1_filled=False)]))
    types = {e["type"] for e in ev.diff_events(prev, curr)}
    assert "tp1_touched" in types and "tp1_banked" not in types


def test_tp1_touched_suppressed_once_banked():
    # Touched and banked in the same read → only the banked ping, not 'touched'.
    prev = ev.snapshot(_report([_t("a", "DOTUSDT", 0.8)]))
    curr = ev.snapshot(_report([_t("a", "DOTUSDT", 1.0, tp1_touched=True,
                                   tp1_filled=True)]))
    types = {e["type"] for e in ev.diff_events(prev, curr)}
    assert "tp1_banked" in types and "tp1_touched" not in types


def test_deadline_soon_fires_on_entering_window():
    prev = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=9.0)]))
    curr = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=5.0)]))
    assert "deadline_soon" in {e["type"] for e in ev.diff_events(prev, curr)}


def test_deadline_soon_does_not_refire_while_in_window():
    prev = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=5.0)]))
    curr = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=3.0)]))
    assert "deadline_soon" not in {e["type"] for e in ev.diff_events(prev, curr)}


def test_deadline_soon_not_fired_when_overdue():
    # Already overdue (h<=0) is not "soon" — the summary's overdue line owns that.
    prev = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=9.0)]))
    curr = ev.snapshot(_report([_t("a", "XRPUSDT", 0.2, hours_to_deadline=-1.0)]))
    assert "deadline_soon" not in {e["type"] for e in ev.diff_events(prev, curr)}


def test_no_event_when_unchanged():
    snap = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5, health="winning")]))
    assert ev.diff_events(snap, snap) == []


def test_new_trade_ignored_by_diff():
    prev = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5)]))
    curr = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5), _t("b", "ETHUSDT", -0.4)]))
    # 'b' is new (open-event ping covers it) → no intra-trade event for it.
    assert ev.diff_events(prev, curr) == []


def test_unmarked_marks_do_not_flip():
    # pending → marked should not count as recovered/flipped (no prior mark).
    prev = ev.snapshot(_report([_t("a", "BTCUSDT", None, status="pending")]))
    curr = ev.snapshot(_report([_t("a", "BTCUSDT", -0.3)]))
    assert all(e["type"] not in ("recovered", "flipped_red")
               for e in ev.diff_events(prev, curr))


# --- delta_summary -----------------------------------------------------------

def test_delta_summary_none_prev_is_empty():
    curr = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5)]))
    assert ev.delta_summary(None, curr) == ""


def test_delta_summary_no_change_is_empty():
    snap = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5, health="winning")]))
    assert ev.delta_summary(snap, snap) == ""


def test_delta_summary_reports_recovered_and_r_move():
    prev = ev.snapshot(_report([_t("a", "SOLUSDT", -0.3)]))
    curr = ev.snapshot(_report([_t("a", "SOLUSDT", 0.5)]))
    line = ev.delta_summary(prev, curr)
    assert line.startswith("📊 Since last read:")
    assert "1 recovered" in line
    assert "+0.80R" in line


def test_delta_summary_counts_warnings():
    prev = ev.snapshot(_report([_t("a", "ADAUSDT", -0.2, health="healthy")]))
    curr = ev.snapshot(_report([_t("a", "ADAUSDT", -0.6, health="near stop")]))
    assert "1 warning" in ev.delta_summary(prev, curr)


# --- format_event ------------------------------------------------------------

def test_format_event_renders_icon_label_r_detail():
    msg = ev.format_event({"type": "approaching_stop", "symbol": "ADAUSDT",
                           "r": -0.6, "detail": "Drifting toward stop. Watching."})
    assert "⚠️ ADAUSDT — Stop Approaching" in msg
    assert "-0.60R" in msg
    assert "Watching." in msg


def test_format_event_unmarked_r_is_dash():
    msg = ev.format_event({"type": "recovered", "symbol": "X", "r": None})
    assert "—" in msg


# --- state persistence -------------------------------------------------------

def test_state_round_trip(tmp_path):
    path = str(tmp_path / "notify_state.json")
    assert ev.load_state(path) is None          # missing → None
    snap = ev.snapshot(_report([_t("a", "BTCUSDT", 0.5)]))
    assert ev.save_state(snap, path) is True
    assert ev.load_state(path) == snap


def test_load_state_bad_file_is_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json{", encoding="utf-8")
    assert ev.load_state(str(path)) is None


# --- format_summary integration ----------------------------------------------

def test_format_summary_prepends_delta_line():
    report = _report([_t("a", "BTCUSDT", 0.5, health="winning")])
    out = format_summary(report, delta_line="📊 Since last read: 1 recovered")
    lines = out.splitlines()
    assert lines[0] == "⬡ KUDBEE QUANT — Live Read"
    assert lines[1] == "📊 Since last read: 1 recovered"


def test_format_summary_no_delta_line_unchanged_shape():
    report = _report([_t("a", "BTCUSDT", 0.5, health="winning")])
    out = format_summary(report)
    lines = out.splitlines()
    assert lines[0] == "⬡ KUDBEE QUANT — Live Read"
    assert lines[1].startswith("◇ 1 open")


# --- notify_summary gating (the spam-prevention invariant) -------------------

def _wire_notify_summary(monkeypatch, report):
    """Stub the heavy deps so notify_summary runs without disk/network, and
    return (sent_messages, saved_flag). load/save_state are patched so no test
    ever writes the real data/notify_state.json."""
    import kudbee_quant.journal as journal_mod
    import kudbee_quant.review as review_mod
    import kudbee_quant.scorecard as sc_mod
    import kudbee_quant.notifications.heartbeat as hb_mod
    import kudbee_quant.notifications.notify as notify_mod
    from kudbee_quant.notifications import events as ev_mod

    class _DummyJournal:
        predictions: list = []
        def venue_record(self):
            return {}

    sent: list[str] = []
    saved: list[bool] = []
    # prev: same trade was RED last read → green now ⇒ a 'recovered' event.
    prev = ev_mod.snapshot(_report([_t("a", "SOLUSDT", -0.4)]))

    monkeypatch.setattr(notify_mod, "telegram_enabled", lambda: True)
    monkeypatch.setattr(notify_mod, "send_telegram", lambda msg: sent.append(msg) or True)
    monkeypatch.setattr(journal_mod, "TradeJournal", _DummyJournal)
    monkeypatch.setattr(review_mod, "open_trades_report", lambda journal=None: report)
    monkeypatch.setattr(sc_mod, "today_autopsy", lambda j: {})
    monkeypatch.setattr(hb_mod, "load_health", lambda: {})
    monkeypatch.setattr(ev_mod, "load_state", lambda path=None: prev)
    monkeypatch.setattr(ev_mod, "save_state", lambda snap, path=None: saved.append(True) or True)
    return sent, saved


def test_hourly_read_fires_events_and_saves(monkeypatch):
    from kudbee_quant.notifications.notify import notify_summary
    report = _report([_t("a", "SOLUSDT", 0.3)])    # now green (was red)
    sent, saved = _wire_notify_summary(monkeypatch, report)
    assert notify_summary(only_if_open=False) is True
    assert saved == [True]                         # snapshot persisted
    assert any("Recovered" in m for m in sent)     # intra-trade event pinged
    assert any("Since last read" in m for m in sent)  # delta header on the read


def test_five_min_reminder_does_not_fire_events_or_save(monkeypatch):
    from kudbee_quant.notifications.notify import notify_summary
    report = _report([_t("a", "SOLUSDT", 0.3)])    # same recovery scenario
    sent, saved = _wire_notify_summary(monkeypatch, report)
    assert notify_summary(only_if_open=True) is True
    assert saved == []                             # read-only path saves nothing
    assert not any("Recovered" in m for m in sent)  # no event spam every 5 min
    assert not any("Since last read" in m for m in sent)


# --- demo script smoke test --------------------------------------------------

def test_demo_script_renders_expected_events():
    """scripts/demo_event_layer.py replays a bouncing book; lock that it actually
    produces the event vocabulary + delta header (so the 'show me a result' demo
    can't silently rot)."""
    import importlib.util
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "scripts", "demo_event_layer.py")
    spec = importlib.util.spec_from_file_location("demo_event_layer", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.render()
    assert "Stop Approaching" in out
    assert "Slipped to Loss" in out
    assert "Recovered to Profit" in out
    assert "Warning Cleared" in out
    assert "📊 Since last read:" in out
    assert "all in profit" in out          # the final read lands clean
