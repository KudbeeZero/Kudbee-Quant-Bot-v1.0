"""Tests for the event-study engine (deterministic, no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.events import build_features, detect_level_tests, recovery_curve
from kudbee_quant.events.detectors import detect_vector_events
from kudbee_quant.events.outcomes import add_forward_outcomes, forward_return
from kudbee_quant.events.study import benjamini_hochberg, conditional_table, wilson_ci
from kudbee_quant.events.study import StudyConfig


def _ohlcv(n=600, seed=0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.01, n)
    close = 100 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.003, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.003, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n),
    })


def test_build_features_has_expected_columns():
    f = build_features(_ohlcv())
    for col in ["session", "killzone", "day_of_week", "minutes_into_ny",
                "daily_open", "weekly_open", "atr", "dist_daily_open_atr",
                "is_holiday", "vector"]:
        assert col in f.columns


def test_forward_return_no_lookahead():
    df = _ohlcv(50)
    r = forward_return(df["close"], 3)
    # fwd return at t uses close[t+3]; last 3 must be NaN.
    assert r.iloc[-3:].isna().all()
    assert np.isclose(r.iloc[0], df["close"].iloc[3] / df["close"].iloc[0] - 1)


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(8, 10)
    assert 0 <= lo < hi <= 1
    assert wilson_ci(0, 0) == (0.0, 1.0)


def test_benjamini_hochberg_controls_discoveries():
    # One tiny p-value among many large ones -> at most that one rejected.
    pvals = [0.001] + [0.6] * 19
    rejected = benjamini_hochberg(pvals, alpha=0.10)
    assert rejected[0] is True
    assert sum(rejected) == 1
    # All-null p-values -> nothing rejected.
    assert not any(benjamini_hochberg([0.5] * 10, alpha=0.10))


def test_conditional_table_flags_insufficient():
    f = build_features(_ohlcv())
    f = detect_level_tests(f, "daily_open")
    f = add_forward_outcomes(f, horizons=(4,))
    tests = f[f["daily_open_test"]]
    table = conditional_table(tests, "fwd_up_4", ["day_of_week"], StudyConfig(min_n=1000))
    # With min_n huge, nothing is sufficient and nothing is significant.
    assert not table["sufficient"].any()
    assert not table["significant_fdr"].any()


def test_level_tests_number_resets_per_day():
    f = build_features(_ohlcv(300))
    f = detect_level_tests(f, "daily_open")
    nth = f["daily_open_nth_test"]
    assert (nth >= 0).all()
    # nth_test only positive where a test fired.
    assert (nth[~f["daily_open_test"]] == 0).all()


def test_recovery_curve_runs_and_brackets():
    f = build_features(_ohlcv(800))
    res = recovery_curve(f, horizons=(1, 10, 100))
    assert res.n_vectors > 0
    for h in (1, 10, 100):
        assert 0.0 <= res.recovered_frac[h] <= 1.0
        assert 0.0 <= res.null_frac[h] <= 1.0
    # Recovery is monotonic non-decreasing in horizon.
    fr = [res.recovered_frac[h] for h in (1, 10, 100)]
    assert fr[0] <= fr[1] <= fr[2]


def test_vector_events_zone_only_on_climax():
    f = build_features(_ohlcv())
    ev = detect_vector_events(f)
    assert ev.loc[~ev["is_vector"], "zone_low"].isna().all()
    assert (ev.loc[ev["is_vector"], "zone_high"] >= ev.loc[ev["is_vector"], "zone_low"]).all()
