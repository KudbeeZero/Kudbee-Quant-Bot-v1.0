"""Dollar account simulation + trade-log tests (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.backtest.money import simulate_account, trade_log


def _df(prices, atr=1.0):
    n = len(prices)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": prices, "high": [p + 0.1 for p in prices], "low": [p - 0.1 for p in prices],
        "close": prices, "atr": atr})


def test_trade_log_records_stop_pct_and_net_r():
    # Long market entry at 100, ATR 1 -> stop 1% of price. Target 2R (102) hit.
    prices = [100, 100, 102.5, 103]
    df = _df(prices); df.loc[2, "high"] = 102.5
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    log = trade_log(df, sig, stop_atr=1.0, target_r=2.0, max_bars=3,
                    fee_pct=0.0, limit_retrace_atr=None)
    assert len(log) == 1
    assert abs(log["stop_pct"].iloc[0] - 0.01) < 1e-9   # 1.0 / 100
    assert abs(log["outcome_r"].iloc[0] - 2.0) < 1e-9


def test_fixed_fractional_controls_risk():
    # 50 trades, each exactly -1R. Risking 2% per trade, equity should decay like
    # 0.98**k and NEVER be wiped out (no single trade > 2% of equity).
    log = pd.DataFrame({"stop_pct": [0.02] * 50, "net_r": [-1.0] * 50})
    r = simulate_account(log, equity0=100.0, mode="fixed_fractional", risk_frac=0.02,
                         leverage=10.0)
    assert not r.ruined
    assert abs(r.avg_risk_pct - 2.0) < 1e-6
    assert abs(r.equity_final - 100.0 * 0.98 ** 50) < 1e-6


def test_full_notional_10x_can_ruin():
    # Same losing streak, but 10x full notional with a 2.5% stop risks 25% PER
    # trade -> the account is wiped out fast.
    log = pd.DataFrame({"stop_pct": [0.025] * 50, "net_r": [-1.0] * 50})
    r = simulate_account(log, equity0=100.0, mode="full_notional", leverage=10.0)
    assert r.ruined
    assert r.avg_risk_pct > 20.0       # ~25% of equity risked each trade


def test_positive_edge_compounds():
    # All +3R winners at 2% risk -> equity grows 1.06x per trade.
    log = pd.DataFrame({"stop_pct": [0.02] * 10, "net_r": [3.0] * 10})
    r = simulate_account(log, equity0=100.0, mode="fixed_fractional", risk_frac=0.02)
    assert r.equity_final > 100.0 and not r.ruined
    assert abs(r.equity_final - 100.0 * 1.06 ** 10) < 1e-6
