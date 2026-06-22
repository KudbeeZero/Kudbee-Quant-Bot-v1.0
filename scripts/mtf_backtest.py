"""Multi-timeframe (15m entry / 30m bias) backtest — STANDALONE, read-only.

Hypothesis: take a 15m PVSRA vector/climax candle ONLY when the 30m EMA trend
agrees (5>13>50 up / 5<13<50 down). Entry on the 15m climax (market), shipping
bracket geometry. The 30m bias is merged onto the 15m bars CAUSALLY — a 15m
decision at time t may use only the 30m bar that has already CLOSED at/before t,
never the forming 30m bar (the merge that makes or breaks an MTF study).

Does NOT touch live trading, the validated stack, the workflow, or the journal.
Run: PYTHONPATH=. python scripts/mtf_backtest.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kudbee_quant.backtest.bracket import bracket_backtest
from kudbee_quant.config.validated_defaults import MAX_BARS, STOP_ATR, TAKER_FEE_PCT, TARGET_R
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.ingest.resample import resample_ohlcv
from kudbee_quant.levels import build_levels
from kudbee_quant.signals.pvsra import pvsra_vector_candles
from kudbee_quant.universe import TOP_10_CRYPTO

# overnight_research helpers (pooling + bootstrap) — same yardstick as the harness
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from overnight_research import _bootstrap_p, _pool_expectancy  # noqa: E402

LIMIT_15M = 16000          # ~166 days of 15m bars (as many as the client paginates)
FEE_PCT = TAKER_FEE_PCT    # MARKET entry on the climax -> taker cost is the honest fee


def compute_bias30(df30: pd.DataFrame) -> pd.Series:
    """+1 when ema_5>ema_13>ema_50 (stacked up), -1 when stacked down, else 0."""
    e5, e13, e50 = df30["ema_5"], df30["ema_13"], df30["ema_50"]
    up = (e5 > e13) & (e13 > e50)
    dn = (e5 < e13) & (e13 < e50)
    return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=df30.index).astype(float)


def causal_bias_merge(lv15: pd.DataFrame, df30: pd.DataFrame) -> pd.DataFrame:
    """Align ``df30['bias30']`` onto the 15m frame WITHOUT lookahead.

    A 30m bar at ``timestamp`` T closes at T+30m; a 15m bar at ``timestamp`` t
    decides at t+15m. We backward-asof-join so each 15m decision picks the most
    recent 30m bar that has ALREADY CLOSED at/before the decision — never the
    forming 30m bar. Returns lv15 (original order) with a ``bias30`` column.
    """
    left = lv15.copy()
    left["decision_time"] = pd.to_datetime(left["timestamp"], utc=True) + pd.Timedelta(minutes=15)
    right = df30[["timestamp", "bias30"]].copy()
    right["close_time"] = pd.to_datetime(right["timestamp"], utc=True) + pd.Timedelta(minutes=30)
    right = right[["close_time", "bias30"]].sort_values("close_time")
    merged = pd.merge_asof(
        left.sort_values("decision_time").reset_index(drop=True),
        right, left_on="decision_time", right_on="close_time", direction="backward",
    )
    merged["bias30"] = merged["bias30"].fillna(0.0)
    return merged


def mtf_signal(frame: pd.DataFrame) -> pd.Series:
    """CONTRARIAN: FADE the climax in the direction of the 30m trend.
    +1 (long) on a BEAR climax during a 30m up-bias (fade the down-spike);
    -1 (short) on a BULL climax during a 30m down-bias (fade the up-spike)."""
    vec = frame["vector"]
    bias = frame["bias30"]
    long_ = (vec == "bear_climax") & (bias > 0)
    short_ = (vec == "bull_climax") & (bias < 0)
    return pd.Series(np.where(long_, 1.0, np.where(short_, -1.0, 0.0)), index=frame.index)


def run_symbol(client: BinanceClient, symbol: str):
    """Return the list of per-trade R for one symbol (chronological)."""
    df15 = client.klines(symbol, interval="15m", limit=LIMIT_15M, cache_ttl=86400)
    df30 = build_levels(resample_ohlcv(df15, "30min"))
    df30 = df30.assign(bias30=compute_bias30(df30))
    lv15 = pvsra_vector_candles(build_levels(df15))
    frame = causal_bias_merge(lv15, df30)
    sig = mtf_signal(frame)
    res = bracket_backtest(frame, sig, stop_atr=STOP_ATR, target_r=TARGET_R,
                           max_bars=MAX_BARS, fee_pct=FEE_PCT, limit_retrace_atr=None)
    return list(res.trades)


def main():
    client = BinanceClient()
    print(f"MTF 15m-entry / 30m-bias backtest — {len(TOP_10_CRYPTO)} majors, "
          f"limit={LIMIT_15M} 15m bars, taker fee={FEE_PCT}, "
          f"stop={STOP_ATR}ATR target={TARGET_R}R market-entry\n")
    all_trades, h1, h2 = [], [], []
    print(f"  {'symbol':<10} {'n':>5} {'expR':>8} {'win%':>6}")
    for s in TOP_10_CRYPTO:
        try:
            t = run_symbol(client, s)
        except Exception as e:  # noqa: BLE001
            print(f"  {s:<10}  FETCH/RUN FAILED ({type(e).__name__}: {e})")
            continue
        n, exp, win = _pool_expectancy(t)
        print(f"  {s:<10} {n:>5} {exp:>+8.4f} {100*win:>6.1f}")
        all_trades += t
        mid = len(t) // 2
        h1 += t[:mid]; h2 += t[mid:]

    n, exp, win = _pool_expectancy(all_trades)
    _, e1, _ = _pool_expectancy(h1)
    _, e2, _ = _pool_expectancy(h2)
    p = _bootstrap_p([0.0] * len(all_trades), all_trades) if n else 1.0
    print("\n" + "=" * 60)
    print("POOLED (net of taker fees)")
    print("=" * 60)
    print(f"  trades            : {n}")
    print(f"  expectancy        : {exp:+.4f} R/trade")
    print(f"  win rate          : {100*win:.1f}%")
    print(f"  split-half exp    : h1 {e1:+.4f}  |  h2 {e2:+.4f}")
    print(f"  bootstrap p (vs 0): {p:.4f}")
    edge = exp > 0 and e1 > 0 and e2 > 0 and p < 0.05
    print("\n  VERDICT: " + (
        "✅ EDGE — expectancy>0, both halves>0, p<0.05. Worth a forward paper book."
        if edge else
        "🔴 NOT AN EDGE — fails one of {expectancy>0, both halves>0, p<0.05}. Do not ship."))


if __name__ == "__main__":
    main()
