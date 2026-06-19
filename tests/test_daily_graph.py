"""Tests for the daily trade graph (last-24h SVG + summary). No network:
``daily_graph_report`` runs with excursions off, so the journal client is
never called."""
import xml.dom.minidom as minidom
from datetime import datetime, timedelta, timezone

from kudbee_quant.daily_graph import (
    daily_graph_report,
    render_daily_svg,
    render_daily_text,
)
from kudbee_quant.journal import Prediction, TradeJournal

_END = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)


def _resolved(symbol, hours_before_end, outcome_r, *, entry=100.0, stop=99.0):
    """A resolved bracket trade whose resolved_at is `hours_before_end` before _END."""
    when = _END - timedelta(hours=hours_before_end)
    p = Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                   entry=entry, stop=stop, target=entry + 3 * (entry - stop),
                   direction=1.0, target_r=3.0,
                   status="hit" if outcome_r > 0 else "miss", outcome_r=outcome_r)
    p.created_at = (when - timedelta(hours=1)).isoformat()
    p.filled_at = (when - timedelta(hours=1)).isoformat()
    p.resolved_at = when.isoformat()
    return p


def _open(symbol, hours_before_end):
    when = _END - timedelta(hours=hours_before_end)
    p = Prediction(symbol=symbol, kind="bracket", level=100.0, deadline_days=7,
                   entry=100.0, stop=99.0, target=103.0, direction=1.0,
                   target_r=3.0, status="open")
    p.created_at = when.isoformat()
    p.filled_at = when.isoformat()
    return p


def _journal(tmp_path, preds):
    j = TradeJournal(path=tmp_path / "j.json")
    j.predictions = preds
    return j


def _report(tmp_path, preds, **kw):
    return daily_graph_report(_journal(tmp_path, preds), end=_END.isoformat(), **kw)


def test_empty_window(tmp_path):
    # A trade resolved 5 days ago is outside the 24h window.
    rep = _report(tmp_path, [_resolved("BTCUSDT", 24 * 5, +3.0)])
    assert rep["window"]["n_resolved"] == 0
    assert rep["points"] == []
    assert rep["window"]["net_total_r"] == 0.0
    assert "no resolved trades" in render_daily_text(rep).lower()
    # SVG still renders (with the empty-state message) and is well-formed XML.
    minidom.parseString(render_daily_svg(rep))


def test_window_selection_and_cumulative(tmp_path):
    preds = [
        _resolved("BTCUSDT", 20, +2.0),   # in window, earliest
        _resolved("ETHUSDT", 10, -1.0),   # in window
        _resolved("SOLUSDT", 2, +1.0),    # in window, latest
        _resolved("OLDUSDT", 48, +5.0),   # outside (2 days before end)
    ]
    rep = _report(tmp_path, preds)
    assert rep["window"]["n_resolved"] == 3
    syms = [p["symbol"] for p in rep["points"]]
    assert syms == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # time-ordered
    cums = [p["cum_net_r"] for p in rep["points"]]
    # monotone-cumulative in trade order; OLDUSDT's +5R must NOT appear
    assert cums[0] < cums[1] or cums[2] > cums[1]
    assert all(c < 5.0 for c in cums)
    # net total equals the last cumulative point
    assert rep["window"]["net_total_r"] == cums[-1]
    # win flags follow the sign of realized R
    assert [p["win"] for p in rep["points"]] == [True, False, True]


def test_net_is_below_gross_on_crypto(tmp_path):
    # Crypto pays the taker fee, so cumulative NET R < gross total R.
    rep = _report(tmp_path, [_resolved("BTCUSDT", 5, +3.0)])
    assert rep["window"]["net_total_r"] < rep["portfolio"]["total_r"]


def test_open_in_window_counted(tmp_path):
    preds = [_resolved("BTCUSDT", 5, +1.0), _open("ETHUSDT", 3), _open("SOLUSDT", 48)]
    rep = _report(tmp_path, preds)
    assert rep["window"]["n_open_in_window"] == 1   # SOLUSDT opened outside the window


def test_svg_has_one_dot_per_trade(tmp_path):
    preds = [_resolved("BTCUSDT", 20, +2.0), _resolved("ETHUSDT", 10, -1.0)]
    svg = render_daily_svg(_report(tmp_path, preds))
    doc = minidom.parseString(svg)          # well-formed
    assert len(doc.getElementsByTagName("circle")) == 2
    assert svg.startswith("<svg")


def test_mode_filter(tmp_path):
    live = _resolved("BTCUSDT", 5, +1.0)
    live.mode = "live"
    rep = _report(tmp_path, [live, _resolved("ETHUSDT", 5, +1.0)], mode="live")
    assert rep["window"]["n_resolved"] == 1
    assert rep["points"][0]["symbol"] == "BTCUSDT"
