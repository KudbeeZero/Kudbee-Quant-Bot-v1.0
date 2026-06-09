"""Double-top / double-bottom NECKLINE-BREAK setups + support/resistance.

The "Project Syndicate" pattern philosophy, mechanized HONESTLY. The validated
finding (docs/MEMORY.md §11) is that FADING equal highs/lows barely beats the
null (+0.046R) but WAITING for the NECKLINE BREAK is a real edge (+0.181R, 75%
of windows positive). The confirmation/execution is the edge — not the shape.
So this module trades the break, not the touch.

Definitions (all causal — swings are known only ``right`` bars later, the break
is a CLOSE through the neckline, so there is no lookahead):
  Double top (M): two consecutive confirmed swing highs within ``tol_atr`` of
    each other (a "double top" / equal highs = a liquidity pool), separated by a
    swing low = the NECKLINE. A bar that CLOSES below that neckline confirms the
    top and triggers a SHORT.
  Double bottom (W): mirror — two equal-ish swing lows, neckline = the swing
    high between them; a CLOSE above it triggers a LONG.

``support_resistance`` exposes the live S/R map (nearest confirmed swing
high/low and any equal-high/low liquidity shelves) for context and for siting
stops/targets at structure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import swing_pivots


def double_top_bottom_break(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3,
    tol_atr: float = 0.5,
    max_gap: int = 60,
) -> pd.Series:
    """{-1,0,+1} at bars that CLOSE through a double-top/bottom neckline.

    Args:
        left/right: swing-confirmation window (3/3 = the classic 3-candle pivot).
        tol_atr: how close the two highs (or lows) must be to count as "equal",
            in ATR units. Larger = looser double-top match.
        max_gap: max bars between the two equal swings (a stale pattern decays).
    Returns a signal Series aligned to ``df`` (0 except on break bars).
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"double_top_bottom_break needs {sorted(need)}")
    p = swing_pivots(df, left=left, right=right)
    n = len(df)
    close = df["close"].to_numpy()
    atr = df["atr"].to_numpy()
    new_sh = p["new_swing_high"].to_numpy()
    new_sl = p["new_swing_low"].to_numpy()

    # Collect confirmed swing highs/lows as (bar_index, price).
    sh_idx = [(i, new_sh[i]) for i in range(n) if np.isfinite(new_sh[i])]
    sl_idx = [(i, new_sl[i]) for i in range(n) if np.isfinite(new_sl[i])]

    sig = np.zeros(n)

    # --- Double TOP -> short on a close below the intervening swing low. ---
    for a, b in zip(sh_idx, sh_idx[1:]):
        (i1, h1), (i2, h2) = a, b
        if i2 - i1 > max_gap:
            continue
        tol = tol_atr * atr[i2]
        if not np.isfinite(tol) or abs(h2 - h1) > tol:
            continue                                  # not an equal-highs double top
        # Neckline = lowest confirmed swing low between the two tops.
        necks = [pr for (j, pr) in sl_idx if i1 < j < i2 and np.isfinite(pr)]
        if not necks:
            continue
        neck = min(necks)
        # First bar AFTER the second top whose CLOSE breaks below the neckline.
        for k in range(i2 + 1, min(i2 + max_gap, n)):
            if close[k] < neck:
                sig[k] = -1.0
                break
            if close[k] > max(h1, h2):                # invalidated (made new high)
                break

    # --- Double BOTTOM -> long on a close above the intervening swing high. ---
    for a, b in zip(sl_idx, sl_idx[1:]):
        (i1, l1), (i2, l2) = a, b
        if i2 - i1 > max_gap:
            continue
        tol = tol_atr * atr[i2]
        if not np.isfinite(tol) or abs(l2 - l1) > tol:
            continue
        necks = [pr for (j, pr) in sh_idx if i1 < j < i2 and np.isfinite(pr)]
        if not necks:
            continue
        neck = max(necks)
        for k in range(i2 + 1, min(i2 + max_gap, n)):
            if close[k] > neck:
                sig[k] = 1.0 if sig[k] == 0 else sig[k]
                break
            if close[k] < min(l1, l2):
                break

    return pd.Series(sig, index=df.index)


def support_resistance(df: pd.DataFrame, left: int = 3, right: int = 3,
                       eq_tol_atr: float = 0.15) -> pd.DataFrame:
    """Live S/R map: nearest confirmed swing high (resistance) / low (support),
    plus equal-high/low liquidity shelves (repeated swings = a stronger level).

    Adds columns: resistance, support (most recent confirmed swing high/low,
    ffilled), and res_shelf / sup_shelf flags where the latest two swings cluster
    within ``eq_tol_atr`` ATR (the double-top/bottom liquidity pool).
    """
    p = swing_pivots(df, left=left, right=right)
    out = df.copy()
    out["resistance"] = p["swing_high_price"]
    out["support"] = p["swing_low_price"]
    if "atr" in out.columns:
        tol = (out["atr"] * eq_tol_atr)
        sh = p["swing_high_price"]
        sl = p["swing_low_price"]
        # A "shelf" = the current confirmed swing repeats the previous one (equal
        # highs/lows) within tolerance -> a defended level worth trading around.
        out["res_shelf"] = (sh.notna() & (np.abs(sh - sh.shift(1)) <= tol))
        out["sup_shelf"] = (sl.notna() & (np.abs(sl - sl.shift(1)) <= tol))
    return out
