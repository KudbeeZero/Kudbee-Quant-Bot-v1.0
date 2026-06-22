"""Reference-level and range-statistic construction (see package docstring)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..context.calendar import NY, complete_period_mask, ny_session_date
from ..events.features import build_features

# The canonical set of horizontal levels used for confluence scoring. Only
# columns that exist after build_levels are scored; this is the catalog.
_DEFAULT_LEVEL_COLUMNS = [
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
# Opt-in level columns: present ONLY when their feature flag built the frame (e.g.
# ENABLE_VOLUME_PROFILE). They live in the catalog so the scorer counts them when
# present, but the scorer skips absent columns, so listing them is behaviour-
# preserving by default. (Tests assert only the defaults are always present.)
OPTIONAL_LEVEL_COLUMNS = ["vp_poc", "vp_vah", "vp_val", "vp_naked_poc"]
LEVEL_COLUMNS = _DEFAULT_LEVEL_COLUMNS + OPTIONAL_LEVEL_COLUMNS

# Traders-Reality M-level grid + monthly-range band + day color. These are always
# built (below) and emitted as frame columns, but they are deliberately NOT in
# LEVEL_COLUMNS: the live confluence path (confluence.stack.factor_votes) doesn't
# touch LEVEL_COLUMNS, and the research proximity scorer (confluence.scorer) does —
# adding them there would change scored behaviour. They're consumed directly by the
# backtest candidate harness (scripts/overnight_candidates.py), not the live stack.
MLEVEL_COLUMNS = [
    "pivot_r3", "pivot_s3",
    "mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5",
    "prev_day_color", "amr", "amr_high", "amr_low",
    "day_of_week", "level_day", "week_ib_high", "week_ib_low",
    "consec_run_len", "consec_run_dir",
    "ny_brinks_high", "ny_brinks_low",
]


def _per_date_range_avg(out: pd.DataFrame, n: int) -> pd.Series:
    """Average of the prior ``n`` FULL daily ranges, mapped back to bars.

    Only complete days inform the average: TradFi stub days (Sunday Globex
    reopen, holidays — §29) would drag it down. Bars on a stub day inherit
    the average as of the last full day. On 24/7 data this reduces exactly
    to the plain shift(1).rolling(n) of every day's range.
    """
    by_date = out.groupby("ny_date").agg(_dh=("high", "max"), _dl=("low", "min"),
                                         _n=("high", "size"))
    full = complete_period_mask(by_date["_n"])
    rng = (by_date["_dh"] - by_date["_dl"])[full]
    incl = rng.rolling(n, min_periods=1).mean()   # last n full days INCLUDING the day
    prior = incl.shift(1)                          # ... strictly BEFORE the day
    adr = prior.reindex(by_date.index).ffill().where(full, incl.reindex(by_date.index).ffill())
    return out["ny_date"].map(adr).astype(float)


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


def build_levels(df: pd.DataFrame, adr_n: int = 14, awr_n: int = 8, amr_n: int = 14,
                 features=None) -> pd.DataFrame:
    """Annotate bars with the full reference-level set + range-completion stats.

    ``features`` is an optional :class:`~kudbee_quant.config.features.FeatureFlags`
    (defaults to the env-driven flags, all OFF). It only ever ADDS opt-in signal
    columns — the default frame is unchanged, so live trading is untouched until a
    flag is explicitly set.
    """
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

    # NEW YORK Brinks box: the 08:00-09:00 NY accumulation window the desk marks the
    # day's open against (MM load liquidity here before the ~09:50 run). CAUSAL — only
    # revealed to bars AT/AFTER 09:00 NY (box closed); NaN while it's still forming, so
    # it can never be "known" early. (Above is the London box; this is the NY one.)
    ny_hour = ny.dt.hour
    in_ny_brinks = (ny_hour >= 8) & (ny_hour < 9)
    nyb = out[in_ny_brinks].groupby("ny_date").agg(_h=("high", "max"), _l=("low", "min"))
    formed = (ny_hour >= 9).to_numpy()
    out["ny_brinks_high"] = np.where(formed, out["ny_date"].map(nyb["_h"]), np.nan)
    out["ny_brinks_low"] = np.where(formed, out["ny_date"].map(nyb["_l"]), np.nan)

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

    # Classic floor pivots from the PRIOR completed FULL NY day (no lookahead).
    # A TradFi stub day (Sunday Globex reopen — §29) must not set Monday's
    # pivots; stub-day bars themselves take pivots from the last full day.
    dd = out.groupby("ny_date").agg(_dh=("high", "max"), _dl=("low", "min"),
                                    _do=("open", "first"), _dc=("close", "last"),
                                    _n=("close", "size"))
    full_day = complete_period_mask(dd["_n"])
    fd = dd[full_day]

    def _floor_pivots(h, l, c):
        pp = (h + l + c) / 3.0
        return pd.DataFrame({
            "pivot_pp": pp,
            "pivot_r1": 2 * pp - l, "pivot_s1": 2 * pp - h,
            "pivot_r2": pp + (h - l), "pivot_s2": pp - (h - l),
            "pivot_r3": h + 2 * (pp - l), "pivot_s3": l - 2 * (h - pp),
        }, index=h.index)

    piv_prior = _floor_pivots(fd["_dh"].shift(1), fd["_dl"].shift(1), fd["_dc"].shift(1))
    piv_own = _floor_pivots(fd["_dh"], fd["_dl"], fd["_dc"])
    for col in piv_prior.columns:
        s = (piv_prior[col].reindex(dd.index).ffill()
             .where(full_day, piv_own[col].reindex(dd.index).ffill()))
        out[col] = out["ny_date"].map(s).astype(float)

    # Traders-Reality M-level grid: the 6 midpoint pivots between the floor pivots.
    # Derived from the (prior-day, lookahead-safe) floor-pivot columns above, so
    # they inherit the same causality. M3/M2 bracket the pivot; M5..M4 sit in the
    # resistance band, M1..M0 in the support band.
    pp, r1, r2, r3 = out["pivot_pp"], out["pivot_r1"], out["pivot_r2"], out["pivot_r3"]
    s1, s2, s3 = out["pivot_s1"], out["pivot_s2"], out["pivot_s3"]
    out["mlevel_m5"] = (r2 + r3) / 2.0
    out["mlevel_m4"] = (r1 + r2) / 2.0
    out["mlevel_m3"] = (pp + r1) / 2.0
    out["mlevel_m2"] = (s1 + pp) / 2.0
    out["mlevel_m1"] = (s2 + s1) / 2.0
    out["mlevel_m0"] = (s3 + s2) / 2.0

    # Prior-day color (drives the TR day-projection): +1 green / -1 red, from the
    # PRIOR completed full NY day's open->close. Stub days inherit the last full
    # day's prior color (mirrors the pivot fallback). No current-day data used.
    color_prior = np.sign(fd["_dc"].shift(1) - fd["_do"].shift(1))
    out["prev_day_color"] = out["ny_date"].map(
        color_prior.reindex(dd.index).ffill()).astype(float)

    # AMR (Average Monthly Range) band — the monthly analogue of AWR. Lagged one
    # month (shift(1)) so the current month's own range never feeds its own band.
    mo = out.groupby("_month_id").agg(_mh=("high", "max"), _ml=("low", "min"))
    mo["_mr"] = (mo["_mh"] - mo["_ml"]).shift(1).rolling(amr_n, min_periods=1).mean()
    out["amr"] = out["_month_id"].map(mo["_mr"]).astype(float)
    out["amr_high"] = out["monthly_open"] + out["amr"]
    out["amr_low"] = out["monthly_open"] - out["amr"]

    # --- Weekly-cycle / BTMM features (all on the existing NY-day anchor) --------
    # day_of_week from the NY SESSION date (reuses ny_date — no new timezone).
    out["day_of_week"] = pd.to_datetime(out["ny_date"]).dt.weekday        # 0=Mon..6=Sun
    # BTMM "level day": Mon=1, Tue=2, Wed=3, Thu/Fri=4 (continuation); NaN on weekends.
    out["level_day"] = out["day_of_week"].map({0: 1, 1: 2, 2: 3, 3: 4, 4: 4}).astype(float)

    # Weekly initial-balance box = Mon+Tue range of the current NY week. It is only
    # FINALIZED once Tuesday's NY day has closed, so it is left NaN on Mon/Tue (still
    # forming) and populated from Wed onward — a Wed bar reads completed Mon+Tue data.
    mon_tue = out["day_of_week"].isin([0, 1])
    ib = out[mon_tue].groupby("_week_id").agg(_ibh=("high", "max"), _ibl=("low", "min"))
    wedplus = (out["day_of_week"] >= 2).to_numpy()
    out["week_ib_high"] = np.where(wedplus, out["_week_id"].map(ib["_ibh"]), np.nan)
    out["week_ib_low"] = np.where(wedplus, out["_week_id"].map(ib["_ibl"]), np.nan)

    # Consecutive same-direction (close-to-close) run over COMPLETED bars only: the
    # values at bar t describe the run ENDING at t-1 (shift(1)), so the current bar
    # never leaks into its own run length/direction.
    step = np.sign(out["close"].diff())
    run_id = (step != step.shift(1)).cumsum()
    run_len_incl = step.groupby(run_id).cumcount() + 1
    out["consec_run_len"] = run_len_incl.shift(1)
    out["consec_run_dir"] = step.shift(1)

    # ICT/Hybrid microstructure (VWAP, premium/discount, FVGs, macro windows).
    from .microstructure import add_microstructure
    out = add_microstructure(out)
    # Market structure (BOS / CHoCH bias, equal highs/lows).
    from .structure import add_structure
    out = add_structure(out)
    # RSI/momentum divergence (Vol 9) — momentum-reversal signal.
    from .divergence import add_divergence
    out = add_divergence(out)

    # Opt-in experimental signals (default OFF — see config/features.py). Taker
    # delta / CVD / delta-divergence, derived from taker_buy_base. Only runs when
    # the flag is set AND the source column is present, so the default frame and
    # live path are byte-identical.
    if features is None:
        from ..config.features import load_feature_flags
        features = load_feature_flags()
    if features.enable_taker_delta and "taker_buy_base" in out.columns:
        from .delta import add_taker_delta
        out = add_taker_delta(out)
    if features.enable_volume_profile:
        from .volume_profile import add_volume_profile
        out = add_volume_profile(out)

    return out.drop(columns=["_month_id", "_week_id"], errors="ignore")
