"""Level Recorder — persists build_levels() output to Cloudflare D1.

Called after every paper-scan run. One row per (date, symbol, timeframe).
Uses INSERT OR REPLACE so re-running the same hour is idempotent (the UNIQUE
constraint on (date, symbol, timeframe) is the dedup key).

This NEVER mutates the frame and NEVER touches trading logic — it reads the last
bar's columns and writes them out.
"""
from __future__ import annotations

import math

import pandas as pd

from .d1_client import d1_execute

# build_levels() column name == D1 column name. This explicit allowlist is the
# contract: only these fields are persisted, in this order.
LEVEL_FIELDS = [
    "mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5",
    "pivot_pp", "pivot_r1", "pivot_r2", "pivot_r3",
    "pivot_s1", "pivot_s2", "pivot_s3",
    "daily_open", "weekly_open", "monthly_open",
    "pdh", "pdl", "pwh", "pwl", "prev_day_color",
    "asian_high", "asian_low", "asian_open", "ny_open",
    "prior_ny_high", "prior_ny_low",
    "brinks_high", "brinks_low", "ny_brinks_high", "ny_brinks_low",
    "adr", "adr_high", "adr_low",
    "awr", "awr_high", "awr_low",
    "amr", "amr_high", "amr_low",
    "round_above", "round_below",
    "ema_5", "ema_13", "ema_50", "ema_200", "ema_800", "ema_cloud_pos",
    "week_ib_high", "week_ib_low",
    "pct_adr_used", "pct_awr_used",
    "day_of_week", "level_day",
]


def record_levels(df: pd.DataFrame, symbol: str, timeframe: str = "1h") -> None:
    """Write the last bar's TR levels to D1. Idempotent per (date, symbol, timeframe)."""
    last = df.iloc[-1]
    recorded_at = str(last["timestamp"])
    date = str(last.get("ny_date", recorded_at[:10]))

    values = [_safe(last.get(field)) for field in LEVEL_FIELDS]

    cols = ["recorded_at", "date", "symbol", "timeframe"] + LEVEL_FIELDS
    col_names = ", ".join(cols)
    placeholders = ", ".join("?" for _ in cols)
    params = [recorded_at, date, symbol, timeframe] + values

    sql = f"""
        INSERT OR REPLACE INTO daily_levels ({col_names})
        VALUES ({placeholders})
    """
    d1_execute(sql, params)


def _safe(val):
    """Convert numpy types and NaN to a Python native value or None."""
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, np.generic):
            val = val.item()
    except Exception:  # noqa: BLE001 — numpy optional / odd dtypes
        pass
    if isinstance(val, float) and math.isnan(val):
        return None
    return val
