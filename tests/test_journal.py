"""Tests for the prediction journal (no network — fake client)."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from kudbee_quant.config.validated_defaults import TAKER_FEE_PCT
from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.journal.journal import fee_r_of, net_outcome_r, venue_of


class _FakeClient:
    """Returns a fixed OHLCV frame; price ranges 90..110 over recent bars."""
    def __init__(self, base=100.0):
        self.base = base

    def klines(self, symbol, interval="1h", limit=1000):
        now = datetime.now(timezone.utc)
        # Span 24h past..23h "future" so the post-creation window is non-empty
        # (simulates time passing after a prediction is logged).
        ts = pd.date_range(now - timedelta(hours=24), periods=48, freq="h", tz="UTC")
        close = pd.Series(range(48)).apply(lambda i: self.base + (i % 20) - 10)  # ~90..110
        return pd.DataFrame({
            "timestamp": ts, "open": close, "high": close + 1,
            "low": close - 1, "close": close, "volume": 1.0,
        })


def _journal(tmp_path):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient())


def test_add_and_persist(tmp_path):
    j = _journal(tmp_path)
    j.add(Prediction(symbol="ZECUSDT", kind="touch", level=100.0, deadline_days=7, setup="x"))
    j2 = TradeJournal(path=tmp_path / "j.json", client=_FakeClient())
    assert len(j2.predictions) == 1 and j2.predictions[0].symbol == "ZECUSDT"


def test_invalid_kind_rejected():
    with pytest.raises(ValueError):
        Prediction(symbol="X", kind="moon", level=1.0, deadline_days=1)


def test_touch_resolves_hit(tmp_path):
    j = _journal(tmp_path)
    # 100 is within the 90..110 range the fake client produces -> hit.
    j.add(Prediction(symbol="ZECUSDT", kind="touch", level=100.0, deadline_days=0.0001, setup="t"))
    changed = j.check_open()
    assert changed and changed[0].status == "hit"


def test_reach_above_miss_when_unreached_and_deadline_passed(tmp_path):
    j = _journal(tmp_path)
    p = Prediction(symbol="ZECUSDT", kind="reach_above", level=999.0, deadline_days=0.0001)
    # Backdate creation so the deadline has already passed.
    p.created_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[0].status == "miss"


def test_stay_below_violation_is_miss(tmp_path):
    j = _journal(tmp_path)
    # Level 95 is inside the range, so a high will exceed it -> violated -> miss.
    j.add(Prediction(symbol="ZECUSDT", kind="stay_below", level=95.0, deadline_days=7))
    changed = j.check_open()
    assert changed and changed[0].status == "miss"


def test_open_prediction_stays_open(tmp_path):
    j = _journal(tmp_path)
    # Unreached level, deadline far in the future -> still open.
    j.add(Prediction(symbol="ZECUSDT", kind="reach_above", level=999.0, deadline_days=30))
    assert j.check_open() == []
    assert j.predictions[0].status == "open"


# --- N4: journal durability hardening ---------------------------------------

def test_save_is_atomic_no_tmp_file_left_behind(tmp_path):
    """save() must write via a temp file + replace, never leaving a stray
    .tmp behind and never a truncated journal.json on disk."""
    j = _journal(tmp_path)
    j.add(Prediction(symbol="ZECUSDT", kind="touch", level=100.0, deadline_days=7))
    assert j.path.exists()
    tmp = j.path.with_suffix(j.path.suffix + ".tmp")
    assert not tmp.exists()
    # The committed file must be complete, valid JSON.
    import json
    data = json.loads(j.path.read_text())
    assert len(data) == 1 and data[0]["symbol"] == "ZECUSDT"


def test_check_open_isolates_one_symbols_failure(tmp_path, monkeypatch):
    """A dead feed for ONE symbol must not block the rest of the book from
    resolving (regression for the '|| true' masked full-book stall)."""
    j = _journal(tmp_path)
    good = Prediction(symbol="GOOD", kind="touch", level=100.0, deadline_days=0.0001, setup="g")
    bad = Prediction(symbol="BAD", kind="touch", level=100.0, deadline_days=0.0001, setup="b")
    j.add(good)
    j.add(bad)

    orig_evaluate = j._evaluate

    def _flaky(p):
        if p.symbol == "BAD":
            raise RuntimeError("dead feed")
        return orig_evaluate(p)

    monkeypatch.setattr(j, "_evaluate", _flaky)
    changed = j.check_open()
    symbols_changed = {p.symbol for p in changed}
    assert "GOOD" in symbols_changed
    assert "BAD" not in symbols_changed
    assert good.status == "hit"
    assert bad.status == "open"   # untouched, still open — will retry next cycle


def test_scorecard_counts_resolved(tmp_path):
    j = _journal(tmp_path)
    j.add(Prediction(symbol="A", kind="touch", level=100.0, deadline_days=0.0001, setup="s1"))
    j.add(Prediction(symbol="A", kind="reach_above", level=100.0, deadline_days=0.0001, setup="s1"))
    j.check_open()
    sc = j.scorecard()
    assert sc.loc[sc["setup"] == "s1", "n"].iloc[0] == 2


def test_pending_limit_promotes_to_open_on_fill(tmp_path):
    # A limit whose entry price is reached should FILL -> status 'open' with a
    # filled_at, not linger as 'pending'. The fake client oscillates ~90..110;
    # wide stop/target so it fills but doesn't immediately resolve.
    j = _journal(tmp_path)
    p = Prediction(symbol="ZECUSDT", kind="bracket", level=100.0, deadline_days=30,
                   entry=100.0, stop=80.0, target=120.0, direction=1.0,
                   pending_limit=True, fill_deadline_days=30, setup="cts")
    assert p.status == "pending"            # limits start unfilled
    j.add(p)
    j.check_open()
    assert p.status == "open" and p.filled_at is not None


def test_filled_limit_never_reverts_to_pending_or_cancelled(tmp_path):
    # Regression (#100): once filled (filled_at stamped), a limit must NEVER be
    # persisted back to 'pending'/'cancelled' — even if a later evaluation sees an
    # empty/stale window. Pre-fix, the empty-window branch returned pending/cancelled
    # for any status=='pending' row regardless of filled_at, reverting live trades.
    j = _journal(tmp_path)
    now = datetime.now(timezone.utc)
    p = Prediction(symbol="ZECUSDT", kind="bracket", level=100.0, deadline_days=30,
                   entry=100.0, stop=80.0, target=120.0, direction=1.0,
                   pending_limit=True, fill_deadline_days=0.5, setup="cts")
    # Reproduce the inconsistent on-disk state: filled, but created_at in the
    # FUTURE so the post-creation window is empty (the live stale-window case).
    p.created_at = (now + timedelta(hours=30)).isoformat()
    p.filled_at = now.isoformat()
    p.status = "pending"
    j.add(p)
    j.check_open()
    assert p.status == "open"               # never reverted to pending/cancelled
    assert p.filled_at is not None          # fill timestamp preserved


# --- net-of-fee / per-venue scoring (MEMORY §26) ---------------------------

def _bracket(symbol, outcome_r, status="hit", entry=100.0, stop=99.0):
    """A resolved bracket trade; entry/stop give risk=1 so fee_r == fee_pct*entry."""
    return Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                      entry=entry, stop=stop, target=103.0, direction=1.0,
                      target_r=3.0, status=status, outcome_r=outcome_r)


def test_venue_classification():
    crypto = Prediction(symbol="ZECUSDT", kind="touch", level=1.0, deadline_days=1)
    tradfi = Prediction(symbol="yahoo:GC=F", kind="touch", level=1.0, deadline_days=1)
    explicit = Prediction(symbol="binance:BTCUSDT", kind="touch", level=1.0, deadline_days=1)
    assert venue_of(crypto) == "crypto"
    assert venue_of(tradfi) == "tradfi"
    assert venue_of(explicit) == "crypto"


def test_fee_r_and_net_by_venue():
    expected_fee = TAKER_FEE_PCT * 100.0 / 1.0   # fee_pct * entry / risk(=1)
    crypto = _bracket("BTCUSDT", outcome_r=3.0)
    tradfi = _bracket("yahoo:GC=F", outcome_r=3.0)
    assert fee_r_of(crypto) == pytest.approx(expected_fee)
    assert fee_r_of(tradfi) == 0.0                       # zero-fee promo venue
    assert net_outcome_r(crypto) == pytest.approx(3.0 - expected_fee)
    assert net_outcome_r(tradfi) == pytest.approx(3.0)   # net == gross on TradFi


def test_fee_r_zero_for_non_bracket():
    p = Prediction(symbol="BTCUSDT", kind="touch", level=100.0, deadline_days=1)
    assert fee_r_of(p) == 0.0          # no entry/stop -> no R-denominated fee
    assert net_outcome_r(p) is None    # unresolved / carries no R


def test_tp1_fill_adds_a_half_round_trip(tmp_path):
    base = _bracket("BTCUSDT", outcome_r=2.0)
    base.tp1, base.tp1_frac = 102.0, 0.5
    no_tp1 = fee_r_of(base)
    base.tp1_filled_at = "2026-06-09T00:00:00+00:00"     # TP1 banked -> extra exit leg
    assert fee_r_of(base) == pytest.approx(no_tp1 * (1 + 0.5 * 0.5))


def test_scorecard_has_net_columns(tmp_path):
    j = _journal(tmp_path)
    j.predictions = [_bracket("BTCUSDT", outcome_r=3.0)]
    sc = j.scorecard()
    assert {"net_expectancy_r", "net_total_r"} <= set(sc.columns)
    assert sc.iloc[0]["net_expectancy_r"] == pytest.approx(3.0 - TAKER_FEE_PCT * 100.0)


def test_venue_record_splits_gross_and_net(tmp_path):
    j = _journal(tmp_path)
    j.predictions = [_bracket("BTCUSDT", outcome_r=3.0),
                     _bracket("yahoo:GC=F", outcome_r=3.0)]
    rec = j.venue_record()
    fee = TAKER_FEE_PCT * 100.0
    assert rec["crypto"]["n"] == 1 and rec["tradfi"]["n"] == 1
    # TradFi 0-fee venue: net expectancy == gross. Crypto bleeds exactly the taker.
    assert rec["tradfi"]["net_expectancy_r"] == pytest.approx(rec["tradfi"]["expectancy_r"])
    assert rec["crypto"]["net_expectancy_r"] == pytest.approx(rec["crypto"]["expectancy_r"] - fee)
    assert rec["crypto"]["avg_fee_r"] == pytest.approx(fee)
    assert rec["tradfi"]["avg_fee_r"] == 0.0


# --- new record surfaces: symbol / session / equity-by-book -----------------

def test_symbol_record_groups_and_sorts_worst_first(tmp_path):
    j = _journal(tmp_path)
    # BTC nets positive; ETH nets deeply negative -> ETH (worst) sorts first.
    j.predictions = [
        _bracket("BTCUSDT", outcome_r=3.0),
        _bracket("BTCUSDT", outcome_r=3.0),
        _bracket("ETHUSDT", outcome_r=-1.0, status="miss"),
        _bracket("ETHUSDT", outcome_r=-1.0, status="miss"),
        _bracket("ETHUSDT", outcome_r=-1.0, status="miss"),
    ]
    sr = j.symbol_record()
    assert {"avg_r_per_trade", "total_net_r", "pct_of_total_trades"} <= set(sr.columns)
    assert list(sr["symbol"])[0] == "ETHUSDT"              # worst net_total_r first
    assert sr["net_total_r"].is_monotonic_increasing       # ascending
    eth = sr[sr["symbol"] == "ETHUSDT"].iloc[0]
    assert eth["n"] == 3 and eth["hits"] == 0
    assert eth["pct_of_total_trades"] == pytest.approx(60.0)
    # convenience columns mirror the canonical ones
    assert eth["avg_r_per_trade"] == pytest.approx(eth["expectancy_r"])
    assert eth["total_net_r"] == pytest.approx(eth["net_total_r"])


def test_symbol_record_empty(tmp_path):
    j = _journal(tmp_path)
    j.predictions = []
    sr = j.symbol_record()
    assert sr.empty and "pct_of_total_trades" in sr.columns


def test_session_record_classifies_by_utc_hour(tmp_path):
    j = _journal(tmp_path)

    def at(hour, r, status="hit"):
        p = _bracket("BTCUSDT", outcome_r=r, status=status)
        p.filled_at = f"2026-06-15T{hour:02d}:30:00+00:00"
        return p

    j.predictions = [
        at(8, 3.0),             # London
        at(13, 3.0),            # NY Overlap
        at(16, -1.0, "miss"),   # NY
        at(22, 3.0),            # Asia
        at(3, 3.0),             # Asia (wraps past midnight)
    ]
    rec = j.session_record()
    assert {"hit_rate", "expectancy_r", "net_expectancy_r"} <= set(rec.columns)
    assert list(rec["session"]) == ["London", "NY Overlap", "NY", "Asia"]  # canonical order
    by = {row["session"]: row for _, row in rec.iterrows()}
    assert by["Asia"]["n"] == 2
    assert by["London"]["n"] == 1 and by["NY"]["hits"] == 0


def test_session_record_falls_back_to_created_at(tmp_path):
    j = _journal(tmp_path)
    p = _bracket("BTCUSDT", outcome_r=3.0)
    p.filled_at = None
    p.created_at = "2026-06-15T09:00:00+00:00"   # London
    j.predictions = [p]
    rec = j.session_record()
    assert rec.iloc[0]["session"] == "London"


def test_equity_curve_by_book_splits_by_prefix(tmp_path):
    j = _journal(tmp_path)

    def mk(setup, r, t):
        p = _bracket("BTCUSDT", outcome_r=r)
        p.setup = setup
        p.resolved_at = t
        return p

    j.predictions = [
        mk("core_a", 1.0, "2026-06-15T01:00:00+00:00"),
        mk("core_a", 2.0, "2026-06-15T02:00:00+00:00"),
        mk("trend_b", -1.0, "2026-06-15T03:00:00+00:00"),
        mk("other", 5.0, "2026-06-15T04:00:00+00:00"),
    ]
    eq = j.equity_curve_by_book()
    assert set(eq) == {"core", "trend", "all"}
    assert eq["core"] == [1.0, 3.0]                 # cumulative within core book
    assert eq["trend"] == [-1.0]
    assert eq["all"] == [1.0, 3.0, 2.0, 7.0]        # time-ordered cumulative over ALL
