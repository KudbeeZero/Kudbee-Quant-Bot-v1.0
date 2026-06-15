"""Tests for the opt-in killzone entry gate on confluence_position (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.confluence import confluence_position
from kudbee_quant.confluence.stack import KILLZONE_GATE_FLAGS
from kudbee_quant.levels import build_levels


def _ohlcv(n=1200, seed=4):
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


def test_killzone_gate_is_subset_and_off_by_default():
    f = build_levels(_ohlcv())
    base = confluence_position(f, min_pct=0.4)
    gated = confluence_position(f, min_pct=0.4, killzone_gate=True)
    nz_base = base != 0
    nz_gated = gated != 0
    # The gate only removes trades (those outside the active windows).
    assert (nz_gated & ~nz_base).sum() == 0
    assert nz_gated.sum() < nz_base.sum()      # something was actually filtered
    # Default call is unchanged by the new param.
    assert confluence_position(f, min_pct=0.4).equals(base)


def test_gated_trades_are_inside_active_windows():
    f = build_levels(_ohlcv())
    gated = confluence_position(f, min_pct=0.4, killzone_gate=True)
    active = f[list(KILLZONE_GATE_FLAGS)].astype(bool).any(axis=1)
    assert (gated[gated != 0].index.isin(f.index[active])).all()


def test_custom_flag_list():
    f = build_levels(_ohlcv())
    only_london = confluence_position(f, min_pct=0.4, killzone_gate=["in_london_kz"])
    nz = only_london != 0
    assert f.loc[nz, "in_london_kz"].astype(bool).all()


def test_no_op_when_flags_absent():
    f = build_levels(_ohlcv())
    base = confluence_position(f, min_pct=0.4)
    # A frame without the flag columns -> gate cannot block, returns the base signal.
    no_flags = f.drop(columns=[c for c in KILLZONE_GATE_FLAGS if c in f.columns])
    gated = confluence_position(no_flags, min_pct=0.4, killzone_gate=True)
    assert gated.equals(confluence_position(no_flags, min_pct=0.4))
    assert (gated != 0).sum() == (base != 0).sum()
