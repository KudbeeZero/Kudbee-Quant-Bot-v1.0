"""Tests for the market-maker cycle context (deterministic, no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.context import (
    SessionWindows,
    add_mm_context,
    detect_sweeps,
    label_sessions,
    reference_levels,
    weekly_cycle_phase,
)


def _hourly(n: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + np.abs(rng.normal(0, 0.3, n))
    low = close - np.abs(rng.normal(0, 0.3, n))
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": close, "high": high, "low": low, "close": close,
            "volume": rng.lognormal(5, 0.5, n),
        }
    )


def test_session_labels_cover_all_hours():
    out = label_sessions(_hourly(72))
    assert set(out["session"].unique()) <= {"asian", "london", "new_york", "off"}
    # London window 07:00-16:00 UTC -> hour 9 must be london (NY starts 13).
    h9 = out[pd.to_datetime(out["timestamp"]).dt.hour == 9]
    assert (h9["session"] == "london").all()


def test_asian_box_present_during_later_sessions():
    out = label_sessions(_hourly(72))
    # Some London/NY bars should have a defined Asian range from earlier.
    later = out[out["session"].isin(["london", "new_york"])]
    assert later["asian_high"].notna().any()
    assert (out["asian_high"] >= out["asian_low"]).dropna().all()


def test_reference_levels_have_no_lookahead():
    out = reference_levels(_hourly(120))
    # First day has no previous day -> PDH/PDL are NaN there.
    first_day = pd.to_datetime(out["timestamp"]).dt.date == pd.Timestamp("2024-01-01").date()
    assert out.loc[first_day, "pdh"].isna().all()
    # Later days have finite previous-day levels.
    assert out["pdh"].notna().any()


def test_detect_sweeps_flags_known_pierce():
    df = reference_levels(_hourly(120))
    df = label_sessions(df)
    # Force a bullish sweep on the last bar: wick below pdl, close above it.
    i = df.index[-1]
    pdl = df.loc[i, "pdl"]
    if np.isnan(pdl):
        pdl = df["low"].iloc[-50]
        df.loc[i, "pdl"] = pdl
    df.loc[i, "low"] = pdl - 1.0
    df.loc[i, "close"] = pdl + 1.0
    swept = detect_sweeps(df)
    assert bool(swept.loc[i, "swept_low"]) is True
    assert swept.loc[i, "sweep_bias"] >= 1


def test_weekly_phase_labels():
    out = weekly_cycle_phase(_hourly(48))
    assert out["cycle_phase"].str.contains("mon|tue|wed|thu|fri|sat|sun").all()


def test_add_mm_context_pipeline_runs():
    out = add_mm_context(_hourly(300))
    for col in ["session", "pdh", "pwh", "swept_low", "swept_high", "cycle_phase"]:
        assert col in out.columns
    assert len(out) == 300


def test_custom_session_windows():
    out = label_sessions(_hourly(48), SessionWindows(asian=(0, 6), london=(6, 14), new_york=(14, 22)))
    h3 = out[pd.to_datetime(out["timestamp"]).dt.hour == 3]
    assert (h3["in_asian"]).all()
