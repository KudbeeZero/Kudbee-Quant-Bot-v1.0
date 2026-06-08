"""Event detectors — mechanical, no-lookahead definitions of 'something happened'.

Each detector returns the input frame with added boolean/int event columns, so
events stay aligned to bars and can be joined with context features and
forward outcomes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_vector_events(df: pd.DataFrame) -> pd.DataFrame:
    """Flag PVSRA climax (vector) candles and record their zone.

    Requires the 'vector' column from pvsra_vector_candles. Adds:
      is_vector (bool), vector_dir (+1 bull / -1 bear / 0),
      zone_low, zone_high, zone_mid (the candle's price box).
    """
    if "vector" not in df.columns:
        raise ValueError("detect_vector_events needs the 'vector' column (run build_features)")
    out = df.copy()
    is_climax = out["vector"].isin(["bull_climax", "bear_climax"])
    out["is_vector"] = is_climax
    out["vector_dir"] = np.where(out["vector"] == "bull_climax", 1,
                                 np.where(out["vector"] == "bear_climax", -1, 0))
    out["zone_low"] = out["low"].where(is_climax)
    out["zone_high"] = out["high"].where(is_climax)
    out["zone_mid"] = (out["zone_low"] + out["zone_high"]) / 2.0
    return out


def detect_level_tests(
    df: pd.DataFrame,
    level_col: str,
    group_col: str = "ny_date",
    eps_atr: float = 0.05,
) -> pd.DataFrame:
    """Detect fresh touches of a price level and number them (1st, 2nd, ...).

    A 'test' is a bar whose range contains the level (within eps_atr*ATR),
    where the *previous* bar did not — so a fresh approach counts once, not
    once per bar resting on the level. The counter resets within each
    ``group_col`` group (e.g. per NY date for the daily open).

    Adds columns: f"{level_col}_test" (bool), f"{level_col}_nth_test" (int,
    0 where no test).
    """
    for col in (level_col, group_col, "atr", "high", "low"):
        if col not in df.columns:
            raise ValueError(f"detect_level_tests requires column {col!r}")
    out = df.copy()
    level = out[level_col]
    band = (out["atr"] * eps_atr).fillna(0.0)
    contains = (out["high"] >= level - band) & (out["low"] <= level + band) & level.notna()
    fresh = contains & ~contains.shift(1, fill_value=False)

    test_col, nth_col = f"{level_col}_test", f"{level_col}_nth_test"
    out[test_col] = fresh
    out[nth_col] = fresh.groupby(out[group_col]).cumsum().where(fresh, 0).astype(int)
    return out
