"""Tests for the DXY inverse-correlation regime filter + its paper-scan gate."""
import numpy as np
import pandas as pd

from kudbee_quant.signals.dxy_regime import (
    dxy_regime, compute_dxy, RISK_ON, RISK_OFF, NEUTRAL,
)


class _FakeDXY:
    """Returns a 1h OHLCV frame from a close path (or raises / returns empty)."""
    def __init__(self, closes=None, raise_=False, empty=False):
        self.closes = closes
        self.raise_ = raise_
        self.empty = empty

    def klines(self, symbol, interval="1h", limit=1500):
        assert symbol == "yahoo:DX-Y.NYB"      # routes via the yahoo path
        if self.raise_:
            raise RuntimeError("rate limited")
        if self.empty:
            return pd.DataFrame()
        n = len(self.closes)
        ts = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
        c = pd.Series(self.closes, dtype=float)
        return pd.DataFrame({"timestamp": ts, "open": c, "high": c + 0.1,
                             "low": c - 0.1, "close": c, "volume": 1.0})


def test_risk_on_when_below_ema_and_declining():
    # Dollar falling -> last close below EMA, EMA slope negative -> favours longs.
    client = _FakeDXY(np.linspace(110.0, 100.0, 1200))
    assert dxy_regime(client) == RISK_ON


def test_risk_off_when_above_ema_and_rising():
    client = _FakeDXY(np.linspace(100.0, 110.0, 1200))
    assert dxy_regime(client) == RISK_OFF


def test_neutral_when_flat():
    client = _FakeDXY(np.full(1200, 100.0))
    d = compute_dxy(client)
    assert d["state"] == NEUTRAL and d["ok"]
    assert abs(d["pct_diff"]) <= 0.002 + 1e-9


def test_fail_open_on_error():
    d = compute_dxy(_FakeDXY(raise_=True))
    assert d["state"] == NEUTRAL and d["ok"] is False
    assert dxy_regime(_FakeDXY(raise_=True)) == NEUTRAL


def test_fail_open_on_empty():
    assert dxy_regime(_FakeDXY(empty=True)) == NEUTRAL


# --- paper-scan gate ----------------------------------------------------------

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


def test_dxy_gate_blocks_long_in_risk_off(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "dxy_regime", lambda client: RISK_OFF)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), dxy_gate=True)
    assert logged == []          # RISK_OFF blocks the long


def test_dxy_gate_allows_long_in_risk_on_and_tags_book(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "dxy_regime", lambda client: RISK_ON)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), dxy_gate=True)
    assert len(logged) == 1 and logged[0].direction == 1.0
    assert "_dxy" in logged[0].setup    # separately-tagged book


def test_dxy_gate_off_is_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    # Even if the regime would say RISK_OFF, gate OFF must not call/honor it.
    monkeypatch.setattr(pp, "dxy_regime", lambda client: RISK_OFF)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())   # dxy_gate defaults False
    assert len(logged) == 1 and "_dxy" not in logged[0].setup
