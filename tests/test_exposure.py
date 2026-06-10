"""Net/gross exposure guard tests (no network)."""
from datetime import datetime, timedelta, timezone

import pandas as pd

from kudbee_quant.exposure import (portfolio_exposure, symbol_exposure,
                                   total_gross_risk, would_exceed)
from kudbee_quant.journal import Prediction, TradeJournal


def _bracket(symbol, direction, tf, status="open"):
    p = Prediction(symbol=symbol, kind="bracket", level=100, entry=100, stop=99,
                   target=103, direction=direction, target_r=3.0, deadline_days=1.0,
                   timeframe=tf, setup="x")
    p.status = status
    return p


def test_symbol_exposure_counts_both_sides():
    preds = [_bracket("ZECUSDT", 1, "1h"), _bracket("ZECUSDT", -1, "5m"),
             _bracket("BTCUSDT", 1, "1h")]
    ex = symbol_exposure(preds, "ZECUSDT", risk_per_trade=0.01)
    assert ex.n_long == 1 and ex.n_short == 1
    assert abs(ex.gross_risk - 0.02) < 1e-9     # both can lose
    assert abs(ex.net_risk - 0.0) < 1e-9        # directionally flat
    assert ex.net_direction == 0


def test_net_direction_when_lopsided():
    preds = [_bracket("ZECUSDT", 1, "1h"), _bracket("ZECUSDT", 1, "2h"),
             _bracket("ZECUSDT", -1, "5m")]
    ex = symbol_exposure(preds, "ZECUSDT", risk_per_trade=0.01)
    assert ex.n_long == 2 and ex.n_short == 1
    assert abs(ex.gross_risk - 0.03) < 1e-9
    assert abs(ex.net_risk - 0.01) < 1e-9
    assert ex.net_direction == 1                # net long


def test_would_exceed_blocks_third_trade_at_2pct_cap():
    preds = [_bracket("ZECUSDT", 1, "1h"), _bracket("ZECUSDT", -1, "5m")]  # 2% gross
    assert would_exceed(preds, "ZECUSDT", 1, risk_per_trade=0.01, max_symbol_risk=0.02)
    # A fresh coin has room.
    assert not would_exceed(preds, "ETHUSDT", 1, risk_per_trade=0.01, max_symbol_risk=0.02)


def test_resolved_trades_dont_count():
    preds = [_bracket("ZECUSDT", 1, "1h", status="hit"),
             _bracket("ZECUSDT", -1, "5m", status="miss")]
    ex = symbol_exposure(preds, "ZECUSDT")
    assert ex.gross_risk == 0.0
    assert total_gross_risk(preds) == 0.0


def test_paper_scan_respects_symbol_risk_cap(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df, **kw: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "j.json", client=C())
    # cap 2%, 1% per trade -> at most 2 concurrent trades on one coin.
    a = pp.paper_scan(["BTCUSDT"], min_pct=0.5, intervals=["1h"], journal=j, client=C(),
                      risk_per_trade=0.01, max_symbol_risk=0.02)
    b = pp.paper_scan(["BTCUSDT"], min_pct=0.5, intervals=["5m"], journal=j, client=C(),
                      risk_per_trade=0.01, max_symbol_risk=0.02)
    c = pp.paper_scan(["BTCUSDT"], min_pct=0.5, intervals=["15m"], journal=j, client=C(),
                      risk_per_trade=0.01, max_symbol_risk=0.02)
    assert len(a) == 1 and len(b) == 1     # 1h + 5m allowed (2% gross)
    assert len(c) == 0                     # 15m would be 3% -> blocked by the guard
    ex = symbol_exposure(j.predictions, "BTCUSDT")
    assert ex.n_long == 2 and ex.gross_risk <= 0.02 + 1e-9
