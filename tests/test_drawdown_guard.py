"""Tests for the drawdown circuit breaker + its paper-scan gate ('_dcb')."""
from types import SimpleNamespace

import pandas as pd

from kudbee_quant.risk.drawdown_guard import DrawdownGuard


def _closed(r, i=0, status="hit"):
    ts = f"2026-01-{1 + i:02d}T00:00:00+00:00"
    return SimpleNamespace(status=status, outcome_r=r, resolved_at=ts, created_at=ts)


def test_thin_history_stays_active(tmp_path):
    g = DrawdownGuard(window=10, state_path=str(tmp_path / "dd.json"))
    g.update([_closed(-1.0, i) for i in range(3)])     # only 3 closed < window
    assert g.rolling_r is None
    assert g.is_paused is False


def test_trips_when_rolling_below_threshold(tmp_path):
    g = DrawdownGuard(window=5, pause_threshold_r=-3.0, resume_threshold_r=-1.0,
                      state_path=str(tmp_path / "dd.json"))
    g.update([_closed(-1.0, i) for i in range(5)])     # rolling = -5.0 < -3.0
    assert g.rolling_r == -5.0
    assert g.is_paused is True


def test_does_not_trip_above_threshold(tmp_path):
    g = DrawdownGuard(window=5, pause_threshold_r=-3.0,
                      state_path=str(tmp_path / "dd.json"))
    preds = [_closed(-1.0, 0), _closed(-1.0, 1), _closed(1.0, 2), _closed(1.0, 3), _closed(-1.0, 4)]
    g.update(preds)                                    # rolling = -1.0 > -3.0
    assert g.is_paused is False


def test_resume_hysteresis(tmp_path):
    state = str(tmp_path / "dd.json")
    g = DrawdownGuard(window=5, pause_threshold_r=-3.0, resume_threshold_r=-1.0,
                      state_path=state)
    g.update([_closed(-1.0, i) for i in range(5)])     # rolling -5 -> paused
    assert g.is_paused is True
    # recovers to -2.0 (above pause, but still below resume -1.0) -> STAY paused
    g.update([_closed(-2.0, 0), _closed(0.0, 1), _closed(0.0, 2), _closed(0.0, 3), _closed(0.0, 4)])
    assert g.rolling_r == -2.0 and g.is_paused is True
    # recovers to 0.0 (>= resume -1.0) -> resume
    g.update([_closed(0.0, i) for i in range(5)])
    assert g.is_paused is False


def test_state_persists_across_instances(tmp_path):
    state = str(tmp_path / "dd.json")
    g1 = DrawdownGuard(window=5, state_path=state)
    g1.update([_closed(-1.0, i) for i in range(5)])
    assert g1.is_paused is True
    g2 = DrawdownGuard(window=5, state_path=state)     # fresh instance, same file
    assert g2.is_paused is True                        # loaded the paused flag
    # the DEFAULT state file is isolated from the bot-owned journal
    assert DrawdownGuard().state_path.name == "drawdown_state.json"
    assert "journal" not in str(DrawdownGuard().state_path)


# --- paper_scan wiring -------------------------------------------------------

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


class _FakeGuard:
    paused = False

    def __init__(self, *a, **k):
        self.is_paused = _FakeGuard.paused

    def update(self, predictions, persist=True):
        return self.is_paused

    def status_message(self):
        return "fake guard"


def test_paper_scan_paused_returns_empty(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.paused = True
    monkeypatch.setattr(pp, "DrawdownGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), drawdown_circuit_breaker=True)
    assert logged == []


def test_paper_scan_active_proceeds_and_tags(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.paused = False
    monkeypatch.setattr(pp, "DrawdownGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), drawdown_circuit_breaker=True)
    assert len(logged) == 1 and "_dcb" in logged[0].setup


def test_paper_scan_gate_off_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.paused = True       # would pause if consulted
    monkeypatch.setattr(pp, "DrawdownGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())     # breaker defaults off
    assert len(logged) == 1 and "_dcb" not in logged[0].setup
