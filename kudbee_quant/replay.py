"""Replay a journal trade through the confluence stack, bar by bar (read-only).

The journal stores the final confluence pct of a trade but not WHICH factors
voted — so replay recomputes build_levels + factor_votes over the trade's
window from current exchange data. That makes it honest-but-approximate:

* warmup is pinned to 600 bars before the window (the live scan's exact
  context, paper.py) so indicators match what the scan COULD have seen, but
* the data itself is re-fetched today, and the taint audit proved live-edge
  conditions don't always reproduce (3 pre-fix TradFi entries were
  NOT_REPRODUCED; pre-fix filled_at timestamps are unreliable — MEMORY §29/§31).

Never writes: the journal is loaded, searched, and left untouched.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

import pandas as pd

from .confluence.trace import factor_trace
from .ingest import RouterClient
from .journal import Prediction, TradeJournal
from .levels import build_levels
from .paper.paper import _INTERVAL_MIN

WARMUP_BARS = 600     # same history depth the live scan feeds build_levels
LEAD_IN_BARS = 12     # visual run-up before the signal bar
MAX_FETCH_BARS = 4000  # replay age cap (1h -> ~166 days back)

REPLAY_CAVEAT = (
    "Recomputed from CURRENT exchange data with the live scan's 600-bar warmup — "
    "indicator values can differ from what the scan saw at the live edge. Known: "
    "3 pre-fix TradFi entries were NOT_REPRODUCED in the taint audit, and pre-fix "
    "filled_at timestamps (<= 2026-06-10) are unreliable as fill times."
)

_ID_RE = re.compile(r"^[0-9a-f]{8}$")


class ReplayUnsupported(ValueError):
    """Trade exists but can't be replayed (non-bracket kind)."""


class ReplayTooOld(ValueError):
    """Trade window + warmup exceeds the fetchable history."""


def find_trade(trade_id: str, journal: TradeJournal | None = None) -> Prediction:
    """Read-only lookup by id; ValueError on bad format, KeyError if absent."""
    if not _ID_RE.match(trade_id or ""):
        raise ValueError("invalid trade id (expected 8 hex chars)")
    j = journal or TradeJournal()
    for p in j.predictions:
        if p.id == trade_id:
            return p
    raise KeyError(trade_id)


def _utc(ts: str) -> datetime:
    """Parse journal timestamps (isoformat or pandas str) to aware UTC."""
    t = pd.Timestamp(ts)
    return (t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")).to_pydatetime()


def replay_trade(trade_id: str, *, journal: TradeJournal | None = None,
                 client: RouterClient | None = None) -> dict:
    p = find_trade(trade_id, journal=journal)
    if p.kind != "bracket":
        raise ReplayUnsupported("only bracket trades are replayable")

    interval = p.timeframe or "1h"
    bar_min = _INTERVAL_MIN.get(interval, 60)
    created = _utc(p.created_at)
    window_end = _utc(p.resolved_at) if p.resolved_at else datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    bars_since = max(int(math.ceil((now - created).total_seconds() / 60.0 / bar_min)), 1)
    need = bars_since + WARMUP_BARS + LEAD_IN_BARS + 5
    if need > MAX_FETCH_BARS:
        raise ReplayTooOld(
            f"trade is too old to replay: needs ~{need} {interval} bars of history "
            f"(cap {MAX_FETCH_BARS}); the exchange feed can't reach back that far honestly")

    df = (client or RouterClient()).klines(p.symbol, interval=interval, limit=need)
    levels = build_levels(df)
    ts = pd.to_datetime(levels["timestamp"], utc=True)

    in_window = (ts <= pd.Timestamp(window_end)) & (ts >= pd.Timestamp(created))
    window_pos = list(levels.index[in_window])
    if not window_pos:
        raise ReplayTooOld("no completed bars between the trade's creation and resolution "
                           "in the fetched history — nothing to replay")
    lead_pos = list(levels.index[ts < pd.Timestamp(created)])[-LEAD_IN_BARS:]
    idx = lead_pos + window_pos

    bars = factor_trace(levels, indices=idx)
    n_pre = len(lead_pos)
    for i, row in enumerate(bars):
        row["pre"] = i < n_pre   # lead-in bar, before the signal

    events: dict[int, list[str]] = {}

    def _mark(when: str | None, label: str) -> None:
        if not when:
            return
        t = pd.Timestamp(_utc(when))
        sel = [k for k, pos in enumerate(idx) if ts.loc[pos] >= t]
        # Event time can postdate the last bar (wall-clock resolution stamps).
        k = sel[0] if sel else len(idx) - 1
        events.setdefault(k, []).append(label)

    _mark(p.created_at, "SIGNAL")
    _mark(p.filled_at, f"FILLED {p.entry:g}" if p.entry is not None else "FILLED")
    _mark(p.tp1_filled_at, "TP1 BANKED")
    if p.resolved_at:
        r = f" {p.outcome_r:+g}R" if p.outcome_r is not None else ""
        _mark(p.resolved_at, f"RESOLVED {p.status.upper()}{r}")

    return {
        "trade": {
            "id": p.id, "symbol": p.symbol, "timeframe": interval,
            "direction": p.direction, "entry": p.entry, "stop": p.stop,
            "target": p.target, "target_r": p.target_r, "tp1": p.tp1,
            "status": p.status, "outcome_r": p.outcome_r, "source": p.source,
            "setup": p.setup, "note": p.note, "created_at": p.created_at,
            "filled_at": p.filled_at, "resolved_at": p.resolved_at,
        },
        "bars": bars,
        "events": {str(k): v for k, v in sorted(events.items())},
        "caveat": REPLAY_CAVEAT,
    }
