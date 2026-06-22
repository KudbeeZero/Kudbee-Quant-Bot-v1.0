"""Vector Candle Tracker — persists unrecovered PVSRA climax bars to D1.

An "unrecovered" climax candle is a price magnet:
  - bull_climax body that price has NOT revisited = unfilled demand zone
  - bear_climax body that price has NOT revisited = unfilled supply zone

Updated every scan run:
  1. Upsert new climax candles (INSERT OR IGNORE).
  2. Check all active vectors for recovery against later bars.
  3. Mark recovered ones (active=0, recovery_price, recovered_at).
  4. Update days_open on all still-active vectors.

Recovery definition (within RECOVERY_TOLERANCE = 0.3%):
  bull_climax at candle_low X : recovered when a later bar's LOW  <= X * (1 + tol)
  bear_climax at candle_high Y: recovered when a later bar's HIGH >= Y * (1 - tol)

NEVER touches trading logic — it only reads pvsra_vector_candles() output.
"""
from __future__ import annotations

import math

import pandas as pd

from .d1_client import d1_execute, d1_query

RECOVERY_TOLERANCE = 0.003  # 0.3% — price considered "at" the candle zone


def update_vectors(df: pd.DataFrame, symbol: str, timeframe: str = "1h") -> dict:
    """Process vector candles for a symbol.

    Returns: ``{"new": N, "recovered": N, "still_active": N}``.
    """
    from kudbee_quant.signals.pvsra import pvsra_vector_candles
    vec_df = pvsra_vector_candles(df)

    climax_types = {"bull_climax", "bear_climax"}
    climaxes = vec_df[vec_df["vector"].isin(climax_types)].copy()

    # 1. Upsert new climax candles.
    new_count = 0
    for _, row in climaxes.iterrows():
        result = d1_execute("""
            INSERT OR IGNORE INTO unrecovered_vectors
              (symbol, timeframe, candle_time, candle_type,
               body_open, body_close, candle_high, candle_low, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            symbol, timeframe, str(row["timestamp"]), row["vector"],
            _safe(row["open"]), _safe(row["close"]),
            _safe(row["high"]), _safe(row["low"]),
            _safe(row.get("volume")),
        ])
        if result.get("changes", 0) > 0:
            new_count += 1

    # 2. Check active vectors for recovery against LATER bars.
    active = d1_query("""
        SELECT id, candle_type, candle_high, candle_low, candle_time
        FROM unrecovered_vectors
        WHERE symbol = ? AND timeframe = ? AND active = 1
    """, [symbol, timeframe])

    recovered_count = 0
    for v in active:
        candle_ts = pd.to_datetime(v["candle_time"], utc=True)
        future = vec_df[pd.to_datetime(vec_df["timestamp"], utc=True) > candle_ts]
        if future.empty:
            continue

        if v["candle_type"] == "bull_climax":
            # Recovery = price dips back to the candle-low zone.
            threshold = v["candle_low"] * (1 + RECOVERY_TOLERANCE)
            hits = future[future["low"] <= threshold]
            recovered = not hits.empty
            rec_price = float(hits["low"].min()) if recovered else None
        else:  # bear_climax
            # Recovery = price pops back to the candle-high zone.
            threshold = v["candle_high"] * (1 - RECOVERY_TOLERANCE)
            hits = future[future["high"] >= threshold]
            recovered = not hits.empty
            rec_price = float(hits["high"].max()) if recovered else None

        if recovered:
            rec_bar = str(hits["timestamp"].min())
            d1_execute("""
                UPDATE unrecovered_vectors
                SET active = 0, recovery_price = ?, recovered_at = ?
                WHERE id = ?
            """, [_safe(rec_price), rec_bar, v["id"]])
            recovered_count += 1

    # 3. Update days_open on all still-active vectors for this symbol.
    today = str(vec_df.iloc[-1]["timestamp"])[:10]
    d1_execute("""
        UPDATE unrecovered_vectors
        SET days_open = CAST(
            (julianday(?) - julianday(substr(candle_time, 1, 10))) AS INTEGER
        )
        WHERE symbol = ? AND timeframe = ? AND active = 1
    """, [today, symbol, timeframe])

    still_active = d1_query("""
        SELECT COUNT(*) AS n FROM unrecovered_vectors
        WHERE symbol = ? AND timeframe = ? AND active = 1
    """, [symbol, timeframe])

    return {
        "new": new_count,
        "recovered": recovered_count,
        "still_active": still_active[0]["n"] if still_active else 0,
    }


def _safe(val):
    """Convert numpy types and NaN to a Python native value or None."""
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, np.generic):
            val = val.item()
    except Exception:  # noqa: BLE001
        pass
    if isinstance(val, float) and math.isnan(val):
        return None
    return val
