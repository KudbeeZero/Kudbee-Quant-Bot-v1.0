"""Tests for the live trade tracker (F2)."""
from types import SimpleNamespace

import kudbee_quant.notifications.trade_tracker as tt
from kudbee_quant.notifications.trade_tracker import build_messages, emit, format_trade_update


def _pred(**kw):
    base = dict(symbol="BTCUSDT", direction=1.0, entry=64000.0, stop=63000.0,
                tp1=65000.0, target=67000.0, target_r=3.0,
                tp1_filled_at=None, be_after_tp1=True, status="open", kind="bracket", id="abc")
    base.update(kw)
    return SimpleNamespace(**base)


def test_format_long_original_stop():
    t = {"unrealized_r": 0.8, "pnl_pct": 1.2, "tp1_touched": False, "time_in_trade_hours": 5}
    out = format_trade_update(_pred(), t)
    assert "📊 TRADE UPDATE — BTCUSDT LONG" in out
    assert "Open since: 5h" in out
    assert "Current P&L: +0.80R  (+1.2%)" in out
    assert "Stop: $63,000  original" in out
    assert "TP1: ⏳ $65,000 (+1.0R)" in out
    assert "TP2: ⏳ $67,000 (+3.0R)" in out


def test_format_breakeven_and_tp1_hit():
    p = _pred(tp1_filled_at="2026-06-30T00:00:00Z")
    out = format_trade_update(p, {"unrealized_r": 1.5, "pnl_pct": 2.0, "time_in_trade_hours": 30})
    assert "🔒 moved to breakeven" in out
    assert "TP1: ✅ hit" in out
    assert "Open since: 1d 6h" in out


def test_format_short():
    out = format_trade_update(_pred(direction=-1.0), {"unrealized_r": None, "time_in_trade_hours": None})
    assert "BTCUSDT SHORT" in out
    assert "Current P&L: n/a" in out
    assert "Open since: —" in out


def test_emit_off_by_default(monkeypatch):
    monkeypatch.setattr(tt, "live_tracker_enabled", lambda: False)
    assert emit() == 0


def test_build_messages_filters_open_only(monkeypatch):
    preds = [_pred(id="a", status="open"), _pred(id="b", status="pending"),
             _pred(id="c", status="hit")]
    journal = SimpleNamespace(predictions=preds)
    monkeypatch.setattr("kudbee_quant.review.open_trades_report",
                        lambda j, c=None: {"trades": [{"id": "a", "unrealized_r": 0.5,
                                                       "pnl_pct": 1.0, "time_in_trade_hours": 2}]})
    msgs = build_messages(journal=journal)
    assert len(msgs) == 1 and "BTCUSDT LONG" in msgs[0]


def test_emit_dry_run_prints(monkeypatch, capsys):
    journal = SimpleNamespace(predictions=[_pred(status="open")])
    monkeypatch.setattr("kudbee_quant.review.open_trades_report",
                        lambda j, c=None: {"trades": [{"id": "abc", "unrealized_r": 0.5,
                                                       "pnl_pct": 1.0, "time_in_trade_hours": 2}]})
    n = emit(journal=journal, force=True, dry_run=True)
    assert n == 1
    assert "TRADE UPDATE" in capsys.readouterr().out
