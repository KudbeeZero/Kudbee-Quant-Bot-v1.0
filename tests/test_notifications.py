"""Tests for the Telegram notification layer (no real network).

Covers the two things that matter: (1) the gating — with no creds everything is a
silent no-op and never raises; (2) the message formatting — pure functions that
turn Predictions / report dicts into the strings we'd send.
"""
from __future__ import annotations

import kudbee_quant.notifications.telegram as tg
from kudbee_quant.journal import Prediction
from kudbee_quant.notifications import (
    notify_summary,
    notify_trades_opened,
    notify_trades_resolved,
    send_telegram,
    telegram_enabled,
)
from kudbee_quant.notifications.notify import (
    format_summary,
    format_trades_opened,
    format_trades_resolved,
)
from kudbee_quant.notifications.notify import _g, _realized_today, _book_label
from kudbee_quant.notifications.telegram import _split


def test_g_price_format_no_scientific_notation():
    # The bug: BTC at 64,170 rendered as "6.417e+04" on mobile. Now: thousands
    # separators >=1000, 4g mid-range, 5g sub-1 — never scientific notation.
    assert _g(64170.0) == "64,170"
    assert _g(1735.0) == "1,735"
    assert _g(591.3) == "591.3"
    assert _g(8.0134) == "8.013"
    assert _g(0.08349) == "0.08349"   # DOGE-range unaffected
    assert _g(None) == "?"
    for v in (64170.0, 1735.0, 999999.0):
        assert "e" not in _g(v).lower()   # no scientific notation


def _pred(symbol="BTCUSDT", direction=1.0, status="open", outcome_r=None, pending=True):
    return Prediction(
        symbol=symbol, kind="bracket", level=100.0, deadline_days=3.0,
        entry=100.0, stop=99.0, target=103.0, direction=direction, target_r=3.0,
        timeframe="1h", status=status, outcome_r=outcome_r, pending_limit=pending,
    )


# --- gating: no creds -> silent no-op, never raises -------------------------

def _clear_env(monkeypatch):
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "KUDBEE_TELEGRAM_ENABLED"):
        monkeypatch.delenv(k, raising=False)


def test_disabled_without_creds(monkeypatch):
    _clear_env(monkeypatch)
    assert telegram_enabled() is False
    # Every entry point must no-op (return False) and not touch the network.
    assert send_telegram("hi") is False
    assert notify_trades_opened([_pred()]) is False
    assert notify_trades_resolved([_pred(status="hit", outcome_r=3.0)]) is False
    assert notify_summary() is False


def test_killswitch_overrides_creds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("KUDBEE_TELEGRAM_ENABLED", "false")
    assert telegram_enabled() is False
    monkeypatch.setenv("KUDBEE_TELEGRAM_ENABLED", "1")
    assert telegram_enabled() is True


def test_enabled_with_both_creds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)
    assert telegram_enabled() is True


def test_send_swallows_network_error(monkeypatch):
    """A raising HTTP client must not propagate — send returns False."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)

    class _Boom:
        def post(self, *a, **k):
            raise RuntimeError("network down")

    monkeypatch.setitem(__import__("sys").modules, "requests", _Boom())
    assert send_telegram("hi") is False


def test_send_error_does_not_leak_token(monkeypatch, caplog):
    """A network error must not log the bot token (it lives in the request URL)."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "SECRET123:abcdef")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)

    class _Boom:
        def post(self, *a, **k):
            # Mimic requests embedding the token-bearing URL in its message.
            raise RuntimeError(
                "Max retries exceeded with url: /botSECRET123:abcdef/sendMessage")

    monkeypatch.setitem(__import__("sys").modules, "requests", _Boom())
    import logging
    with caplog.at_level(logging.WARNING):
        assert send_telegram("hi") is False
    assert "SECRET123:abcdef" not in caplog.text
    assert "***" in caplog.text


def test_send_success_path(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)
    sent = {}

    class _Resp:
        status_code = 200
        text = "ok"

    class _OK:
        def post(self, url, json, timeout):
            sent["json"] = json
            return _Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", _OK())
    assert send_telegram("hello") is True
    assert sent["json"]["text"] == "hello"
    assert sent["json"]["chat_id"] == "1"


# --- formatting (pure) ------------------------------------------------------

def test_format_trades_opened():
    msg = format_trades_opened([_pred("BTCUSDT"), _pred("ETHUSDT", direction=-1.0)])
    assert "2 new trade setups" in msg
    assert "LONG BTCUSDT" in msg
    assert "SHORT ETHUSDT" in msg
    assert "limit pending" in msg


