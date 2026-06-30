"""Tests for the correlation guard + its paper-scan gate ('_cg')."""
from types import SimpleNamespace

import numpy as np
import pandas as pd

from kudbee_quant.risk.correlation_guard import CorrelationGuard


def _open(symbol, direction):
    return SimpleNamespace(symbol=symbol, direction=direction, status="open", kind="bracket")


class _CorrClient:
    """Returns a deterministic close path per symbol so correlation is controllable."""
    def __init__(self, paths):
        self.paths = paths

    def klines(self, symbol, interval="1h", limit=100):
        closes = self.paths[symbol]
        n = len(closes)
        ts = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
        c = pd.Series(closes, dtype=float)
        return pd.DataFrame({"timestamp": ts, "open": c, "high": c + 1,
                             "low": c - 1, "close": c, "volume": 1.0})


def test_blocks_highly_correlated_same_direction():
    base = list(np.linspace(100, 120, 25))
    guard = CorrelationGuard(threshold=0.80, lookback=20)
    client = _CorrClient({"BTCUSDT": base, "ETHUSDT": [x * 2 + 1 for x in base]})  # corr ~1
    hit, peer = guard.is_correlated("BTCUSDT", 1.0, [_open("ETHUSDT", 1.0)], client)
    assert hit is True and peer == "ETHUSDT"


def test_allows_opposite_direction():
    base = list(np.linspace(100, 120, 25))
    guard = CorrelationGuard(threshold=0.80, lookback=20)
    client = _CorrClient({"BTCUSDT": base, "ETHUSDT": [x * 2 for x in base]})
    hit, peer = guard.is_correlated("BTCUSDT", 1.0, [_open("ETHUSDT", -1.0)], client)
    assert hit is False and peer is None       # short ETH is a hedge, not a stack


def test_allows_uncorrelated():
    guard = CorrelationGuard(threshold=0.80, lookback=20)
    base = list(np.linspace(100, 120, 25))
    zig = [100 + (5 if i % 2 else -5) for i in range(25)]
    client = _CorrClient({"BTCUSDT": base, "ETHUSDT": zig})
    hit, _ = guard.is_correlated("BTCUSDT", 1.0, [_open("ETHUSDT", 1.0)], client)
    assert hit is False


def test_no_peers_allows():
    guard = CorrelationGuard()
    client = _CorrClient({"BTCUSDT": list(range(25))})
    assert guard.is_correlated("BTCUSDT", 1.0, [], client) == (False, None)


def test_fetch_failure_fails_open():
    class _Boom:
        def klines(self, *a, **k):
            raise RuntimeError("rate limited")
    guard = CorrelationGuard()
    assert guard.is_correlated("BTCUSDT", 1.0, [_open("ETHUSDT", 1.0)], _Boom()) == (False, None)


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
    hit = False

    def __init__(self, *a, **k):
        pass

    def is_correlated(self, *a, **k):
        return (_FakeGuard.hit, "ETHUSDT" if _FakeGuard.hit else None)


def test_correlation_gate_blocks(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.hit = True
    monkeypatch.setattr(pp, "CorrelationGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), correlation_guard=True)
    assert logged == []


def test_correlation_gate_allows_and_tags(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.hit = False
    monkeypatch.setattr(pp, "CorrelationGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), correlation_guard=True)
    assert len(logged) == 1 and "_cg" in logged[0].setup


def test_correlation_gate_off_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeGuard.hit = True       # would block if consulted
    monkeypatch.setattr(pp, "CorrelationGuard", _FakeGuard)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())     # guard defaults off
    assert len(logged) == 1 and "_cg" not in logged[0].setup
