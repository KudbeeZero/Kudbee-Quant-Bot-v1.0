"""Tests for the session-open brief (F3)."""
from types import SimpleNamespace

import kudbee_quant.notifications.session_brief as sb
from kudbee_quant.notifications.session_brief import emit, format_brief


def _journal(open_syms=()):
    preds = [SimpleNamespace(symbol=s, status="open", kind="bracket") for s in open_syms]
    return SimpleNamespace(predictions=preds)


def test_format_brief_london(monkeypatch):
    monkeypatch.setattr(sb, "_dxy_line", lambda c: "RISK_OFF")
    monkeypatch.setattr(sb, "_breaker_line", lambda: "🟢 active")
    monkeypatch.setattr(sb, "read_skips", lambda *a, **k: [
        {"blocking_gate": "_fp"}, {"blocking_gate": "_adr"}, {"blocking_gate": "_adr"},
        {"blocking_gate": "_dxy"}])
    out = format_brief("london", _journal(["BTCUSDT"]))
    assert "🌅 LONDON OPEN BRIEF" in out
    assert "DXY Regime:     RISK_OFF" in out
    assert "Open positions: 1 (BTCUSDT)" in out
    assert "Signals blocked today: 4 (fingerprint: 1, ADR: 2, DXY: 1)" in out
    assert "Good hunting" in out


def test_format_brief_ny_emoji(monkeypatch):
    monkeypatch.setattr(sb, "_dxy_line", lambda c: "NEUTRAL")
    monkeypatch.setattr(sb, "_breaker_line", lambda: "🟢 active")
    monkeypatch.setattr(sb, "read_skips", lambda *a, **k: [])
    out = format_brief("ny", _journal())
    assert "🗽 NY OPEN BRIEF" in out
    assert "Open positions: 0 (none)" in out


def test_emit_off_by_default(monkeypatch):
    monkeypatch.setattr(sb, "session_brief_enabled", lambda: False)
    assert emit("london") is False


def test_emit_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(sb, "_dxy_line", lambda c: "RISK_ON")
    monkeypatch.setattr(sb, "_breaker_line", lambda: "🟢 active")
    monkeypatch.setattr(sb, "read_skips", lambda *a, **k: [])
    assert emit("london", journal=_journal(), force=True, dry_run=True) is True
    assert "LONDON OPEN BRIEF" in capsys.readouterr().out
