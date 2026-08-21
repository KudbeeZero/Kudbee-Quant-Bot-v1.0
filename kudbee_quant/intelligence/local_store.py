"""Local-JSON intelligence store — a working fallback for the D1 recorders.

``intelligence/level_recorder.py`` and ``intelligence/vector_tracker.py`` were built
to persist to Cloudflare D1, but D1 was **never provisioned** (CROSSROADS X2 /
MEMORY §67): ``wrangler.toml`` still has ``database_id = "REPLACE_WITH_DATABASE_ID"``.
So those recorders have been silent no-ops and the Telegram ``/levels`` ``/history``
``/vectors`` commands query an empty D1 and always answer "no data".

This module persists the SAME engine output to local, git-ignored JSON
(``data/levels_snapshot.json``) every scan, and serves it back read-only. It is:
  * sourced straight from ``build_levels()`` / ``pvsra_vector_candles()`` (the real
    engine, so the data is accurate, not a copy),
  * write-only from the scan path and read-only from the command path, so it never
    touches trading logic or the validated core,
  * atomic on write and tolerant on read (a missing/corrupt file => empty, not a crash),
  * a strict superset of the D1 columns, so if D1 is later provisioned the two can be
    reconciled field-for-field.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .level_recorder import LEVEL_FIELDS

log = logging.getLogger(__name__)

LEVELS_SNAPSHOT = Path("data/levels_snapshot.json")
VECTORS_SNAPSHOT = Path("data/vectors_snapshot.json")

_LEVEL_KEYS = set(LEVEL_FIELDS)


def _atomic_write(path: Path, obj) -> None:
    """Temp-file + atomic replace, mirroring TradeJournal.save (crash-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(path)


def _safe(val):
    """JSON-coerce a scalar (NaN/inf -> None, numpy -> python)."""
    try:
        if val is None:
            return None
        f = float(val)
        if pd.isna(f) or f != f:  # NaN
            return None
        if f in (float("inf"), float("-inf")):
            return None
        return f
    except (TypeError, ValueError):
        return None


# ── LEVELS ───────────────────────────────────────────────────────────────────

def persist_levels(df: pd.DataFrame, symbol: str, timeframe: str = "1h") -> None:
    """Append/replace the last bar's TR levels for (symbol, timeframe).

    Called once per symbol per scan from ``paper_scan`` (wrapped in try/except there,
    so any failure here can never affect the trading scan). Idempotent per
    (symbol, timeframe): a re-run of the same hour replaces the prior row.
    """
    if df is None or len(df) == 0:
        return
    last = df.iloc[-1]
    recorded_at = str(last.get("timestamp", datetime.now(timezone.utc).isoformat()))
    date = str(last.get("ny_date", recorded_at[:10]))
    row = {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "recorded_at": recorded_at,
        "date": date,
    }
    for field in LEVEL_FIELDS:
        row[field] = _safe(last.get(field))
    # Load-and-merge so we keep history per (symbol, timeframe, date).
    store = _load_store(LEVELS_SNAPSHOT)
    key = f"{symbol.upper()}:{timeframe}"
    history = store.get(key, [])
    history = [r for r in history if r.get("date") != date]  # one row per date
    history.append(row)
    history.sort(key=lambda r: r.get("recorded_at", ""))
    store[key] = history[-60:]  # keep last ~60 sessions, bounded file
    _atomic_write(LEVELS_SNAPSHOT, {"schema_version": 1,
                                    "generated_at": datetime.now(timezone.utc).isoformat(),
                                    "data": store})


def get_levels(symbol: str, timeframe: str = "1h") -> list[dict]:
    """All stored level rows for (symbol, timeframe), newest last."""
    store = _load_store(LEVELS_SNAPSHOT)
    return store.get(f"{symbol.upper()}:{timeframe}", [])


def get_levels_latest(symbol: str, timeframe: str = "1h") -> dict | None:
    rows = get_levels(symbol, timeframe)
    return rows[-1] if rows else None


# ── VECTORS ──────────────────────────────────────────────────────────────────

def persist_vectors(vec_df: pd.DataFrame, symbol: str, timeframe: str = "1h",
                    recovered: list[dict] | None = None) -> None:
    """Persist the latest unrecovered PVSRA climax candles for (symbol, timeframe)."""
    if vec_df is None or len(vec_df) == 0:
        return
    from .vector_tracker import RECOVERY_TOLERANCE
    climax_types = {"bull_climax", "bear_climax"}
    rows = []
    for _, r in vec_df[vec_df["vector"].isin(climax_types)].iterrows():
        rows.append({
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "candle_type": r.get("vector"),
            "candle_high": _safe(r.get("candle_high")),
            "candle_low": _safe(r.get("candle_low")),
            "body_close": _safe(r.get("body_close")),
            "candle_time": str(r.get("timestamp", "")),
            "days_open": _safe(r.get("days_open")),
            "recovered": bool(r.get("recovered", False)),
        })
    store = _load_store(VECTORS_SNAPSHOT)
    key = f"{symbol.upper()}:{timeframe}"
    store[key] = rows[:50]
    _atomic_write(VECTORS_SNAPSHOT, {"schema_version": 1,
                                     "generated_at": datetime.now(timezone.utc).isoformat(),
                                     "data": store})


def get_vectors(symbol: str, timeframe: str = "1h") -> list[dict]:
    store = _load_store(VECTORS_SNAPSHOT)
    return store.get(f"{symbol.upper()}:{timeframe}", [])


# ── shared load ──────────────────────────────────────────────────────────────

def _load_store(path: Path) -> dict:
    """Tolerant load: missing file => {}; corrupt JSON => {} + a warning."""
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text())
        return doc.get("data", {}) if isinstance(doc, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        log.warning("local_store: could not read %s (%s) — starting empty", path, e)
        return {}
