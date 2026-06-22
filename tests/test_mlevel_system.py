"""Traders-Reality M-level grid + AWR/AMR + day-color: math + lookahead audit.

No network — a synthetic multi-day 1h frame drives both the exact-midpoint checks
and the causality check (modifying the LAST bar must not change any prior bar's
M-level / AMR / prev_day_color column)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from kudbee_quant.context.calendar import NY
from kudbee_quant.levels import MLEVEL_COLUMNS, build_levels


def _ohlcv(n=1200, seed=7):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.01, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": np.r_[close[0], close[:-1]], "high": high, "low": low,
        "close": close, "volume": rng.lognormal(5, 0.5, n),
    })


def test_mlevels_are_exact_midpoints():
    f = build_levels(_ohlcv())
    assert np.allclose(f["mlevel_m3"], (f["pivot_pp"] + f["pivot_r1"]) / 2, equal_nan=True)
    assert np.allclose(f["mlevel_m1"], (f["pivot_s2"] + f["pivot_s1"]) / 2, equal_nan=True)
    assert np.allclose(f["mlevel_m5"], (f["pivot_r2"] + f["pivot_r3"]) / 2, equal_nan=True)
    assert np.allclose(f["mlevel_m4"], (f["pivot_r1"] + f["pivot_r2"]) / 2, equal_nan=True)
    assert np.allclose(f["mlevel_m2"], (f["pivot_s1"] + f["pivot_pp"]) / 2, equal_nan=True)
    assert np.allclose(f["mlevel_m0"], (f["pivot_s3"] + f["pivot_s2"]) / 2, equal_nan=True)


def test_r3_s3_standard_formula():
    f = build_levels(_ohlcv())
    # R3 = prevHigh + 2*(PP - prevLow); equivalently r3 - pp == 2*(r1 - s1)/... ;
    # check the grid ordering R3>R2>R1>PP>S1>S2>S3 wherever pivots are defined.
    row = f.dropna(subset=["pivot_s3", "pivot_r3"]).iloc[-1]
    assert (row["pivot_s3"] < row["pivot_s2"] < row["pivot_s1"] < row["pivot_pp"]
            < row["pivot_r1"] < row["pivot_r2"] < row["pivot_r3"])


def test_prev_day_color_is_signum():
    f = build_levels(_ohlcv())
    vals = set(f["prev_day_color"].dropna().unique())
    assert vals <= {-1.0, 0.0, 1.0} and vals & {-1.0, 1.0}


def test_all_mlevel_columns_present_but_not_in_live_catalog():
    from kudbee_quant.levels import LEVEL_COLUMNS
    f = build_levels(_ohlcv())
    assert all(c in f.columns for c in MLEVEL_COLUMNS)
    # critical: these must NOT have leaked into the live-scored catalog
    assert not (set(MLEVEL_COLUMNS) & set(LEVEL_COLUMNS))


def test_no_lookahead_modifying_last_bar_leaves_prior_days_unchanged():
    base = _ohlcv()
    f0 = build_levels(base)
    spiked = base.copy()
    i = len(spiked) - 1
    spiked.loc[i, "high"] = spiked.loc[i, "high"] * 5      # huge future spike
    spiked.loc[i, "low"] = spiked.loc[i, "low"] * 0.2
    spiked.loc[i, "close"] = spiked.loc[i, "high"]
    f1 = build_levels(spiked)

    ny_date = pd.to_datetime(base["timestamp"], utc=True).dt.tz_convert(NY).dt.date
    prior = (ny_date < ny_date.iloc[-1]).to_numpy()        # every bar before the last day
    assert prior.sum() > 100
    cols = ["mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5",
            "prev_day_color", "amr_high", "amr_low", "pivot_r3", "pivot_s3",
            "week_ib_high", "week_ib_low", "consec_run_len", "consec_run_dir",
            "day_of_week", "level_day"]
    for c in cols:
        a = f0[c].to_numpy()[prior]
        b = f1[c].to_numpy()[prior]
        assert np.allclose(a, b, equal_nan=True), f"lookahead leak in {c}"


def test_level_day_mapping():
    f = build_levels(_ohlcv())
    m = f.groupby("day_of_week")["level_day"].first()
    assert m.get(0) == 1 and m.get(1) == 2 and m.get(2) == 3 and m.get(3) == 4 and m.get(4) == 4
    if 5 in m.index:
        assert np.isnan(m.get(5))                          # weekend: no MM level day


def test_week_ib_nan_mon_tue_populated_wed_plus():
    f = build_levels(_ohlcv())
    montue = f["day_of_week"].isin([0, 1])
    wed = f["day_of_week"] >= 2
    # forming on Mon/Tue -> must be NaN (can't be used before Tuesday closes)
    assert f.loc[montue, "week_ib_high"].isna().all()
    assert f.loc[montue, "week_ib_low"].isna().all()
    # finalized Wed+ -> some values, and high >= low where present
    wk = f.loc[wed, ["week_ib_high", "week_ib_low"]].dropna()
    assert len(wk) > 0 and (wk["week_ib_high"] >= wk["week_ib_low"]).all()


def test_consec_run_uses_only_completed_bars():
    f = build_levels(_ohlcv())
    # run length/dir at bar t describe the run ENDING at t-1: the value at t must
    # equal a recomputation that never sees close[t].
    step = np.sign(f["close"].diff())
    run_id = (step != step.shift(1)).cumsum()
    expect_len = (step.groupby(run_id).cumcount() + 1).shift(1)
    assert np.allclose(f["consec_run_len"].to_numpy(), expect_len.to_numpy(), equal_nan=True)
    assert np.allclose(f["consec_run_dir"].to_numpy(), step.shift(1).to_numpy(), equal_nan=True)
    assert set(f["consec_run_dir"].dropna().unique()) <= {-1.0, 0.0, 1.0}


def test_bracket_target_price_parity_and_level_targeting():
    """The bracket's new per-bar target_price: None == legacy scalar path; a level
    above entry resolves at that level's R; a level behind entry is skipped."""
    from kudbee_quant.backtest.bracket import bracket_backtest
    n = 60
    close = np.linspace(100, 130, n)                       # steady uptrend
    df = pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5,
                       "close": close, "atr": np.ones(n)})
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[0] = 1.0                                      # one long at entry≈100

    a = bracket_backtest(df, sig, stop_atr=1.0, target_r=3.0, limit_retrace_atr=None)
    b = bracket_backtest(df, sig, stop_atr=1.0, target_r=3.0, limit_retrace_atr=None,
                         target_price=None)
    assert list(a.trades) == list(b.trades)               # None == legacy scalar path

    tp = pd.Series(105.0, index=df.index)                 # entry 100, 1R=1 -> 105 = +5R
    c = bracket_backtest(df, sig, stop_atr=1.0, target_r=3.0, limit_retrace_atr=None,
                         target_price=tp)
    assert len(list(c.trades)) == 1
    assert c.trades[0] > a.trades[0] and c.trades[0] > 4.0   # ~+5R, beyond the 3R scalar

    behind = pd.Series(99.5, index=df.index)              # below a long entry -> not tradable
    d = bracket_backtest(df, sig, stop_atr=1.0, target_r=3.0, limit_retrace_atr=None,
                         target_price=behind)
    assert list(d.trades) == []


def test_slice_overrides_is_positional_and_passes_scalars():
    """The harness slices a per-bar target_price POSITIONALLY (so it lines up with
    df.iloc[lo:hi]) and leaves scalar overrides untouched."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from overnight_research import _slice_overrides

    s = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0], index=[100, 101, 102, 103, 104])
    out = _slice_overrides({"target_price": s, "tp1_r": None, "stop_atr": 1.5}, 1, 4)
    assert isinstance(out["target_price"], np.ndarray)
    assert list(out["target_price"]) == [11.0, 12.0, 13.0]   # positional [1:4], index ignored
    assert out["tp1_r"] is None and out["stop_atr"] == 1.5    # scalars pass through
