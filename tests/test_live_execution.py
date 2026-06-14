"""Live order-placement tests — fully hermetic (a fake exchange, no network).

Covers the real-money seam end to end: maker-only order placement, sizing cap,
concurrency cap, the daily-loss kill-switch, venue-clock fills via poll(),
cancellation, and the signed Binance broker's request shaping / error handling.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kudbee_quant.config.runtime import load_runtime_config
from kudbee_quant.execution.exchange import (
    BUY, CANCELED, FILLED, NEW, BinanceBrokerClient, OrderError, OrderResult,
)
from kudbee_quant.execution.killswitch import (
    DailyLossLimitReached, check_daily_loss, realized_loss_usd_today, realized_usd_pnl,
)
from kudbee_quant.execution.live import LiveExecutor, build_executor
from kudbee_quant.execution.paper import PaperExecutor
from kudbee_quant.journal import Prediction, TradeJournal

from test_journal import _FakeClient


_LIVE_ENV = {"TRADING_MODE": "live", "ENABLE_LIVE_EXECUTION": "true"}


def _cfg(**over):
    env = dict(_LIVE_ENV)
    env.update({k: str(v) for k, v in over.items()})
    return load_runtime_config(env=env)


def _journal(tmp_path):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient())


def _bracket(symbol="BTCUSDT", entry=100.0, stop=99.0, target=103.0, direction=1.0, **kw):
    return Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                      entry=entry, stop=stop, target=target, direction=direction,
                      target_r=3.0, **kw)


class FakeExchange:
    """Programmable ExchangeClient stand-in that records orders placed."""

    def __init__(self, *, on_create=None, on_fetch=None):
        self.orders = []        # list of (symbol, side, qty, price)
        self.cancelled = []
        self._on_create = on_create
        self._on_fetch = on_fetch
        self._seq = 0

    def create_limit_order(self, symbol, side, qty, price):
        self.orders.append((symbol, side, qty, price))
        if self._on_create:
            return self._on_create(symbol, side, qty, price)
        self._seq += 1
        return OrderResult(order_id=f"OID{self._seq}", status=NEW)

    def fetch_order(self, symbol, order_id):
        if self._on_fetch:
            return self._on_fetch(symbol, order_id)
        return OrderResult(order_id=order_id, status=NEW)

    def cancel_order(self, symbol, order_id):
        self.cancelled.append((symbol, order_id))
        return OrderResult(order_id=order_id, status=CANCELED)

    def fetch_free_balance(self, asset):
        return 1_000_000.0


# --- selection + placement --------------------------------------------------

def test_build_executor_returns_live_when_enabled(tmp_path):
    ex = build_executor(_cfg(), journal=_journal(tmp_path), exchange=FakeExchange())
    assert isinstance(ex, LiveExecutor) and ex.mode == "live"

def test_build_executor_paper_when_disabled(tmp_path):
    ex = build_executor(load_runtime_config(env={}), journal=_journal(tmp_path))
    assert isinstance(ex, PaperExecutor)

def test_live_submit_rests_a_maker_limit_and_journals_it(tmp_path):
    j = _journal(tmp_path)
    fake = FakeExchange()
    ex = LiveExecutor(_cfg(MAX_POSITION_SIZE_USD=100), journal=j, exchange=fake)
    res = ex.submit(_bracket(entry=100.0, direction=1.0))
    assert res.accepted and res.mode == "live"
    # one maker order, BUY (long), qty = size/entry = 100/100 = 1.0, at entry price
    assert fake.orders == [("BTCUSDT", BUY, 1.0, 100.0)]
    p = res.prediction
    assert p.mode == "live" and p.status == "pending" and p.pending_limit is True
    assert p.exchange_order_id == "OID1"
    assert p.position_size_usd == 100.0
    assert len(j.predictions) == 1

def test_live_sizing_is_capped_by_max_position_size(tmp_path):
    j = _journal(tmp_path)
    fake = FakeExchange()
    ex = LiveExecutor(_cfg(MAX_POSITION_SIZE_USD=100), journal=j, exchange=fake)
    # ask for $500 but the cap is $100 -> qty reflects the capped notional
    res = ex.submit(_bracket(entry=50.0, position_size_usd=500.0))
    assert res.prediction.position_size_usd == 100.0
    assert fake.orders[0][2] == pytest.approx(100.0 / 50.0)   # qty = 2.0

def test_live_honours_max_concurrent_positions(tmp_path):
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(MAX_CONCURRENT_POSITIONS=1), journal=j, exchange=FakeExchange())
    assert ex.submit(_bracket("BTCUSDT")).accepted is True
    blocked = ex.submit(_bracket("ETHUSDT"))
    assert blocked.accepted is False and "max_concurrent" in blocked.reason
    assert len(j.predictions) == 1

def test_live_rejects_non_bracket_signal(tmp_path):
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=FakeExchange())
    res = ex.submit(Prediction(symbol="BTCUSDT", kind="touch", level=100.0, deadline_days=3))
    assert res.accepted is False and "bracket" in res.reason
    assert len(j.predictions) == 0

def test_live_exchange_rejection_is_surfaced_not_journaled(tmp_path):
    def boom(*a):
        raise OrderError("would immediately match (LIMIT_MAKER)")
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=FakeExchange(on_create=boom))
    res = ex.submit(_bracket())
    assert res.accepted is False and "would immediately match" in res.reason
    assert len(j.predictions) == 0


# --- kill-switch ------------------------------------------------------------

def _resolved_live_loss(usd_size, entry=100.0, stop=90.0, outcome_r=-1.0, when=None):
    p = _bracket(entry=entry, stop=stop, position_size_usd=usd_size)
    p.mode = "live"
    p.status = "miss"
    p.outcome_r = outcome_r
    p.resolved_at = (when or datetime.now(timezone.utc)).isoformat()
    return p

def test_realized_usd_pnl_bridges_r_to_dollars():
    p = _resolved_live_loss(3000.0, entry=100.0, stop=90.0, outcome_r=-1.0)
    # risk_usd = 3000 * 10/100 = 300; net_r ~ -1.0 minus a small crypto fee
    assert realized_usd_pnl(p) < -300.0

def test_paper_and_unsized_trades_dont_move_the_killswitch(tmp_path):
    j = _journal(tmp_path)
    paper = _resolved_live_loss(3000.0)
    paper.mode = "paper"
    unsized = _resolved_live_loss(3000.0)
    unsized.position_size_usd = None
    j.predictions = [paper, unsized]
    assert realized_loss_usd_today(j) == 0.0

def test_killswitch_only_counts_today(tmp_path):
    j = _journal(tmp_path)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1, hours=1)
    j.predictions = [_resolved_live_loss(3000.0, when=yesterday)]
    assert realized_loss_usd_today(j) == 0.0

def test_killswitch_trips_and_blocks_new_live_orders(tmp_path):
    j = _journal(tmp_path)
    j.predictions = [_resolved_live_loss(3000.0)]   # ~ -$300 realized today
    with pytest.raises(DailyLossLimitReached):
        check_daily_loss(j, 250.0)
    # and the executor refuses to open anything new
    ex = LiveExecutor(_cfg(MAX_DAILY_LOSS_USD=250), journal=j, exchange=FakeExchange())
    res = ex.submit(_bracket("ETHUSDT"))
    assert res.accepted is False and "kill-switch" in res.reason.lower()


# --- poll / cancel (venue-clock fills) --------------------------------------

def test_poll_marks_fill_from_venue_clock_not_bar_time(tmp_path):
    venue_time = "2026-06-14T12:34:56+00:00"
    fake = FakeExchange(on_fetch=lambda s, o: OrderResult(
        order_id=o, status=FILLED, filled_qty=1.0, avg_price=100.0, filled_at=venue_time))
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=fake)
    res = ex.submit(_bracket())
    assert res.prediction.status == "pending"
    ex.poll(res.prediction)
    assert res.prediction.status == "open"
    assert res.prediction.filled_at == venue_time     # NOT a bar timestamp

def test_poll_cancels_when_venue_expired_the_limit(tmp_path):
    fake = FakeExchange(on_fetch=lambda s, o: OrderResult(order_id=o, status=CANCELED))
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=fake)
    res = ex.submit(_bracket())
    ex.poll(res.prediction)
    assert res.prediction.status == "cancelled" and "venue" in res.prediction.reason_closed

def test_cancel_pulls_resting_limit(tmp_path):
    fake = FakeExchange()
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=fake)
    res = ex.submit(_bracket())
    ex.cancel(res.prediction)
    assert fake.cancelled == [("BTCUSDT", "OID1")]
    assert res.prediction.status == "cancelled"

def test_reconcile_reports_state_changes(tmp_path):
    fake = FakeExchange(on_fetch=lambda s, o: OrderResult(
        order_id=o, status=FILLED, filled_qty=1.0, avg_price=100.0,
        filled_at="2026-06-14T01:02:03+00:00"))
    j = _journal(tmp_path)
    ex = LiveExecutor(_cfg(), journal=j, exchange=fake)
    ex.submit(_bracket())
    changed = ex.reconcile()
    assert len(changed) == 1 and changed[0].status == "open"


# --- signed Binance broker (fake session, no network) -----------------------

class _FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
    def json(self):
        return self._payload

class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []
    def request(self, method, url, headers=None, timeout=None):
        self.calls.append((method, url, headers))
        return self._resp

def test_broker_requires_keys_before_any_network():
    broker = BinanceBrokerClient(api_key="", api_secret="", session=_FakeSession(None))
    with pytest.raises(OrderError):
        broker.create_limit_order("BTCUSDT", BUY, 1.0, 100.0)

def test_broker_create_order_is_signed_maker_only(monkeypatch):
    resp = _FakeResp(200, {"orderId": 42, "status": "NEW", "executedQty": "0",
                           "cummulativeQuoteQty": "0"})
    sess = _FakeSession(resp)
    broker = BinanceBrokerClient(api_key="k", api_secret="s", session=sess,
                                 base="https://testnet.binance.vision")
    out = broker.create_limit_order("BTCUSDT", BUY, 1.0, 100.0)
    assert out.order_id == "42" and out.status == NEW
    method, url, headers = sess.calls[0]
    assert method == "POST"
    assert "type=LIMIT_MAKER" in url           # maker-only, never a taker
    assert "signature=" in url                 # HMAC signed
    assert headers["X-MBX-APIKEY"] == "k"

def test_broker_surfaces_venue_error_without_leaking_keys():
    resp = _FakeResp(400, {"code": -2010, "msg": "Order would immediately match and take."})
    broker = BinanceBrokerClient(api_key="secretkey", api_secret="secretsecret",
                                 session=_FakeSession(resp))
    with pytest.raises(OrderError) as e:
        broker.create_limit_order("BTCUSDT", BUY, 1.0, 100.0)
    msg = str(e.value)
    assert "immediately match" in msg
    assert "secretkey" not in msg and "secretsecret" not in msg

def test_broker_parses_filled_order_with_venue_timestamp():
    resp = _FakeResp(200, {"orderId": 7, "status": "FILLED", "executedQty": "2",
                           "cummulativeQuoteQty": "200", "updateTime": 1_700_000_000_000})
    broker = BinanceBrokerClient(api_key="k", api_secret="s", session=_FakeSession(resp))
    out = broker.fetch_order("BTCUSDT", "7")
    assert out.is_filled and out.filled_qty == 2.0 and out.avg_price == 100.0
    assert out.filled_at is not None and out.filled_at.endswith("+00:00")

def test_broker_rejects_bad_symbol_ssrf():
    broker = BinanceBrokerClient(api_key="k", api_secret="s", session=_FakeSession(None))
    with pytest.raises(ValueError):
        broker.create_limit_order("../../evil", BUY, 1.0, 100.0)

def test_broker_fetch_free_balance():
    resp = _FakeResp(200, {"balances": [{"asset": "USDT", "free": "123.45", "locked": "0"}]})
    broker = BinanceBrokerClient(api_key="k", api_secret="s", session=_FakeSession(resp))
    assert broker.fetch_free_balance("usdt") == 123.45
