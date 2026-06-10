"""ZCash (ZECUSDT) orderbook-fill backtest.

Tests the user's insight: on short timeframes (1m–1h), price gaps create
unexecuted order zones. A LIMIT order placed in the gap fills at a better
price than a market order, and at maker rate instead of taker.

Coinbase consumer fee structure for reference (why this matters):
  Market/taker: ~1.49% + spread ≈ 2-3% round-trip
  Limit/maker:  ~0.4-0.6% each way ≈ 0.8-1.2% round-trip

We test with Binance ZECUSDT data (publicly available) and use:
  market entry : TAKER_FEE_PCT = 0.0009 (measured Binance taker)
  limit entry  : FEE_PCT       = 0.0004 (Binance maker assumption)
  coinbase_taker: 0.012         (conservative Coinbase Pro taker estimate)
  coinbase_maker: 0.008         (Coinbase Pro limit-maker estimate)

Key question: on which timeframe does the gap-fill limit entry produce the
highest improvement in expectancy vs market entry?
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import pandas as pd

from kudbee_quant.ingest import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.signals import pvsra_vector_candles
from kudbee_quant.backtest.bracket import bracket_backtest
from kudbee_quant.config.validated_defaults import (
    STOP_ATR, TARGET_R, MAX_BARS, RETRACE_ATR, ENTRY_WINDOW,
    FEE_PCT, TAKER_FEE_PCT,
)

SYMBOL = "ZECUSDT"

# Coinbase Pro estimates (round-trip fraction of price)
COINBASE_TAKER = 0.012   # market order: ~0.6% each way + spread
COINBASE_MAKER = 0.008   # limit order: ~0.4% each way maker rate

TIMEFRAMES = [
    ("1m",  3000, 3),   # (interval, bars_to_fetch, entry_window_for_gaps)
    ("3m",  2000, 4),
    ("5m",  1500, 5),
    ("15m", 1000, 5),
    ("1h",  2000, 6),
    ("4h",  1000, 6),
]

# Limit retrace depths to test (in ATR multiples)
RETRACE_LEVELS = [0.10, 0.20, 0.25, 0.35, 0.50]

LONG_ONLY_SIGNAL = True  # ZEC has been persistently bullish — test long side


def _pvsra_signal(df: pd.DataFrame, long_only: bool = True) -> pd.Series:
    from kudbee_quant.backtest.strategy import pvsra_positions
    return pvsra_positions(df, allow_short=not long_only)


def run_tf_comparison(client: BinanceClient) -> pd.DataFrame:
    rows = []
    for interval, limit, ewin in TIMEFRAMES:
        print(f"\n{'='*60}")
        print(f"  {SYMBOL}  {interval}  ({limit} bars)")
        print(f"{'='*60}")

        raw = client.klines(SYMBOL, interval=interval, limit=limit)
        df = build_levels(raw)
        sig = _pvsra_signal(df, long_only=LONG_ONLY_SIGNAL)

        # --- Baseline: market entry, Binance taker fee ---
        mkt = bracket_backtest(
            df, sig,
            stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
            fee_pct=TAKER_FEE_PCT,
            limit_retrace_atr=None,
        )
        print(f"  Market entry (Binance taker 0.09%): "
              f"n={mkt.n_trades:3d}  WR={mkt.win_rate:.0%}  "
              f"E={mkt.expectancy_r:+.3f}R  total={mkt.total_r:+.1f}R  "
              f"PF={mkt.profit_factor:.2f}")
        rows.append({"tf": interval, "entry": "market_binance",
                     "retrace_atr": None, "fee_pct": TAKER_FEE_PCT,
                     **mkt.summary()})

        # --- Coinbase taker (market) — shows why retail is at a disadvantage ---
        cb_mkt = bracket_backtest(
            df, sig,
            stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
            fee_pct=COINBASE_TAKER,
            limit_retrace_atr=None,
        )
        print(f"  Market entry (Coinbase taker 1.2%) : "
              f"n={cb_mkt.n_trades:3d}  WR={cb_mkt.win_rate:.0%}  "
              f"E={cb_mkt.expectancy_r:+.3f}R  total={cb_mkt.total_r:+.1f}R")
        rows.append({"tf": interval, "entry": "market_coinbase",
                     "retrace_atr": None, "fee_pct": COINBASE_TAKER,
                     **cb_mkt.summary()})

        # --- Limit entry: Binance maker, sweep retrace depths ---
        best_lim = None
        for ret in RETRACE_LEVELS:
            lim = bracket_backtest(
                df, sig,
                stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
                fee_pct=FEE_PCT,
                limit_retrace_atr=ret,
                entry_window=ewin,
            )
            fill_pct = lim.n_trades / max(mkt.n_trades, 1)
            print(f"  Limit {ret:.2f}ATR (Binance maker 0.04%): "
                  f"n={lim.n_trades:3d}  WR={lim.win_rate:.0%}  "
                  f"E={lim.expectancy_r:+.3f}R  total={lim.total_r:+.1f}R  "
                  f"fill%={fill_pct:.0%}")
            rows.append({"tf": interval, "entry": f"limit_{ret:.2f}atr_binance",
                         "retrace_atr": ret, "fee_pct": FEE_PCT,
                         **lim.summary()})
            if best_lim is None or lim.expectancy_r > best_lim.expectancy_r:
                best_lim = lim
                best_ret = ret

        # --- Limit entry: Coinbase maker ---
        cb_best = bracket_backtest(
            df, sig,
            stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
            fee_pct=COINBASE_MAKER,
            limit_retrace_atr=RETRACE_ATR,
            entry_window=ewin,
        )
        print(f"  Limit {RETRACE_ATR:.2f}ATR (Coinbase maker  0.8%) : "
              f"n={cb_best.n_trades:3d}  WR={cb_best.win_rate:.0%}  "
              f"E={cb_best.expectancy_r:+.3f}R  total={cb_best.total_r:+.1f}R")
        rows.append({"tf": interval, "entry": f"limit_{RETRACE_ATR:.2f}atr_coinbase",
                     "retrace_atr": RETRACE_ATR, "fee_pct": COINBASE_MAKER,
                     **cb_best.summary()})

        if best_lim is not None:
            gain = best_lim.expectancy_r - mkt.expectancy_r
            print(f"\n  *** Best limit ({best_ret:.2f}ATR) vs market: "
                  f"ΔE = {gain:+.3f}R  ({'+' if gain>0 else ''}{gain/max(abs(mkt.expectancy_r),0.001):.0%})")

    return pd.DataFrame(rows)


def print_summary_table(df: pd.DataFrame) -> None:
    print("\n\n" + "="*80)
    print("SUMMARY — ZEC orderbook-fill: E (expectancy per trade in R)")
    print("="*80)
    pivot = df.pivot_table(
        index="tf", columns="entry", values="expectancy_r", aggfunc="first"
    )
    # Order columns logically
    col_order = ["market_binance", "market_coinbase"]
    for ret in RETRACE_LEVELS:
        k = f"limit_{ret:.2f}atr_binance"
        if k in pivot.columns:
            col_order.append(k)
    k2 = f"limit_{RETRACE_ATR:.2f}atr_coinbase"
    if k2 in pivot.columns:
        col_order.append(k2)
    col_order = [c for c in col_order if c in pivot.columns]
    tf_order = ["1m", "3m", "5m", "15m", "1h", "4h"]
    pivot = pivot.reindex(index=[t for t in tf_order if t in pivot.index],
                          columns=col_order)
    print(pivot.round(3).to_string())

    print("\n\nSUMMARY — total R accumulated")
    print("-"*80)
    pivot2 = df.pivot_table(
        index="tf", columns="entry", values="total_r", aggfunc="first"
    )
    pivot2 = pivot2.reindex(index=[t for t in tf_order if t in pivot2.index],
                            columns=col_order)
    print(pivot2.round(1).to_string())

    print("\n\nSUMMARY — trade count (fills)")
    print("-"*80)
    pivot3 = df.pivot_table(
        index="tf", columns="entry", values="n_trades", aggfunc="first"
    )
    pivot3 = pivot3.reindex(index=[t for t in tf_order if t in pivot3.index],
                            columns=col_order)
    print(pivot3.to_string())


if __name__ == "__main__":
    client = BinanceClient()
    results = run_tf_comparison(client)
    print_summary_table(results)

    # Save for reference
    results.to_csv("data/zec_orderbook_fill_backtest.csv", index=False)
    print(f"\n\nResults saved to data/zec_orderbook_fill_backtest.csv")
    print("\nINTERPRETATION GUIDE:")
    print("  E > 0          : positive expectancy — edge exists on this TF/entry combo")
    print("  ΔE (limit-mkt) : how much better limit fill is vs market fill in R/trade")
    print("  fill%          : fraction of signals that found a retrace (higher=better)")
    print("  On 1m/3m: fee_pct/ATR is very large → market entries are nearly always")
    print("  negative; limit entries into gaps reduce this cost dramatically.")
    print("  The 'sweet spot' is where ΔE > 0 AND fill% > 40%.")
