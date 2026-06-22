"""Tests for the forward-validation scorecard toolkit (no network, synthetic journal)."""
from __future__ import annotations

from types import SimpleNamespace

from kudbee_quant.journal import Prediction
import kudbee_quant.scorecard as sc


def _p(setup, r, *, status="hit", when="2026-06-21T12:00:00+00:00", mode="paper",
       atr=None, entry=100.0):
    return Prediction(symbol="BTCUSDT", kind="bracket", level=entry, deadline_days=3,
                      setup=setup, timeframe="1h", status=status, outcome_r=r,
                      resolved_at=when, entry=entry, stop=entry - 1.0, target=entry + 3.0,
                      direction=1.0, mode=mode, atr_at_entry=atr, filled_at=when)


def _journal(preds):
    return SimpleNamespace(predictions=preds)


def test_book_of_labels():
    assert sc.book_of("confluence_r_60pct_tf") == "core"
    assert sc.book_of("confluence_r_60pct_tf_cts") == "trend(_cts)"
    assert sc.book_of("confluence_r_55pct_tf_lo") == "longs(_lo)"
    assert sc.book_of("confluence_r_60pct_tradfi") == "tradfi"
    assert sc.book_of("bias_scalp_60pct") == "bias"
    assert sc.book_of("my_read") == "human" and sc.book_of("") == "human"


def test_scorecard_groups_by_book_and_verdicts():
    preds = ([_p("confluence_r_60pct_tf", 1.0) for _ in range(35)]      # core: +1R -> KEEP
             + [_p("confluence_r_60pct_tf_cts", -1.0) for _ in range(35)]  # trend: -1R -> REVERT
             + [_p("confluence_r_55pct_tf_lo", 1.0) for _ in range(5)])    # longs: thin -> WAIT
    card = sc.book_scorecard(_journal(preds), mode="paper")
    assert card["books"]["core"]["verdict"] == "KEEP"
    assert card["books"]["core"]["n"] == 35
    assert card["books"]["trend(_cts)"]["verdict"] == "REVERT"
    assert card["books"]["longs(_lo)"]["verdict"] == "WAIT"   # n=5 < 30


def test_net_of_fees_reduces_expectancy_below_gross():
    preds = [_p("confluence_r_60pct_tf", 1.0) for _ in range(40)]
    card = sc.book_scorecard(_journal(preds), mode="paper")
    exp = card["books"]["core"]["expectancy_r"]
    assert 0 < exp < 1.0          # +1R gross, but strictly less after the venue fee
    assert card["books"]["core"]["verdict"] == "KEEP"


def test_since_filter_excludes_old_era():
    preds = ([_p("confluence_r_60pct_tf", -1.0, when="2026-01-01T00:00:00+00:00") for _ in range(50)]
             + [_p("confluence_r_60pct_tf", 1.0, when="2026-06-22T00:00:00+00:00") for _ in range(40)])
    all_time = sc.book_scorecard(_journal(preds), mode="paper")["books"]["core"]
    forward = sc.book_scorecard(_journal(preds), mode="paper", since="2026-06-10")["books"]["core"]
    assert all_time["n"] == 90 and all_time["verdict"] == "REVERT"   # poisoned by old era
    assert forward["n"] == 40 and forward["verdict"] == "KEEP"       # forward window is positive


def test_resolved_on_or_after_includes_same_day():
    # a bare-date `since` must INCLUDE a same-day UTC trade and exclude the day before
    # (locks the lexicographic ISO compare against future timestamp-format drift).
    same = _p("confluence_r_60pct_tf", 1.0, when="2026-06-21T00:00:00+00:00")
    prev = _p("confluence_r_60pct_tf", 1.0, when="2026-06-20T23:59:59+00:00")
    assert sc._resolved_on_or_after(same, "2026-06-21") is True
    assert sc._resolved_on_or_after(prev, "2026-06-21") is False
    assert sc._resolved_on_or_after(same, None) is True


def test_mode_filter():
    preds = [_p("confluence_r_60pct_tf", 1.0, mode="paper") for _ in range(10)] + \
            [_p("confluence_r_60pct_tf", 1.0, mode="live") for _ in range(3)]
    assert sc.book_scorecard(_journal(preds), mode="paper")["overall"]["n"] == 10
    assert sc.book_scorecard(_journal(preds), mode="live")["overall"]["n"] == 3
    assert sc.book_scorecard(_journal(preds), mode=None)["overall"]["n"] == 13


def test_hour_breakdown_flags_toxic():
    # 12 losers all entered at 18:00 UTC -> toxic; 12 winners at 09:00 -> not toxic
    preds = ([_p("confluence_r_60pct_tf", -1.0, when="2026-06-21T18:00:00+00:00") for _ in range(12)]
             + [_p("confluence_r_60pct_tf", 2.0, when="2026-06-21T09:00:00+00:00") for _ in range(12)])
    hb = sc.book_hour_breakdown(_journal(preds), mode="paper", min_n=8)
    assert 18 in hb["toxic_hours"] and 9 not in hb["toxic_hours"]
    assert hb["hours"][18]["toxic"] is True


def test_regime_breakdown_terciles():
    # rising atr_at_entry across 9 trades -> low/mid/high terciles populated
    preds = [_p("confluence_r_60pct_tf", 1.0, atr=a) for a in (0.5, 0.6, 0.7, 1.0, 1.1, 1.2, 2.0, 2.1, 2.2)]
    reg = sc.book_regime_breakdown(_journal(preds), mode="paper")["regimes"]
    assert {"low", "mid", "high"} <= set(reg)
    assert reg["low"]["n"] + reg["mid"]["n"] + reg["high"]["n"] == 9
    assert reg["low"]["n"] >= 3                      # the low-vol tercile holds the smallest ATR%


def test_format_scorecard_and_notify_muted(monkeypatch):
    preds = [_p("confluence_r_60pct_tf", -1.0) for _ in range(35)]
    msg = sc.format_scorecard(sc.book_scorecard(_journal(preds), mode="paper"))
    assert "core" in msg and "REVERT" in msg
    # notify is a no-op (False, never raises) when Telegram is unconfigured
    monkeypatch.setattr(sc, "book_scorecard", lambda *a, **k: {"books": {}, "overall": {}, "wait_min_n": 30})
    import kudbee_quant.notifications as notif
    monkeypatch.setattr(notif, "telegram_enabled", lambda: False)
    assert sc.notify_scorecard(_journal(preds)) is False


def test_write_forward_report(tmp_path):
    preds = [_p("confluence_r_60pct_tf", 1.0, atr=1.0) for _ in range(35)]
    out = tmp_path / "fwd.md"
    text = sc.write_forward_report(out, _journal(preds), mode="paper")
    assert out.exists()
    assert "Forward-validation scorecard" in text and "Per-book verdicts" in text
    assert "core" in text and "KEEP" in text


def test_today_autopsy_groups_and_extremes():
    preds = [_p("confluence_r_60pct_tf", 2.0), _p("confluence_r_60pct_tf", -1.0),
             _p("confluence_r_60pct_tradfi", -1.0), _p("confluence_r_60pct_tf_lo", 0.5)]
    a = sc.today_autopsy(_journal(preds), since="2020-01-01")
    assert a["n"] == 4
    assert a["by_book"]["core"]["n"] == 2 and "tradfi" in a["by_book"] and "longs(_lo)" in a["by_book"]
    assert a["best"][1] > 0 > a["worst"][1]              # a real winner and a real loser
    assert a["best"][0] == "BTCUSDT"                      # the +2R trade is the day's best
