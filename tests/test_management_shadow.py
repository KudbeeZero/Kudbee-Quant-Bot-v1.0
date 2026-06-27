"""Tests for research/management_shadow.py — CI-safe (injected bar fetch, no network).

  (a) load_resolved_validated filters to resolved validated 1h bracket trades only;
  (b) score_trade resolves A/B/C from post-fill bars — a clean +3R long gives
      A (full ride) > B (bank-half blended), proving the geometries differ as
      expected on real-trade inputs;
  (c) score_trade returns None when the fetched bars don't cover the entry;
  (d) run_shadow wires it together over an injected fetch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

import management_shadow as ms  # noqa: E402


def _bars_rising(fill_hour: pd.Timestamp, n: int = 30) -> pd.DataFrame:
    """Hourly bars from the entry bar, rising enough to clear a +3R long target."""
    ts = pd.date_range(fill_hour, periods=n, freq="1h", tz="UTC")
    close = np.linspace(100.0, 110.0, n)        # climbs through 103 (=3R for sd=1)
    high = close + 0.5
    low = close - 0.2                            # never revisits the 99 stop
    return pd.DataFrame({"timestamp": ts, "high": high, "low": low, "close": close})


def _trade(**kw) -> dict:
    base = {"id": "t1", "symbol": "BTCUSDT", "kind": "bracket", "timeframe": "1h",
            "status": "miss", "setup": "confluence_r_50pct_tf",
            "filled_at": "2026-06-09T06:00:00+00:00", "entry": 100.0, "stop": 99.0,
            "target": 103.0, "direction": 1.0, "outcome_r": 3.0}
    base.update(kw)
    return base


# --- (a) filtering ----------------------------------------------------------

def test_load_resolved_validated_filters(tmp_path: Path):
    journal = [
        _trade(id="keep"),                                   # valid
        _trade(id="drop_tf", timeframe="5m"),                # wrong TF
        _trade(id="drop_status", status="pending"),          # not resolved
        _trade(id="drop_setup", setup="my_read"),            # not validated book
        _trade(id="drop_nofill", filled_at=None),            # missing entry time
        {"id": "drop_kind", "kind": "directional"},          # not a bracket
    ]
    p = tmp_path / "j.json"
    p.write_text(json.dumps(journal))
    kept = ms.load_resolved_validated(p)
    assert [t["id"] for t in kept] == ["keep"]


# --- (b) geometry resolution on a real-trade input --------------------------

def test_score_trade_ride_beats_bankhalf_on_clean_winner():
    fill = pd.Timestamp("2026-06-09T06:00:00+00:00")
    bars = _bars_rising(fill)
    row = ms.score_trade(_trade(), bars)
    assert row is not None
    # A rides the full move to ~3R; B banks half at 1R -> blended ~2R; both net of fee
    assert row["net_a"] > row["net_b"] > 0
    assert abs(row["net_a"] - 3.0) < 0.05      # ~+3R minus tiny maker fee
    assert row["side"] == "long"


# --- (c) bars not covering the entry ----------------------------------------

def test_score_trade_returns_none_when_entry_missing():
    # bars start AFTER the fill hour -> entry bar not located
    later = pd.Timestamp("2026-06-10T06:00:00+00:00")
    bars = _bars_rising(later)
    assert ms.score_trade(_trade(filled_at="2026-06-09T06:00:00+00:00"), bars) is None


# --- (d) end-to-end with injected fetch -------------------------------------

def test_run_shadow_scores_via_injected_fetch(tmp_path: Path):
    journal = [_trade(id="a"), _trade(id="b", symbol="ETHUSDT")]
    p = tmp_path / "j.json"
    p.write_text(json.dumps(journal))

    def fake_fetch(symbol, start, end):
        return _bars_rising(pd.Timestamp("2026-06-09T06:00:00+00:00"))

    res = ms.run_shadow(fake_fetch, journal_path=p)
    assert res["n_candidates"] == 2
    assert len(res["rows"]) == 2
    summ = ms.summarize(res["rows"])
    assert summ["geom"]["A ride-3R"]["n"] == 2
    assert summ["deltas"]["A-B"]["mean_delta"] > 0   # A beats B on clean winners
