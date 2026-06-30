"""Tests for the daily + weekly performance recaps."""
from datetime import datetime, timezone
from types import SimpleNamespace

import kudbee_quant.notifications.recap as rc
from kudbee_quant.notifications.recap import (
    emit_weekly, format_daily_recap, format_weekly_recap,
)

_NOW = datetime(2026, 6, 30, 5, 0, tzinfo=timezone.utc)


def _p(symbol, r, resolved_at, status="hit"):
    return SimpleNamespace(symbol=symbol, status=status, outcome_r=r,
                           resolved_at=resolved_at, created_at=resolved_at)


def _journal():
    preds = [
        _p("DOTUSDT", 3.0, "2026-06-23T10:00:00+00:00"),
        _p("EURUSD", 3.0, "2026-06-24T10:00:00+00:00"),
        _p("AVAXUSDT", -1.0, "2026-06-24T12:00:00+00:00", status="miss"),
        _p("SOLUSDT", 1.5, "2026-06-28T09:00:00+00:00"),
        _p("OLDCOIN", 9.0, "2026-01-01T00:00:00+00:00"),   # outside the 7d window
    ]
    return SimpleNamespace(predictions=preds)


def _net_is_gross(monkeypatch):
    # make net == gross for deterministic assertions
    monkeypatch.setattr("kudbee_quant.journal.net_outcome_r", lambda p: p.outcome_r)


def test_weekly_recap(monkeypatch):
    _net_is_gross(monkeypatch)
    out = format_weekly_recap(_journal(), now=_NOW)
    assert "WEEKLY RECAP" in out
    assert "Net R:      +6.50R" in out          # 3 + 3 - 1 + 1.5 (OLDCOIN excluded)
    assert "Win rate:   75%   (3W / 1L, 4 trades)" in out
    assert "Avg/trade:  +1.62R" in out
    assert "By day:" in out
    assert "06-24" in out                         # multi-trade day present
    assert "🏆 Top:" in out and "DOTUSDT +3.0R" in out
    assert "🔻 Worst: AVAXUSDT -1.0R" in out
    assert "Best symbol:" in out
    assert "7d sample — not a validated edge" in out


def test_weekly_recap_empty(monkeypatch):
    _net_is_gross(monkeypatch)
    out = format_weekly_recap(SimpleNamespace(predictions=[]), now=_NOW)
    assert "Net R:      +0.00R" in out
    assert "0 trades" in out


def test_daily_recap(monkeypatch):
    _net_is_gross(monkeypatch)
    # yesterday = 2026-06-29; add a trade there
    j = SimpleNamespace(predictions=[
        _p("BTCUSDT", 2.0, "2026-06-29T14:00:00+00:00"),
        _p("ETHUSDT", -1.0, "2026-06-29T16:00:00+00:00", status="miss"),
        _p("SOLUSDT", 1.0, "2026-06-25T10:00:00+00:00"),     # in 7d window, not yesterday
    ])
    out = format_daily_recap(j, now=_NOW)
    assert "DAILY RECAP — 2026-06-29" in out
    assert "Yesterday: +1.00R  (1W/1L, 2 trades)" in out
    assert "Rolling 7d: +2.00R" in out
    assert "🏆 Top: BTCUSDT +2.0R" in out


def test_emit_off_by_default(monkeypatch):
    monkeypatch.setattr(rc, "_enabled", lambda flag: False)
    assert emit_weekly() is False


def test_emit_dry_run(monkeypatch, capsys):
    _net_is_gross(monkeypatch)
    assert emit_weekly(journal=_journal(), force=True, dry_run=True) is True
    assert "WEEKLY RECAP" in capsys.readouterr().out


def test_recap_command(monkeypatch):
    _net_is_gross(monkeypatch)
    import kudbee_quant.telegram_commands as tc
    out = tc.cmd_recap("/recap", _journal())
    assert "WEEKLY RECAP" in out
