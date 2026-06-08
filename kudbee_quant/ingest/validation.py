"""Validation at the ingestion boundary — never trust external data raw.

Market data arrives as untrusted JSON/CSV from public APIs. Before anything
downstream relies on it we enforce a strict schema and sanity bounds, so a
malformed or hostile payload becomes a clean error instead of silently
corrupting a backtest (garbage in, confident-but-wrong out).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_OHLCV = ["open", "high", "low", "close", "volume"]


def validate_ohlcv(df: pd.DataFrame, *, symbol: str = "?", drop_bad: bool = True) -> pd.DataFrame:
    """Validate and lightly sanitize an OHLCV frame.

    Checks: required columns present; timestamp tz-aware UTC, strictly
    increasing and unique; prices finite and > 0; volume finite and >= 0;
    high >= max(open, close) and low <= min(open, close). Rows that violate
    price/volume sanity are dropped (``drop_bad``) or raise.

    Raises ValueError on structural problems (missing columns, no timestamp,
    empty after cleaning).
    """
    if df is None or len(df) == 0:
        raise ValueError(f"[{symbol}] empty OHLCV frame")
    missing = [c for c in (["timestamp"] + _OHLCV) if c not in df.columns]
    if missing:
        raise ValueError(f"[{symbol}] missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    if out["timestamp"].isna().any():
        raise ValueError(f"[{symbol}] unparseable timestamps present")

    out = out.sort_values("timestamp")
    dup = out["timestamp"].duplicated()
    if dup.any():
        out = out[~dup]  # keep first; duplicate bars corrupt returns

    for c in _OHLCV:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    finite = np.isfinite(out[_OHLCV].to_numpy()).all(axis=1)
    prices_pos = (out[["open", "high", "low", "close"]] > 0).all(axis=1)
    vol_ok = out["volume"] >= 0
    hi_ok = out["high"] >= out[["open", "close"]].max(axis=1) - 1e-9
    lo_ok = out["low"] <= out[["open", "close"]].min(axis=1) + 1e-9
    good = finite & prices_pos & vol_ok & hi_ok & lo_ok

    if not good.all():
        if not drop_bad:
            raise ValueError(f"[{symbol}] {int((~good).sum())} invalid OHLCV rows")
        out = out[good]

    if len(out) == 0:
        raise ValueError(f"[{symbol}] no valid rows after validation")
    return out.reset_index(drop=True)
