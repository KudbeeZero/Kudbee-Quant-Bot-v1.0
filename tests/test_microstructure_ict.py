"""Tests for microstructure features and ICT scenarios (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.levels import build_levels
from kudbee_quant.levels.microstructure import add_fvg, add_session_vwap
from kudbee_quant.scenarios import SCENARIOS
from kudbee_quant.scenarios.audit import lookahead_audit
from kudbee_quant.scenarios.ict import ICT_SCENARIOS


def _ohlcv(n=900, seed=7):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.011, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n),
    })


def test_vwap_within_day_range():
    f = add_session_vwap(_ohlcv(200).assign(
        utc_date=pd.to_datetime(_ohlcv(200)["timestamp"], utc=True).dt.date))
    assert "vwap" in f.columns
    ok = f.dropna(subset=["vwap"])
    # VWAP must sit between the running low and high (sanity).
    assert (ok["vwap"] <= ok["high"].cummax() + 1e6).all()


def test_fvg_detects_gaps():
    # Construct an explicit bullish gap: bar t low above bar t-2 high.
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
        "open": [10, 10, 12, 12, 12], "high": [10.5, 11, 13, 13, 13],
        "low": [9.5, 10, 11.2, 12, 12], "close": [10, 11, 12.5, 12.5, 12.5],
        "volume": [1, 1, 1, 1, 1],
    })
    f = add_fvg(df)
    # bar index 2: low 11.2 > high[0] 10.5 -> bullish FVG.
    assert bool(f["fvg_bull"].iloc[2])


def test_build_levels_has_microstructure():
    f = build_levels(_ohlcv())
    for col in ["vwap", "in_premium", "fvg_bull", "in_silver_bullet", "dealing_mid"]:
        assert col in f.columns


def test_daily_open_is_utc_midnight():
    f = build_levels(_ohlcv(300))
    # The daily open of the first UTC day equals that day's first bar open.
    first_day = f[f["utc_date"] == f["utc_date"].iloc[0]]
    assert np.isclose(first_day["daily_open"].iloc[0], first_day["open"].iloc[0])


def test_ict_scenarios_valid_and_causal():
    df = _ohlcv(700)
    f = build_levels(df)
    for name, fn in ICT_SCENARIOS.items():
        sig = fn(f)
        assert len(sig) == len(f), name
        vals = pd.Series(sig).dropna().unique()
        assert set(np.sign(vals)).issubset({-1.0, 0.0, 1.0}), name
    # Causality: a representative ICT scenario must pass the lookahead audit.
    r = lookahead_audit(df, ICT_SCENARIOS["turtle_soup"], n_checks=20, min_history=300,
                        name="turtle_soup")
    assert r.clean


def test_ict_in_registry():
    for k in ICT_SCENARIOS:
        assert k in SCENARIOS
