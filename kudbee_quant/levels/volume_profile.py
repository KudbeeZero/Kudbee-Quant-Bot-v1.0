"""Per-session volume profile — POC / VAH / VAL / naked POC as horizontal levels.

A volume profile bins a session's traded volume by price; the busiest price is the
**POC** (point of control), and the contiguous band around it holding ~70% of the
volume is the **value area** (edges **VAH**/**VAL**). A POC that price has not yet
traded back through is a **naked / virgin POC** — an unfilled magnet that often
acts as a later draw on liquidity.

Built per NY-session day and exposed exactly like the existing prior-period levels
(``prior_ny_high``, floor pivots): a day's profile is complete only at day end, so
it is shown to the NEXT day's bars (shift one day) — strictly causal, no lookahead.

OPT-IN: ``build_levels`` only calls this when ``FeatureFlags.enable_volume_profile``
is set (default OFF). The columns are listed in ``LEVEL_COLUMNS`` but the
level-clustering scorer only scores columns actually present, so the default frame
and live path are unchanged until the flag is set.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Level columns (joined into LEVEL_COLUMNS) + scale-free features for the meta-model.
VP_LEVEL_COLUMNS = ["vp_poc", "vp_vah", "vp_val", "vp_naked_poc"]
VP_FEATURE_COLUMNS = ["dist_vp_poc_atr", "dist_vp_naked_poc_atr", "in_value_area"]


def _day_profile(tp: np.ndarray, vol: np.ndarray, lo: float, hi: float,
                 n_bins: int, va_frac: float) -> tuple[float, float, float]:
    """POC, VAH, VAL for one session from a volume-by-price histogram."""
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo or vol.sum() <= 0:
        return np.nan, np.nan, np.nan
    edges = np.linspace(lo, hi, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    idx = np.clip(np.digitize(tp, edges) - 1, 0, n_bins - 1)
    hist = np.zeros(n_bins)
    np.add.at(hist, idx, vol)
    total = hist.sum()
    poc_bin = int(np.argmax(hist))
    poc = float(centers[poc_bin])

    # Expand a value-area window out from the POC, always taking the heavier
    # neighbour, until it holds ``va_frac`` of total volume.
    lo_b = hi_b = poc_bin
    acc = hist[poc_bin]
    target = va_frac * total
    while acc < target and (lo_b > 0 or hi_b < n_bins - 1):
        below = hist[lo_b - 1] if lo_b > 0 else -1.0
        above = hist[hi_b + 1] if hi_b < n_bins - 1 else -1.0
        if above >= below:
            hi_b += 1
            acc += hist[hi_b]
        else:
            lo_b -= 1
            acc += hist[lo_b]
    return poc, float(edges[hi_b + 1]), float(edges[lo_b])


def add_volume_profile(df: pd.DataFrame, n_bins: int = 50, va_frac: float = 0.70,
                       near_atr: float = 0.25) -> pd.DataFrame:
    """Annotate bars with the prior-session volume profile + naked POC (causal)."""
    out = df.copy()
    if "ny_date" not in out.columns:
        from ..context.calendar import ny_session_date
        out["ny_date"] = ny_session_date(out["timestamp"])

    tp = ((out["high"] + out["low"] + out["close"]) / 3.0).to_numpy()
    vol = out["volume"].to_numpy(dtype=float)
    low = out["low"].to_numpy()
    high = out["high"].to_numpy()
    close = out["close"].to_numpy()
    dates = out["ny_date"].to_numpy()

    # One profile per day.
    poc_by_date: dict = {}
    vah_by_date: dict = {}
    val_by_date: dict = {}
    for d, g in out.groupby("ny_date"):
        rows = g.index.to_numpy()
        i0, i1 = rows[0], rows[-1] + 1
        poc, vah, val = _day_profile(tp[i0:i1], vol[i0:i1],
                                     low[i0:i1].min(), high[i0:i1].max(), n_bins, va_frac)
        poc_by_date[d] = poc
        vah_by_date[d] = vah
        val_by_date[d] = val

    # Expose the PRIOR day's profile to each bar (shift one session) — causal.
    ordered = list(dict.fromkeys(dates))           # unique dates in order
    prior = {d: ordered[i - 1] if i > 0 else None for i, d in enumerate(ordered)}
    out["vp_poc"] = [poc_by_date.get(prior[d]) if prior[d] is not None else np.nan for d in dates]
    out["vp_vah"] = [vah_by_date.get(prior[d]) if prior[d] is not None else np.nan for d in dates]
    out["vp_val"] = [val_by_date.get(prior[d]) if prior[d] is not None else np.nan for d in dates]

    # Naked POC: nearest prior-day POC not yet traded through. Single causal pass —
    # the previous day's POC enters the pool at the first bar of the new day; we
    # expose the nearest untouched POC BEFORE letting the current bar touch it.
    n = len(out)
    naked = np.full(n, np.nan)
    untouched: list[float] = []
    last_date = None
    for t in range(n):
        d = dates[t]
        if d != last_date:
            if last_date is not None:
                p = poc_by_date.get(last_date)
                if p is not None and np.isfinite(p):
                    untouched.append(p)
            last_date = d
        if untouched:
            arr = np.asarray(untouched)
            naked[t] = float(arr[np.argmin(np.abs(arr - close[t]))])
        # mark any untouched POC the current bar trades through as filled
        if untouched:
            untouched = [p for p in untouched if not (low[t] <= p <= high[t])]
    out["vp_naked_poc"] = naked

    # Scale-free features for the meta-model (distance in ATR; in-value-area flag).
    if "atr" in out.columns:
        atr = out["atr"].replace(0, np.nan)
        out["dist_vp_poc_atr"] = (out["close"] - out["vp_poc"]) / atr
        out["dist_vp_naked_poc_atr"] = (out["close"] - out["vp_naked_poc"]) / atr
        out["in_value_area"] = ((out["close"] >= out["vp_val"]) &
                                (out["close"] <= out["vp_vah"])).astype(float)
        out["near_vp_poc"] = (out["close"] - out["vp_poc"]).abs().le(near_atr * out["atr"]).astype(float)
    return out
