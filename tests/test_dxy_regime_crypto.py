"""Tests for research/dxy_regime_crypto.py — the DXY-regime crypto study.

CI-safe: pure synthetic fixtures, no network, no DXY/Binance fetch. Guards:
  (a) the trade enumerator reproduces the live bracket_backtest BASELINE net-R
      list EXACTLY — proving it's a faithful mirror, not a reimplementation;
  (b) the DXY as-of lookup forward-fills correctly (weekends/holidays) and
      returns NaN before the series start;
  (c) regime bucketing uses the shipped get_dxy_regime and the significance gate
      (boot_p<0.05 AND n>=30) yields INCONCLUSIVE on a small/insignificant set.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402

import dxy_regime_crypto as dxc  # noqa: E402
import trailing_sweep as ts  # noqa: E402


def _synthetic_frame(seed: int = 11, n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.004, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    op = np.r_[close[0], close[:-1]]
    atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()
    # Match the LIVE frame shape: RangeIndex + a tz-aware UTC `timestamp` column
    # (build_levels output). A DatetimeIndex fixture would have masked the
    # RangeIndex/timestamp-column join bug found on the first real run.
    ts = pd.date_range("2024-06-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"timestamp": ts, "open": op, "high": high, "low": low, "close": close, "atr": atr}
    )


def _alt_signal(df: pd.DataFrame) -> pd.Series:
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::9] = 1.0
    sig.iloc[5::17] = -1.0
    return sig


# --- (a) fidelity: enumerator == live bracket_backtest baseline -------------

def test_enumerator_reproduces_bracket_baseline_exactly():
    df = _synthetic_frame()
    sig = _alt_signal(df)
    engine = bracket_backtest(df, sig, **ts.BASELINE_KW)
    rows = dxc.baseline_trades_with_times(df, sig)
    net = [r["net_r"] for r in rows]
    assert len(net) == engine.n_trades, f"count: mirror={len(net)} engine={engine.n_trades}"
    np.testing.assert_allclose(net, engine.trades, rtol=0, atol=1e-12)
    # every row carries a usable entry timestamp + a valid side
    assert all(isinstance(r["entry_ts"], pd.Timestamp) for r in rows)
    assert {r["side"] for r in rows} <= {"long", "short"}


# --- (b) DXY as-of lookup ---------------------------------------------------

def test_dxy_asof_forward_fills_and_guards_start():
    dxy = pd.Series(
        [100.0, 101.0, 102.0],
        index=pd.to_datetime(["2024-06-03", "2024-06-04", "2024-06-05"]),  # Mon/Tue/Wed
    )
    # exact day
    assert dxc.dxy_asof(dxy, pd.Timestamp("2024-06-04 07:00")) == 101.0
    # weekend after Wed close -> forward-fill Wed's 102.0
    assert dxc.dxy_asof(dxy, pd.Timestamp("2024-06-08 12:00")) == 102.0
    # before the series -> NaN
    assert np.isnan(dxc.dxy_asof(dxy, pd.Timestamp("2024-06-01")))
    # tz-aware UTC input (live frame shape) must resolve the same as naive
    assert dxc.dxy_asof(dxy, pd.Timestamp("2024-06-04 07:00", tz="UTC")) == 101.0


# --- (c) regime bucketing + gate --------------------------------------------

def test_study_buckets_by_regime_and_gate_is_inconclusive_on_small_set():
    df = _synthetic_frame()
    sig = _alt_signal(df)
    # DXY pinned in the 95-98 band over the whole window -> all trades land in
    # USD_BASE_BUILDING; other regimes are empty.
    dxy = pd.Series(96.0, index=pd.date_range("2024-05-01", periods=120, freq="1D"))
    summary = dxc.study([("w", "BTCUSDT", df, sig)], dxy, boot_p=lambda x: 0.5)

    # structure: one row per regime x {all,long,short}
    assert set(summary["regime"]) == set(dxc.REGIME_ORDER)
    assert set(summary["side"]) == {"all", "long", "short"}
    base = summary[(summary["regime"] == "USD_BASE_BUILDING") & (summary["side"] == "all")]
    assert int(base["n"].iloc[0]) > 0, "trades should populate the pinned regime"
    other = summary[(summary["regime"] == "USD_BULL_CONFIRMED") & (summary["side"] == "all")]
    assert int(other["n"].iloc[0]) == 0, "no trades should fall in an unused regime"

    # gate: with boot_p stubbed at 0.5 (>=0.05) nothing qualifies -> INCONCLUSIVE
    assert "INCONCLUSIVE" in dxc._verdict(summary)


def test_verdict_flags_a_significant_cell():
    # hand-built summary with one qualifying cell (boot_p<0.05 AND n>=30)
    summary = pd.DataFrame([
        {"regime": "USD_BULL_CONFIRMED", "side": "short", "n": 40, "mean_r": 0.20,
         "win_rate": 0.55, "total_r": 8.0, "boot_p": 0.01},
        {"regime": "USD_WEAK", "side": "short", "n": 12, "mean_r": 0.10,
         "win_rate": 0.50, "total_r": 1.2, "boot_p": 0.30},
    ])
    v = dxc._verdict(summary)
    assert "SIGNIFICANT" in v and "USD_BULL_CONFIRMED/short" in v
