"""Tests for the weekly performance digest (F6)."""
from datetime import datetime, timezone
from types import SimpleNamespace

import kudbee_quant.notifications.digest as dg
from kudbee_quant.notifications.digest import _quip, emit, format_digest

_NOW = datetime(2026, 6, 30, 20, 0, tzinfo=timezone.utc)


def _journal():
    series = [
        {"t": "2026-06-28T12:00:00+00:00", "r": 2.0, "symbol": "BTCUSDT"},
        {"t": "2026-06-27T12:00:00+00:00", "r": -1.0, "symbol": "ETHUSDT"},
        {"t": "2026-01-01T00:00:00+00:00", "r": 9.0, "symbol": "OLD"},   # outside week
    ]
    preds = [SimpleNamespace(kind="bracket", created_at="2026-06-29T00:00:00+00:00")]
    return SimpleNamespace(resolved_series=lambda: series, predictions=preds)


def test_quip_tiers():
    assert "Outstanding" in _quip(6)
    assert "Solid" in _quip(3)
    assert "Green is green" in _quip(0.5)
    assert "gates held" in _quip(-2)


def test_format_digest(monkeypatch):
    monkeypatch.setattr(dg, "read_skips", lambda *a, **k: [
        {"blocking_gate": "_dxy"}, {"blocking_gate": "_adr"}, {"blocking_gate": "_adr"}])
    out = format_digest(_journal(), now=_NOW)
    assert "WEEKLY PERFORMANCE DIGEST" in out
    assert "Total R:        +1.00R" in out                 # 2.0 - 1.0, OLD excluded
    assert "Win rate:       50%  (1W / 1L)" in out
    assert "Best trade:     BTCUSDT +2.00R" in out
    assert "Worst trade:    ETHUSDT -1.00R" in out
    assert "Signals skipped: 3" in out
    assert "ADR filter: +2.00R" in out                     # 2 ADR skips ~ +2R estimated
    assert "DXY filter: +1.00R" in out
    assert "Green is green" in out                          # total +1.0


def test_emit_off_by_default(monkeypatch):
    monkeypatch.setattr(dg, "weekly_digest_enabled", lambda: False)
    assert emit() is False