def test_format_trades_opened_singular():
    assert "1 new trade setup logged" in format_trades_opened([_pred()])


def test_format_trades_resolved_filters_and_totals():
    preds = [
        _pred("BTCUSDT", status="hit", outcome_r=3.0),
        _pred("ETHUSDT", status="miss", outcome_r=-1.0),
        _pred("SOLUSDT", status="open"),          # still open -> excluded
    ]
    msg = format_trades_resolved(preds)
    assert "2 trades resolved" in msg
    assert "+2.00R total" in msg          # 3.0 + (-1.0)
    assert "✅ BTCUSDT" in msg
    assert "❌ ETHUSDT" in msg
    assert "SOLUSDT" not in msg


def test_format_summary():
    report = {"portfolio": {
        "total_open": 3, "total_unrealized_r": 1.25, "total_unrealized_usd": None,
        "winners_open": 2, "losers_open": 1, "total_open_risk_pct": 3.0,
        "closest_to_stop": "ETHUSDT", "closest_to_tp": "BTCUSDT", "warnings": ["XRPUSDT near stop"],
    }}
    record = {"crypto": {"n": 10, "hits": 4, "net_expectancy_r": 0.12}}
    msg = format_summary(report, record=record)
    assert "Open: 3" in msg
    assert "+1.25R" in msg
    assert "near stop" in msg
    assert "crypto 4/10" in msg
    # back-compat: no trades / no realized_today -> none of the new blocks appear
    assert "By book" not in msg and "Best:" not in msg and "Today:" not in msg


def _t(symbol, setup, ur, pct=None):
    return {"symbol": symbol, "setup": setup, "unrealized_r": ur, "pnl_pct": pct}


def test_format_summary_per_book_breakdown_and_best_worst():
    report = {
        "portfolio": {"total_open": 3, "total_unrealized_r": 0.7,
                      "total_unrealized_usd": None, "winners_open": 2, "losers_open": 1,
                      "total_open_risk_pct": 3.0},
        "trades": [
            _t("BTCUSDT", "confluence_r_60pct_tf", 0.8, 2.1),       # core
            _t("ETHUSDT", "confluence_r_60pct_tf_cts", 0.4, 1.0),   # trend
            _t("SOLUSDT", "confluence_r_60pct_tf_lo", -0.5, -1.3),  # longs
        ],
    }
    msg = format_summary(report)
    # per-book breakdown, validated 'core' listed first
    assert "By book:" in msg
    assert "core 1 (+0.80R)" in msg and "trend 1 (+0.40R)" in msg and "longs 1 (-0.50R)" in msg
    assert msg.index("core") < msg.index("trend") < msg.index("longs")
    # best & worst by unrealized R
    assert "Best: ETHUSDT" not in msg          # ETH +0.4 is not the best
    assert "Best: BTCUSDT +0.80R (+2.1%)" in msg
    assert "Worst: SOLUSDT -0.50R (-1.3%)" in msg


def test_format_summary_single_book_skips_breakdown():
    # One book -> headline already covers it; don't emit a noisy "By book" line.
    report = {"portfolio": {"total_open": 2, "total_unrealized_r": 1.0,
                            "total_unrealized_usd": None, "winners_open": 2,
                            "losers_open": 0, "total_open_risk_pct": 2.0},
              "trades": [_t("BTCUSDT", "confluence_r_60pct_tf", 0.6, 1.0),
                         _t("ETHUSDT", "confluence_r_60pct_tf", 0.4, 0.5)]}
    msg = format_summary(report)
    assert "By book" not in msg
    assert "Best: BTCUSDT" in msg and "Worst: ETHUSDT" in msg


def test_format_summary_realized_today():
    report = {"portfolio": {"total_open": 0, "total_unrealized_r": 0.0,
                            "total_unrealized_usd": None, "winners_open": 0,
                            "losers_open": 0, "total_open_risk_pct": 0.0}}
    assert "Today:" in format_summary(report, realized_today={"r": 1.8, "n": 4})
    assert "+1.80R on 4 closed" in format_summary(report, realized_today={"r": 1.8, "n": 4})
    # no closes today -> line omitted
    assert "Today:" not in format_summary(report, realized_today={"r": 0.0, "n": 0})


