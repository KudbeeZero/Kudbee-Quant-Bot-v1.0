"""Tests for bracket journal predictions and the paper-trading scan (no network)."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from kudbee_quant.journal import Prediction, TradeJournal


class _FakeClient:
    def __init__(self, path_prices):
        self.prices = path_prices

    def klines(self, symbol, interval="1h", limit=1000):
        now = datetime.now(timezone.utc)
        n = len(self.prices)
        ts = pd.date_range(now - timedelta(hours=n - 1), periods=n, freq="h", tz="UTC")
        c = pd.Series(self.prices, dtype=float)
        return pd.DataFrame({"timestamp": ts, "open": c, "high": c + 0.5,
                             "low": c - 0.5, "close": c, "volume": 1.0})


def _journal(tmp_path, prices):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient(prices))


def _bracket(direction, entry, stop, target, days=1.0):
    p = Prediction(symbol="X", kind="bracket", level=entry, entry=entry, stop=stop,
                   target=target, direction=direction, target_r=2.0, deadline_days=days,
                   setup="confluence_r")
    # Backdate so the fake bars fall after creation.
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    return p


def test_bracket_target_first_is_win(tmp_path):
    # Long entry 100, stop 99, target 102. Price path reaches 102 (high 102.5).
    j = _journal(tmp_path, [100, 101, 102, 103])
    j.add(_bracket(1, 100, 99, 102))
    changed = j.check_open()
    assert changed and changed[0].status == "hit" and changed[0].outcome_r == 2.0


def test_bracket_stop_first_is_loss(tmp_path):
    # Long entry 100, stop 99, target 102. Price drops to 98 first.
    j = _journal(tmp_path, [100, 98, 102, 103])
    j.add(_bracket(1, 100, 99, 102))
    changed = j.check_open()
    assert changed and changed[0].status == "miss" and changed[0].outcome_r == -1.0


def test_bracket_short_target(tmp_path):
    # Short entry 100, stop 101, target 98. Price falls to 97.
    j = _journal(tmp_path, [100, 99, 97, 97])
    j.add(_bracket(-1, 100, 101, 98))
    changed = j.check_open()
    assert changed and changed[0].status == "hit" and changed[0].outcome_r == 2.0


def test_scorecard_reports_expectancy_r(tmp_path):
    j = _journal(tmp_path, [100, 102.5, 103, 103])  # this path hits long target
    j.add(_bracket(1, 100, 99, 102))
    j.check_open()
    sc = j.scorecard()
    assert "expectancy_r" in sc.columns
    assert sc.loc[sc["setup"] == "confluence_r", "expectancy_r"].iloc[0] == 2.0


def _pending(direction, limit, stop, target, days=2.0, fill_days=0.5):
    p = Prediction(symbol="X", kind="bracket", level=limit, entry=limit, stop=stop,
                   target=target, direction=direction, target_r=3.0, deadline_days=days,
                   pending_limit=True, signal_price=limit + direction, fill_deadline_days=fill_days,
                   setup="confluence_r")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    return p


def test_pending_limit_fills_then_wins(tmp_path):
    # Long limit at 99.5 (below signal). Price dips to 99.5 (fills), then runs to
    # target 99.5+3=102.5. Stop 98.5. Path: 100,99.4(fill),101,103.
    j = _journal(tmp_path, [100, 99.4, 101, 103])
    j.add(_pending(1, 99.5, 98.5, 102.5))
    changed = j.check_open()
    assert changed and changed[-1].status == "hit" and changed[-1].outcome_r == 3.0


def test_pending_limit_cancelled_if_never_filled(tmp_path):
    # Price never dips to the 99.5 limit within the fill window -> cancelled.
    j = _journal(tmp_path, [100, 100.5, 101, 102])
    p = _pending(1, 99.5, 98.5, 102.5, fill_days=0.01)  # tiny fill window (already passed)
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "cancelled"
    assert changed[-1].outcome_r is None  # no trade -> not scored


def test_pending_limit_stays_pending_within_window(tmp_path):
    # Not filled yet, fill window still open -> remains pending (no resolution).
    j = _journal(tmp_path, [100, 100.5, 101, 101])
    p = Prediction(symbol="X", kind="bracket", level=99.5, entry=99.5, stop=98.5,
                   target=102.5, direction=1.0, target_r=3.0, deadline_days=5,
                   pending_limit=True, fill_deadline_days=5.0, setup="c")
    j.add(p)
    assert j.check_open() == []  # still pending, nothing changed
    assert j.predictions[-1].status == "pending"


def test_bracket_partial_tp1_banks_then_breakeven(tmp_path):
    # Long entry 100, stop 99, TP1 at 101 (half), TP2/target at 103.
    # Price hits 101 (banks 0.5*1R=0.5R, stop->BE 100), then falls back to 100
    # before TP2 -> remainder ~0R. Blended = 0.5R. Path: 100,101,100,99.9.
    j = _journal(tmp_path, [100, 101, 100, 99.9])
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, tp1=101, tp1_frac=0.5, be_after_tp1=True,
                   direction=1.0, target_r=3.0, deadline_days=1.0, setup="partial")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].outcome_r is not None
    assert abs(changed[-1].outcome_r - 0.5) < 1e-9
    assert changed[-1].tp1_filled_at is not None


def test_bracket_partial_full_run_blends_targets(tmp_path):
    # TP1 at 101 (half @ +1R), TP2 at 103 (half @ +3R). Price runs to 103.
    # Blended = 0.5*1 + 0.5*3 = 2.0R. Path: 100,101,103,103.
    j = _journal(tmp_path, [100, 101, 103, 103])
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, tp1=101, tp1_frac=0.5, be_after_tp1=True,
                   direction=1.0, target_r=3.0, deadline_days=1.0, setup="partial")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "hit"
    assert abs(changed[-1].outcome_r - 2.0) < 1e-9


def test_paper_scan_logs_when_signalling(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    # Force a strong long confluence signal (60% of factors aligned).
    fake_levels = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                                "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake_levels)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})
    j = TradeJournal(path=tmp_path / "j.json", client=C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j, client=C())
    assert len(logged) == 1
    p = logged[0]
    # Pending LIMIT entry at a 0.25 ATR retrace: 100 - 0.25 = 99.75; stop 98.75;
    # target 99.75 + 2*1 = 101.75.
    assert p.kind == "bracket" and p.pending_limit and p.direction == 1.0
    assert abs(p.entry - 99.75) < 1e-9 and abs(p.stop - 98.75) < 1e-9 and abs(p.target - 101.75) < 1e-9
    # Re-scan: already open on BTCUSDT -> no duplicate.
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, journal=j, client=C()) == []
    # Below-threshold confluence (40%) -> nothing logged on a fresh symbol.
    fake_levels["confluence_pct"] = [0.4]
    j2 = TradeJournal(path=tmp_path / "j2.json", client=C())
    assert pp.paper_scan(["ETHUSDT"], min_pct=0.5, journal=j2, client=C()) == []


def test_paper_scan_tags_tradfi_venue(tmp_path, monkeypatch):
    """A yahoo: (TradFi) spec is logged with the '_tradfi' setup tag so its
    forward record scores separately from the fee-paying crypto book; a bare
    crypto symbol is NOT tagged."""
    import kudbee_quant.paper.paper as pp
    fake_levels = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                                "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake_levels)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "tf.json", client=C())
    logged = pp.paper_scan(["yahoo:GC=F"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j, client=C())
    assert len(logged) == 1
    p = logged[0]
    assert p.symbol == "YAHOO:GC=F"        # spec preserved; source lowercased on route
    assert p.setup.endswith("_tradfi")     # separate scorecard row
    assert "TradFi 0-fee venue" in p.note

    j2 = TradeJournal(path=tmp_path / "cr.json", client=C())
    crypto = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j2, client=C())
    assert crypto and "_tradfi" not in crypto[0].setup


class _C1:
    def klines(self, *a, **k):
        return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})


def test_paper_scan_long_only_skips_shorts(tmp_path, monkeypatch):
    """--long-only: a SHORT signal is skipped; a LONG is taken and tagged '_lo'."""
    import kudbee_quant.paper.paper as pp
    monkeypatch.setattr(pp, "build_levels", lambda df: df)

    short = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                          "direction": [-1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: short)
    j = TradeJournal(path=tmp_path / "lo.json", client=_C1())
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         long_only=True, journal=j, client=_C1()) == []

    long = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: long)
    j2 = TradeJournal(path=tmp_path / "lo2.json", client=_C1())
    logged = pp.paper_scan(["ETHUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           long_only=True, journal=j2, client=_C1())
    assert len(logged) == 1 and logged[0].direction == 1.0 and "_lo" in logged[0].setup


def test_paper_scan_killzone_gate_filters_off_hours(tmp_path, monkeypatch):
    """--killzone-gate: skip when all session flags are False; take (tag '_kz')
    when one is True; NO-OP when the frame lacks the flag columns entirely."""
    import kudbee_quant.paper.paper as pp
    monkeypatch.setattr(pp, "build_levels", lambda df: df)

    off = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                        "direction": [1.0], "confluence_pct": [0.6],
                        "in_london_kz": [False], "in_ny_brinks": [False],
                        "in_overlap": [False]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: off)
    j = TradeJournal(path=tmp_path / "kz.json", client=_C1())
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         killzone_gate=True, journal=j, client=_C1()) == []

    on = off.copy()
    on["in_ny_brinks"] = [True]
    monkeypatch.setattr(pp, "confluence_score", lambda df: on)
    j2 = TradeJournal(path=tmp_path / "kz2.json", client=_C1())
    logged = pp.paper_scan(["ETHUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           killzone_gate=True, journal=j2, client=_C1())
    assert len(logged) == 1 and "_kz" in logged[0].setup

    nokz = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: nokz)
    j3 = TradeJournal(path=tmp_path / "kz3.json", client=_C1())
    assert len(pp.paper_scan(["SOLUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                             killzone_gate=True, journal=j3, client=_C1())) == 1


def _trend_frame(stacked: bool, n: int = 14) -> pd.DataFrame:
    """Feature frame for the §C gate. stacked=True => a clean, WIDENING 13>50>800
    up-stack; False => ema_13 < ema_50 (no clean stack in either direction)."""
    if stacked:
        e13 = [102.0 + i * 0.2 for i in range(n)]   # widening gap over ema_50
        e50 = [101.0] * n
        e800 = [100.0] * n
    else:
        e13 = [100.5] * n                            # below ema_50 -> not up; not down either
        e50 = [101.0] * n
        e800 = [100.0] * n
    return pd.DataFrame({"ema_13": e13, "ema_50": e50, "ema_800": e800,
                         "atr": [1.0] * n, "close": [103.0] * n})


def test_paper_scan_clean_trend_stack_gate(tmp_path, monkeypatch):
    """§C gate blocks signals when EMAs are NOT cleanly stacked/widening, and
    passes (tagging '_cts') when they are."""
    import kudbee_quant.paper.paper as pp
    sig = pd.DataFrame({"close": [103.0], "atr": [1.0], "strength": [6.0],
                        "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: sig)

    monkeypatch.setattr(pp, "build_levels", lambda df: _trend_frame(False))
    j = TradeJournal(path=tmp_path / "cts0.json", client=_C1())
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         clean_trend_stack=True, journal=j, client=_C1()) == []

    monkeypatch.setattr(pp, "build_levels", lambda df: _trend_frame(True))
    j2 = TradeJournal(path=tmp_path / "cts1.json", client=_C1())
    logged = pp.paper_scan(["ETHUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           clean_trend_stack=True, journal=j2, client=_C1())
    assert len(logged) == 1 and "_cts" in logged[0].setup


def test_per_book_dedup_lets_experiment_coexist(tmp_path, monkeypatch):
    """Per-book dedup: the §C (_cts) book holds its OWN trade on a symbol+timeframe
    the baseline book already occupies; re-running §C does NOT duplicate."""
    import kudbee_quant.paper.paper as pp
    monkeypatch.setattr(pp, "build_levels", lambda df: _trend_frame(True))
    sig = pd.DataFrame({"close": [103.0], "atr": [1.0], "strength": [6.0],
                        "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: sig)
    j = TradeJournal(path=tmp_path / "book.json", client=_C1())

    base = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         max_symbol_risk=0.05, journal=j, client=_C1())
    assert len(base) == 1 and "_cts" not in base[0].setup
    # baseline already holds (BTC,1h,'') -> §C opens a SECOND BTC 1h trade (book '_cts')
    cts = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                        clean_trend_stack=True, max_symbol_risk=0.05, journal=j, client=_C1())
    assert len(cts) == 1 and "_cts" in cts[0].setup
    # re-running §C is deduped within its own book
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                         clean_trend_stack=True, max_symbol_risk=0.05, journal=j, client=_C1()) == []


def test_paper_scan_trailing_atr_stamps_atr_at_entry(tmp_path, monkeypatch):
    """--trailing-atr stamps trailing_atr + the signal-time ATR on the Prediction
    (and leaves tp1 None); default leaves both None."""
    import kudbee_quant.paper.paper as pp
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    lvl = pd.DataFrame({"close": [100.0], "atr": [2.0], "strength": [6.0],
                        "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "confluence_score", lambda df: lvl)

    j = TradeJournal(path=tmp_path / "tr.json", client=_C1())
    p = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.9, stop_atr=1.5,
                      trailing_atr=1.5, journal=j, client=_C1())[0]
    assert p.trailing_atr == 1.5 and p.atr_at_entry == 2.0 and p.tp1 is None

    j2 = TradeJournal(path=tmp_path / "tr2.json", client=_C1())
    p2 = pp.paper_scan(["ETHUSDT"], min_pct=0.5, stop_atr=1.5, journal=j2, client=_C1())[0]
    assert p2.trailing_atr is None and p2.atr_at_entry is None


def test_trailing_stop_wires_through_journal(tmp_path):
    """A Prediction carrying trailing_atr/atr_at_entry resolves via the chandelier
    trail in resolve_bracket: a runner to +3.5R that reverses locks ~+2.5R (a 1R
    trail), NOT the far target and NOT the −1R stop. Proves the journal wiring."""
    j = _journal(tmp_path, [100, 103, 101])  # high 103.5 then low 100.5
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=110, direction=1.0, target_r=10.0, deadline_days=1.0,
                   trailing_atr=1.0, atr_at_entry=1.0, setup="trail")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "hit"
    assert abs(changed[-1].outcome_r - 2.5) < 1e-9
