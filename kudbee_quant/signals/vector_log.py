"""Vector-candle logger — track WHERE and WHEN PVSRA climax candles form.

Motivation (user, 2026-06-14): a climax/"vector" candle can print on a low
timeframe and be gone before the hourly scan ever sees it ("missing entries
because of time"). This module is the LOGGING + CONTEXT half of the answer: detect
vector candles (reusing `signals/pvsra.py`), tag each with the chart location it
formed at (which structural level, how far in ATR) and the multi-factor confluence
snapshot at that bar, and append them to a dedicated log so we can study, later and
honestly, whether climax candles at certain levels/times actually precede moves.

HONESTY (carried from pvsra.py): a vector candle marks where volume showed up — a
hypothesis about intent, not a trade signal. This module only RECORDS; the study
half (`vector_study.py`) measures whether it predicts anything, and §37 still says
trading 1m/5m is fee-poisoned. Log first, validate, then maybe trade.

The log is `data/vector_log.json` — a NEW research artifact, NOT the bot-owned
`data/journal.json` and NOT `data/alert_inbox/`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from ..confluence.stack import confluence_score
from ..ingest import RouterClient
from ..levels import build_levels
from .pvsra import pvsra_vector_candles

DEFAULT_LOG = Path("data/vector_log.json")

# Structural levels a candle can form "at", in priority/labeling order. Each is a
# column produced by build_levels; distance is measured from the candle close in
# ATR units, and the nearest within ATR_NEAR is the candle's location tag.
_LEVELS = [
    ("daily_open", "daily_open"),
    ("vwap", "vwap"),
    ("pivot_pp", "pivot_pp"),
    ("pivot_r1", "pivot_r1"), ("pivot_s1", "pivot_s1"),
    ("pivot_r2", "pivot_r2"), ("pivot_s2", "pivot_s2"),
    ("dealing_mid", "dealing_mid"),
    ("ema_50", "ema_50"), ("ema_200", "ema_200"), ("ema_800", "ema_800"),
]
ATR_NEAR = 0.5   # within this many ATR of a level => "formed at" that level


@dataclass
class VectorEvent:
    symbol: str
    timeframe: str
    timestamp: str
    vector: str                 # bull_climax | bear_climax (climax only here)
    close: float
    vol_ratio: float            # volume / rolling-avg volume (how big the climax)
    level: str                  # nearest structural level, or "open_space"
    level_dist_atr: float       # distance from close to that level, in ATR
    confluence_pct: float       # multi-factor agreement at the bar (0..1)
    confluence_dir: float       # +1 long / -1 short / 0
    agree: bool                 # does the climax color agree with confluence dir?

    def key(self) -> tuple:
        return (self.symbol, self.timeframe, self.timestamp)


def _nearest_level(row: pd.Series, atr: float) -> tuple[str, float]:
    """Nearest named level to the bar close, in ATR units."""
    if atr <= 0:
        return ("open_space", float("inf"))
    best_name, best_dist = "open_space", float("inf")
    close = float(row["close"])
    for name, col in _LEVELS:
        val = row.get(col)
        if val is None or pd.isna(val):
            continue
        dist = abs(close - float(val)) / atr
        if dist < best_dist:
            best_name, best_dist = name, dist
    if best_dist > ATR_NEAR:
        return ("open_space", best_dist)
    return (best_name, best_dist)


def detect_vector_events(df: pd.DataFrame, symbol: str, timeframe: str,
                         *, last_only: bool = False) -> list[VectorEvent]:
    """Find CLIMAX vector candles in an OHLCV frame, each tagged with the level it
    formed at and the confluence snapshot at that bar.

    ``last_only`` returns just the most-recent bar if it is a climax (the live
    "did a vector candle just print?" check); otherwise returns every climax in
    the frame (the historical pass).
    """
    # Ensure structural levels (build_levels) + the confluence snapshot + the PVSRA
    # vector class are all present; each helper copies and adds columns, so one
    # chained frame carries level context, confluence_pct/direction, and `vector`.
    base = df if "daily_open" in df.columns else build_levels(df)
    work = confluence_score(pvsra_vector_candles(base))
    rows = work.reset_index(drop=True)
    idxs = [len(rows) - 1] if last_only else range(len(rows))
    out: list[VectorEvent] = []
    for i in idxs:
        r = rows.iloc[i]
        vec = str(r.get("vector", "neutral"))
        if vec not in ("bull_climax", "bear_climax"):
            continue
        atr = float(r.get("atr", 0.0) or 0.0)
        level, dist = _nearest_level(r, atr)
        avg_v = float(r.get("avg_volume", 0.0) or 0.0)
        vol_ratio = (float(r["volume"]) / avg_v) if avg_v > 0 else 0.0
        cdir = float(r.get("direction", 0.0) or 0.0)
        cpct = float(r.get("confluence_pct", 0.0) or 0.0)
        climax_dir = 1.0 if vec == "bull_climax" else -1.0
        out.append(VectorEvent(
            symbol=symbol, timeframe=timeframe, timestamp=str(r["timestamp"]),
            vector=vec, close=float(r["close"]), vol_ratio=round(vol_ratio, 2),
            level=level, level_dist_atr=round(dist, 3) if dist != float("inf") else -1.0,
            confluence_pct=round(cpct, 3), confluence_dir=cdir,
            agree=bool(climax_dir == cdir and cdir != 0.0),
        ))
    return out


def scan_and_log(symbols: list[str], intervals: list[str],
                 client: RouterClient | None = None, path: Path | str = DEFAULT_LOG,
                 limit: int = 300, last_only: bool = True) -> list[VectorEvent]:
    """Scan symbols x intervals for vector candles and APPEND new ones to the log.

    Deduplicates by (symbol, timeframe, timestamp) so re-runs don't double-log.
    Returns the newly-added events.
    """
    client = client or RouterClient()
    path = Path(path)
    existing = json.loads(path.read_text()) if path.exists() else []
    seen = {(e["symbol"], e["timeframe"], e["timestamp"]) for e in existing}

    new: list[VectorEvent] = []
    for interval in intervals:
        for sym in symbols:
            try:
                df = build_levels(client.klines(sym, interval=interval, limit=limit))
                events = detect_vector_events(df, sym, interval, last_only=last_only)
            except Exception:
                continue   # one bad symbol must not sink the scan
            for ev in events:
                if ev.key() not in seen:
                    new.append(ev)
                    seen.add(ev.key())
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing + [asdict(e) for e in new], indent=2))
    return new
