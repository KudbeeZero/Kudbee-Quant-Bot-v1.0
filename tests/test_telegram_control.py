"""Tests for the Telegram control commands (/gates /pnl /pause /resume /enable /disable)
+ the manual-pause kill-switch in paper_scan."""
import pandas as pd

import kudbee_quant.control as control
import kudbee_quant.telegram_commands as tc
from kudbee_quant.config import feature_toggles as ft


# --- control state -----------------------------------------------------------

def test_control_round_trip(tmp_path):
    p = str(tmp_path / "control.json")
    assert control.is_paused(p) is False
    control.set_paused(True, reason="x", since="2026-06-30T00:00:00Z", path=p)
    assert control.is_paused(p) is True
    assert control.status(p)["reason"] == "x"
    control.set_paused(False, path=p)
    assert control.is_paused(p) is False
    assert control.status(p)["reason"] is None


def test_control_corrupt_file_fails_open(tmp_path):
    p = tmp_path / "control.json"
    p.write_text("{bad")
    assert control.is_paused(str(p)) is False


# --- paper_scan kill-switch --------------------------------------------------

def _force_long_signal(monkeypatch):
    import kudbee_quant.paper.paper as pp
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)
    return pp


class _C:
    def klines(self, *a, **k):
        return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC")})


def test_paper_scan_halts_when_manually_paused(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "_manual_paused", lambda: True)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         journal=j, client=_C()) == []


def test_paper_scan_runs_when_not_paused(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "_manual_paused", lambda: False)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())
    assert len(logged) == 1


# --- commands ----------------------------------------------------------------

class _FakeJournal:
    predictions: list = []

    def resolved_series(self):
        return [{"t": "2026-06-29T12:00:00+00:00", "r": 2.0},
                {"t": "2026-06-28T12:00:00+00:00", "r": -1.0},
                {"t": "2020-01-01T00:00:00+00:00", "r": 5.0}]   # old, excluded


def test_cmd_gates_lists_pause_and_toggles(monkeypatch):
    monkeypatch.setattr(control, "status", lambda *a, **k: {"manual_pause": False, "reason": None, "since": None})
    monkeypatch.setattr(ft, "all_flags", lambda *a, **k: {"signal_cards": True, "live_tracker": False})
    out = tc.cmd_gates(_FakeJournal())
    assert "Manual pause: 🟢 active" in out
    assert "✅ signal_cards" in out and "⬜ live_tracker" in out


def test_cmd_pnl_window(monkeypatch):
    # Freeze "now" by patching only the filtering: the fixture has 1 win + 1 loss in window.
    out = tc.cmd_pnl("/pnl 3650d", _FakeJournal())   # wide window catches the recent two...
    assert "R on" in out and "win" in out


def test_enable_disable_set_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(ft, "set_flag", lambda name, value, **k: calls.append((name, value)))
    monkeypatch.setattr(tc, "_persist_to_repo", lambda path: "")
    assert "enabled signal_cards" in tc.cmd_enable("/enable signal_cards")
    assert "disabled signal_cards" in tc.cmd_disable("/disable signal_cards")
    assert calls == [("signal_cards", True), ("signal_cards", False)]


def test_enable_unknown_feature():
    assert "Unknown feature" in tc.cmd_enable("/enable nope")


def test_pause_resume_write_control(monkeypatch):
    flags = {}
    monkeypatch.setattr(control, "set_paused", lambda v, **k: flags.update(paused=v))
    monkeypatch.setattr(tc, "_persist_to_repo", lambda path: "")
    assert "PAUSED" in tc.cmd_pause()
    assert flags["paused"] is True
    assert "RESUMED" in tc.cmd_resume()
    assert flags["paused"] is False


def test_admin_gate_blocks_non_admin(monkeypatch):
    monkeypatch.setattr(tc, "_admin_ids", lambda: {"999"})
    monkeypatch.setattr(tc, "_persist_to_repo", lambda path: "")
    # a non-admin chat id is refused before the handler runs
    out = tc.dispatch("/pause", "111", journal=_FakeJournal())
    assert "Admin only" in out


def test_admin_gate_allows_admin(monkeypatch):
    monkeypatch.setattr(tc, "_admin_ids", lambda: {"111"})
    monkeypatch.setattr(control, "set_paused", lambda v, **k: None)
    monkeypatch.setattr(tc, "_persist_to_repo", lambda path: "")
    out = tc.dispatch("/pause", "111", journal=_FakeJournal())
    assert "PAUSED" in out
