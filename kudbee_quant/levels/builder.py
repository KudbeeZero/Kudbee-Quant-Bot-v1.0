"""Reference-level and range-statistic construction (see package docstring)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..context.calendar import NY, ny_session_date
from ..events.features import build_features

# The canonical set of horizontal levels used for confluence scoring. Only
# columns that exist after build_levels are scored; this is the catalog.
LEVEL_COLUMNS = [
    "daily_open", "weekly_open", "monthly_open",
    "adr_high", "adr_low", "awr_high", "awr_low",
    "pdh", "pdl", "pwh", "pwl",
    "asian_high", "asian_low",
    "prior_ny_high", "prior_ny_low",
    "ny_open", "asian_open",
    "brinks_high", "brinks_low",
    "round_below", "round_above",
    "pivot_pp", "pivot_r1", "pivot_s1", "pivot_r2", "pivot_s2",
    "vwap", "dealing_mid",
]


def _per_date_range_avg(out: pd.DataFrame, n: int) -> pd.Series:
    """Average of the prior ``n`` completed daily ranges, mapped back to bars."""
    by_date = out.groupby("ny_date").agg(_dh=("high", "max"), _dl=("low", "min"))
    by_date["_range"] = by_date["_dh"] - by_date["_dl"]
    by_date["_adr"] = by_date["_range"].shift(1).rolling(n, min_periods=1).mean()
    return out["ny_date"].map(by_date["_adr"]).astype(float)


def _round_step(price: pd.Series) -> pd.Series:
    """Psychological round-number step ~1% of price scale (e.g. 1000 for ~60k)."""
    safe = price.clip(lower=1e-9)
    return np.power(10.0, np.floor(np.log10(safe)) - 1)


def range_stats(df: pd.DataFrame, adr_n: int = 14, awr_n: int = 8, amr_n: int = 6) -> dict:
    """Summary range statistics (ADR/AWR/AMR) over the sample, for reporting."""
    out = build_features(df)
    out["ny_date"] = ny_session_date(out["timestamp"])
    ny = pd.to_datetime(out["timestamp"], utc=True).dt.tz_convert(NY)
    daily = out.groupby("ny_date").apply(lambda g: g["high"].max() - g["low"].min())
    week_id = ny.dt.tz_localize(None).dt.to_period("W")
    month_id = ny.dt.tz_localize(None).dt.to_period("M")
    weekly = out.assign(_w=week_id.values).groupby("_w").apply(lambda g: g["high"].max() - g["low"].min())
    monthly = out.assign(_m=month_id.values).groupby("_m").apply(lambda g: g["high"].max() - g["low"].min())
    return {
        "adr": float(daily.tail(adr_n).mean()),
        "awr": float(weekly.tail(awr_n).mean()),
        "amr": float(monthly.tail(amr_n).mean()),
        "n_days": int(daily.shape[0]),
        "n_weeks": int(weekly.shape[0]),
        "n_months": int(monthly.shape[0]),
    }


def build_levels(df: pd.DataFrame, adr_n: int = 14, awr_n: int = 8) -> pd.DataFrame:
    """Annotate bars with the full reference-level set + range-completion stats."""
    out = build_features(df)  # gives daily_open, weekly_open, atr, sessions, asian_*, PDH/PDL...
    out["ny_date"] = ny_session_date(out["timestamp"])
    ny = pd.to_datetime(out["timestamp"], utc=True).dt.tz_convert(NY)

    # Monthly open = open of the first bar of each NY month.
    out["_month_id"] = ny.dt.tz_localize(None).dt.to_period("M").astype(str)
    out["monthly_open"] = out.groupby("_month_id")["open"].transform("first")

    # Average daily / weekly range (prior completed periods) + projections.
    out["adr"] = _per_date_range_avg(out, adr_n)
    out["adr_high"] = out["daily_open"] + out["adr"]
    out["adr_low"] = out["daily_open"] - out["adr"]
    out["_week_id"] = ny.dt.tz_localize(None).dt.to_period("W").astype(str)
    wk = out.groupby("_week_id").agg(_wh=("high", "max"), _wl=("low", "min"))
    wk["_wr"] = (wk["_wh"] - wk["_wl"]).shift(1).rolling(awr_n, min_periods=1).mean()
    out["awr"] = out["_week_id"].map(wk["_wr"]).astype(float)
    out["awr_high"] = out["weekly_open"] + out["awr"]
    out["awr_low"] = out["weekly_open"] - out["awr"]

    # Intraday range consumed vs ADR/AWR (running, no future info).
    day_hi = out.groupby("ny_date")["high"].cummax()
    day_lo = out.groupby("ny_date")["low"].cummin()
    out["range_used_today"] = day_hi - day_lo
    out["pct_adr_used"] = (out["range_used_today"] / out["adr"]).replace([np.inf, -np.inf], np.nan)
    wk_hi = out.groupby("_week_id")["high"].cummax()
    wk_lo = out.groupby("_week_id")["low"].cummin()
    out["pct_awr_used"] = ((wk_hi - wk_lo) / out["awr"]).replace([np.inf, -np.inf], np.nan)

    # Session opens and prior-session NY high/low.
    out["ny_open"] = out.where(out["session"] == "ny").groupby(out["ny_date"])["open"].transform("first")
    out["asian_open"] = out.where(out["session"] == "asian").groupby(out["ny_date"])["open"].transform("first")
    ny_sess = out[out["session"] == "ny"].groupby("ny_date").agg(_h=("high", "max"), _l=("low", "min"))
    ny_sess["prior_ny_high"] = ny_sess["_h"].shift(1)
    ny_sess["prior_ny_low"] = ny_sess["_l"].shift(1)
    out["prior_ny_high"] = out["ny_date"].map(ny_sess["prior_ny_high"]).astype(float)
    out["prior_ny_low"] = out["ny_date"].map(ny_sess["prior_ny_low"]).astype(float)

    # Brinks box: the 1h pre-London window (08:00-09:00 UTC, the documented EU
    # Brinks box). Configurable/approximate — exact TR timings are community-
    # specific. High/low of that window per day, available to later bars.
    utc_hour = pd.to_datetime(out["timestamp"], utc=True).dt.hour
    in_brinks = (utc_hour >= 8) & (utc_hour < 9)
    brinks = out[in_brinks].groupby("ny_date").agg(_bh=("high", "max"), _bl=("low", "min"))
    out["brinks_high"] = out["ny_date"].map(brinks["_bh"]).astype(float)
    out["brinks_low"] = out["ny_date"].map(brinks["_bl"]).astype(float)

    # Psychological round numbers bracketing the current close.
    step = _round_step(out["close"])
    out["round_below"] = np.floor(out["close"] / step) * step
    out["round_above"] = out["round_below"] + step

    # EMA stack + cloud position (price above/inside/below the 13-50 ribbon).
    # "Price above the EMA cloud" = bullish markup structure on the timeframe.
    for p in (5, 13, 50, 200, 800):
        out[f"ema_{p}"] = out["close"].ewm(span=p, adjust=False).mean()
    cloud_hi = out[["ema_13", "ema_50"]].max(axis=1)
    cloud_lo = out[["ema_13", "ema_50"]].min(axis=1)
    out["ema_cloud_pos"] = np.where(out["close"] > cloud_hi, 1,
                                    np.where(out["close"] < cloud_lo, -1, 0))

    # Classic floor pivots from the PRIOR completed NY day (no lookahead).
    dd = out.groupby("ny_date").agg(_dh=("high", "max"), _dl=("low", "min"), _dc=("close", "last"))
    pdh, pdl, pdc = dd["_dh"].shift(1), dd["_dl"].shift(1), dd["_dc"].shift(1)
    pp = (pdh + pdl + pdc) / 3.0
    piv = pd.DataFrame({
        "pivot_pp": pp,
        "pivot_r1": 2 * pp - pdl, "pivot_s1": 2 * pp - pdh,
        "pivot_r2": pp + (pdh - pdl), "pivot_s2": pp - (pdh - pdl),
    }, index=dd.index)
    for col in piv.columns:
        out[col] = out["ny_date"].map(piv[col]).astype(float)

    # ICT/Hybrid microstructure (VWAP, premium/discount, FVGs, macro windows).
    from .microstructure import add_microstructure
    out = add_microstructure(out)
    # Market structure (BOS / CHoCH bias, equal highs/lows).
    from .structure import add_structure
    out = add_structure(out)

    return out.drop(columns=["_month_id", "_week_id"], errors="ignore")
