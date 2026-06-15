"""Tests for the opt-in taker-delta / CVD / delta-divergence signal (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.config.features import FeatureFlags, load_feature_flags
from kudbee_quant.confluence import confluence_position
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import DELTA_FEATURE_COLUMNS, add_taker_delta, build_levels
from kudbee_quant.ml.labels import make_features


def _ohlcv_with_taker(n=600, seed=7):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.011, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    vol = rng.lognormal(5, 0.6, n)
    # taker-buy share leans the way the bar closed (more buying on up bars).
    frac = np.clip(0.5 + 0.25 * np.sign(rets) + rng.normal(0, 0.1, n), 0.0, 1.0)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": vol, "taker_buy_base": vol * frac,
    })


def test_delta_columns_present_and_bounded():
    out = add_taker_delta(_ohlcv_with_taker())
    for c in DELTA_FEATURE_COLUMNS:
        assert c in out.columns
    assert out["delta_pct"].dropna().between(-1, 1).all()
    assert out["cvd_session_pct"].dropna().between(-1, 1).all()
    assert out["cvd_roll_pct"].dropna().between(-1, 1).all()
    assert set(np.unique(out["delta_div"].values)).issubset({-1.0, 0.0, 1.0})


def test_delta_sign_matches_aggression():
    df = _ohlcv_with_taker(n=50)
    df.loc[df.index[10], "taker_buy_base"] = df.loc[df.index[10], "volume"]  # all buy
    df.loc[df.index[20], "taker_buy_base"] = 0.0                              # all sell
    out = add_taker_delta(df)
    assert out["delta_pct"].iloc[10] == 1.0
    assert out["delta_pct"].iloc[20] == -1.0


def test_no_op_without_taker_column():
    df = _ohlcv_with_taker().drop(columns=["taker_buy_base"])
    out = add_taker_delta(df)
    assert "delta_pct" not in out.columns
    assert out.equals(df)


def test_causal_truncation_invariance():
    """Backward-only: earlier rows are identical whether or not future bars exist."""
    full = add_taker_delta(_ohlcv_with_taker(n=400))
    trunc = add_taker_delta(_ohlcv_with_taker(n=400).iloc[:250])
    for c in ("delta_pct", "delta_z", "cvd_session_pct", "cvd_roll_pct", "delta_div"):
        a = full[c].iloc[:250].to_numpy()
        b = trunc[c].to_numpy()
        both = np.isfinite(a) & np.isfinite(b)
        assert np.allclose(a[both], b[both], atol=1e-9)


def test_feature_flag_defaults_off():
    assert FeatureFlags().enable_taker_delta is False
    assert load_feature_flags({}).enable_taker_delta is False
    assert load_feature_flags({"ENABLE_TAKER_DELTA": "true"}).enable_taker_delta is True


def test_build_levels_gated_off_by_default():
    df = _ohlcv_with_taker()
    off = build_levels(df, features=FeatureFlags(enable_taker_delta=False))
    on = build_levels(df, features=FeatureFlags(enable_taker_delta=True))
    assert "delta_pct" not in off.columns
    assert "delta_pct" in on.columns
    # The opt-in path only ADDS columns — every default column is preserved.
    assert set(off.columns) <= set(on.columns)


def test_make_features_picks_up_delta_when_present():
    on = build_levels(_ohlcv_with_taker(), features=FeatureFlags(enable_taker_delta=True))
    feats = make_features(on)
    assert {"delta_pct", "cvd_roll_pct", "delta_div"} <= set(feats.columns)


def test_delta_align_filter_is_subset_and_off_by_default():
    on = build_levels(_ohlcv_with_taker(), features=FeatureFlags(enable_taker_delta=True))
    base = confluence_position(on, min_pct=0.4)
    filt = confluence_position(on, min_pct=0.4, delta_align=True)
    # Filter never creates trades; it only removes flow-opposed ones.
    nz_base = base != 0
    nz_filt = filt != 0
    assert (nz_filt & ~nz_base).sum() == 0
    # Default (no delta_align) is unchanged by the new param.
    assert confluence_position(on, min_pct=0.4).equals(base)


def test_binance_to_frame_keeps_taker_columns():
    rows = [[
        1_700_000_000_000, "100", "110", "90", "105", "1000",
        1_700_003_599_999, "105000", 42, "600", "63000", "0",
    ]]
    df = BinanceClient._to_frame(rows)
    assert {"taker_buy_base", "taker_buy_quote"} <= set(df.columns)
    assert df["taker_buy_base"].iloc[0] == 600.0
