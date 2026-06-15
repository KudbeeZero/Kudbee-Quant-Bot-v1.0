"""Out-of-sample validation for Signal #3 — killzone entry gate.

Tests restricting confluence entries to the active London/NY/Brinks windows
(confluence_position(killzone_gate=True)) vs the around-the-clock baseline, on real
Binance 1h data (top-10 majors), canonical validated bracket:

  (A) killzone FILTER: R-expectancy IS(70%)/OOS(30%) + walk_forward() engine check.
  (B) UTC-hour BLEED map: baseline expectancy by entry hour (UTC) — does the gate
      drop the dead hours (e.g. 06h / 16h UTC) and keep the good ones?
  (C) per-window expectancy (London KZ / NY Brinks / overlap vs off-hours).

No files written, no live trading touched. Run: PYTHONPATH=. python scripts/validate_killzone_gate.py
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from kudbee_quant.backtest.engine import BacktestConfig
from kudbee_quant.backtest.walkforward import walk_forward
from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
)
from kudbee_quant.confluence.stack import KILLZONE_GATE_FLAGS, confluence_position
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.ml.labels import trade_outcomes

warnings.filterwarnings("ignore")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
LIMIT = 8000
OOS_FRAC = 0.30
BRK = dict(target_r=TARGET_R, stop_atr=STOP_ATR, limit_retrace_atr=RETRACE_ATR,
           max_bars=MAX_BARS, entry_window=ENTRY_WINDOW, fee_pct=FEE_PCT)


def base_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True)


def kz_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True, killzone_gate=True)


def load_frames():
    client = BinanceClient()
    frames = {}
    for sym in SYMBOLS:
        try:
            df = client.klines(sym, interval="1h", limit=LIMIT, cache_ttl=86400)
            frames[sym] = build_levels(df)
            print(f"  {sym}: {len(df)} bars", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym}: FETCH FAILED ({e})", flush=True)
    return frames


def _split(frames, fn):
    is_r, oos_r = [], []
    for df in frames.values():
        outc = trade_outcomes(df, fn(df), **BRK)
        if outc.empty:
            continue
        cutoff = int(len(df) * (1 - OOS_FRAC))
        eb = outc["entry_bar"].to_numpy()
        r = outc["realized_r"].to_numpy()
        is_r += list(r[eb < cutoff])
        oos_r += list(r[eb >= cutoff])
    return np.array(is_r), np.array(oos_r)


def _line(tag, r):
    if len(r) == 0:
        return f"  {tag:<14} n=0"
    return (f"  {tag:<14} n={len(r):>4}  expectancy={r.mean():+.4f}R  "
            f"win%={100*(r>0).mean():4.1f}  totalR={r.sum():+.1f}")


def filter_analysis(frames):
    print("\n" + "=" * 72)
    print("(A) killzone FILTER — pooled R-expectancy, IS(70%) vs OOS(30%)")
    print("=" * 72)
    b_is, b_oos = _split(frames, base_signal)
    k_is, k_oos = _split(frames, kz_signal)
    print("IN-SAMPLE:")
    print(_line("baseline", b_is))
    print(_line("+killzone", k_is))
    print("OUT-OF-SAMPLE:")
    print(_line("baseline", b_oos))
    print(_line("+killzone", k_oos))
    if len(b_oos) and len(k_oos):
        print(f"\n  OOS expectancy lift = {k_oos.mean()-b_oos.mean():+.4f}R   "
              f"trades kept = {100*len(k_oos)/len(b_oos):.1f}%")


def hour_bleed(frames):
    print("\n" + "=" * 72)
    print("(B) UTC-HOUR BLEED — baseline expectancy by entry hour (all trades)")
    print("=" * 72)
    hours, rs, in_kz = [], [], []
    for df in frames.values():
        outc = trade_outcomes(df, base_signal(df), **BRK)
        if outc.empty:
            continue
        eb = outc["entry_bar"].to_numpy()
        ts = pd.to_datetime(df["timestamp"].to_numpy()[eb], utc=True)
        hours += list(ts.hour)
        rs += list(outc["realized_r"].to_numpy())
        active = df[list(KILLZONE_GATE_FLAGS)].astype(bool).any(axis=1).to_numpy()
        in_kz += list(active[eb])
    d = pd.DataFrame({"hour": hours, "r": rs, "kz": in_kz})
    print(f"  {'UTC':>3} {'n':>5} {'expectancy':>11}  in-killzone?")
    for h, g in d.groupby("hour"):
        flag = "KZ" if g["kz"].mean() > 0.5 else "  "
        mark = "  <-- bleed" if g["r"].mean() < -0.05 else ""
        print(f"  {h:>3} {len(g):>5} {g['r'].mean():>+11.4f}  {flag}{mark}")
    inkz = d[d["kz"]]
    off = d[~d["kz"]]
    print(f"\n  IN killzone : n={len(inkz):>4}  expectancy={inkz['r'].mean():+.4f}R")
    print(f"  OFF hours   : n={len(off):>4}  expectancy={off['r'].mean():+.4f}R")


def walkforward_crosscheck(frames):
    print("\n" + "=" * 72)
    print("(A2) walk_forward() ENGINE cross-check — mean OOS over symbols")
    print("=" * 72)
    cfg = BacktestConfig(fee_bps=FEE_PCT * 1e4 / 2, periods_per_year=24 * 365)
    print(f"  {'variant':<12} {'IS Sharpe':>10} {'OOS Sharpe':>11} {'OOS ret':>10}")
    for name, fn in (("baseline", base_signal), ("+killzone", kz_signal)):
        i, o, r = [], [], []
        for df in frames.values():
            try:
                wf = walk_forward(df.reset_index(drop=True), fn, n_folds=5, config=cfg)
                i.append(wf.in_sample.sharpe)
                o.append(wf.out_of_sample.sharpe)
                r.append(wf.out_of_sample.total_return)
            except Exception:  # noqa: BLE001
                continue
        print(f"  {name:<12} {np.mean(i):>10.3f} {np.mean(o):>11.3f} {np.mean(r):>10.4f}")


def main():
    print("Fetching real Binance 1h data (top-10 majors)...", flush=True)
    frames = load_frames()
    if len(frames) < 3:
        print("Not enough data; aborting.")
        sys.exit(1)
    filter_analysis(frames)
    hour_bleed(frames)
    walkforward_crosscheck(frames)
    print("\nDone.")


if __name__ == "__main__":
    main()