def test_format_summary_deadline_alert():
    base = {"total_open": 3, "total_unrealized_r": 0.0, "total_unrealized_usd": None,
            "winners_open": 0, "losers_open": 0, "total_open_risk_pct": 3.0}
    trades = [
        {"symbol": "BTCUSDT", "setup": "confluence_r_60pct_tf", "unrealized_r": 0.1,
         "pnl_pct": 0.2, "hours_to_deadline": 40.0},    # far off -> ignored
        {"symbol": "SOLUSDT", "setup": "confluence_r_60pct_tf", "unrealized_r": -0.2,
         "pnl_pct": -0.5, "hours_to_deadline": 2.1},    # expiring soon
        {"symbol": "XRPUSDT", "setup": "confluence_r_60pct_tf", "unrealized_r": 0.0,
         "pnl_pct": 0.0, "hours_to_deadline": -3.0},     # overdue
    ]
    msg = format_summary({"portfolio": base, "trades": trades})
    assert "⏰" in msg
    assert "Expiring: SOLUSDT 2.1h" in msg
    assert "overdue: XRPUSDT" in msg
    assert "BTCUSDT" not in msg.split("⏰")[1]  # far-off trade not in the alert
    # nothing near deadline -> no alert line
    far = [dict(t, hours_to_deadline=50.0) for t in trades]
    assert "⏰" not in format_summary({"portfolio": base, "trades": far})


def test_book_label_buckets():
    assert _book_label("confluence_r_60pct_tf") == "core"
    assert _book_label("confluence_r_60pct_tf_cts") == "trend"
    assert _book_label("confluence_r_60pct_tf_lo") == "longs"
    assert _book_label("confluence_r_60pct_tradfi") == "tradfi"
    assert _book_label(None) == "core"


def test_realized_today_sums_fee_net_closes_since_asia_open():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    today_iso = now.isoformat()
    old_iso = now.replace(year=now.year - 1).isoformat()
    preds = [
        _pred(status="hit", outcome_r=3.0),    # resolved now -> counts
        _pred(status="miss", outcome_r=-1.0),  # resolved now -> counts
        _pred(status="open"),                  # still open -> ignored
    ]
    preds[0].resolved_at = today_iso
    preds[1].resolved_at = today_iso
    out = _realized_today(preds)
    assert out["n"] == 2
    # fee-net, so strictly less than the gross 3.0 + (-1.0) = 2.0
    assert out["r"] < 2.0
    # a close dated last year is excluded
    preds[1].resolved_at = old_iso
    assert _realized_today(preds)["n"] == 1


def test_realized_today_rolls_at_ny_open_not_utc_midnight():
    # The day boundary is the most recent New York open (08:00 NY), not UTC midnight:
    # a close 1 min BEFORE that instant is excluded, 1 min AFTER included.
    from datetime import timedelta
    from kudbee_quant.context.calendar import session_day_start
    start = session_day_start()
    before = _pred(status="hit", outcome_r=2.0)
    after = _pred(status="hit", outcome_r=2.0)
    before.resolved_at = (start - timedelta(minutes=1)).isoformat()
    after.resolved_at = (start + timedelta(minutes=1)).isoformat()
    out = _realized_today([before, after])
    assert out["n"] == 1                        # only the post-Asia-open close counts


def test_notify_summary_only_if_open(monkeypatch):
    import types
    import kudbee_quant.notifications.notify as nt
    monkeypatch.setattr(nt, "telegram_enabled", lambda: True)
    sent = []
    monkeypatch.setattr(nt, "send_telegram", lambda msg: sent.append(msg) or True)
    monkeypatch.setattr("kudbee_quant.journal.TradeJournal",
                        lambda *a, **k: types.SimpleNamespace(predictions=[], venue_record=lambda: {}))

    # flat -> silent (no send) under only_if_open
    monkeypatch.setattr("kudbee_quant.review.open_trades_report",
                        lambda **k: {"portfolio": {"total_open": 0}, "trades": []})
    assert nt.notify_summary(only_if_open=True) is False
    assert sent == []

    # holding positions -> it pings
    monkeypatch.setattr("kudbee_quant.review.open_trades_report",
                        lambda **k: {"portfolio": {"total_open": 2, "total_unrealized_r": 0.3,
                                                   "total_unrealized_usd": None, "winners_open": 1,
                                                   "losers_open": 1, "total_open_risk_pct": 2.0},
                                     "trades": []})
    assert nt.notify_summary(only_if_open=True) is True
    assert len(sent) == 1


def test_split_long_message():
    chunks = _split("x" * 5000)
    assert len(chunks) >= 2
    assert all(len(c) <= tg._MAX_LEN for c in chunks)
    short = _split("just one line")
    assert short == ["just one line"]
