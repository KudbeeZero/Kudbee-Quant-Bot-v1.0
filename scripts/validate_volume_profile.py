"""Out-of-sample validation for Signal #2 — per-session volume profile.

Validates the POC/VAH/VAL/naked-POC levels two independent ways on real Binance 1h
data (top-10 majors), on the canonical validated bracket:

  (A) vp-proximity FILTER on confluence_position(): take base signals only when
      price sits within 0.5 ATR of a volume-profile level (POC / naked POC / value-
      area edge) -> R-expectancy IS(70%)/OOS(30%) + walk_forward() engine check.
  (B) vp distance FEATURES into the meta-model: evaluate() OOS WITH vs WITHOUT.

No files written, no live trading touched. Run: PYTHONPATH=. python scripts/validate_volume_profile.py
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from kudbee_quant.backtest.engine import BacktestConfig
from kudbee_quant.backtest.walkforward import walk_forward
from kudbee_quant.config.features import FeatureFlags
from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
)
from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.ml.labels import build_dataset, trade_outcomes
from kudbee_quant.ml.meta_model import evaluate

warnings.filterwarnings("ignore")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
LIMIT = 8000
OOS_FRAC = 0.30
NEAR_ATR = 0.5
FLAGS = FeatureFlags(enable_volume_profile=True)
BRK = dict(target_r=TARGET_R, stop_atr=STOP_ATR, limit_retrace_atr=RETRACE_ATR,
           max_bars=MAX_BARS, entry_window=ENTRY_WINDOW, fee_pct=FEE_PCT)
VP_FEATS = ["dist_vp_poc_atr", "dist_vp_naked_poc_atr", "in_value_area", "near_vp_poc"]


def base_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True)


def vp_signal(df):
    """Base signal, kept only when price is within NEAR_ATR of a VP level."""
    sig = base_signal(df)
    atr = df["atr"]
    near = pd.Series(False, index=df.index)
    for col in ("vp_poc", "vp_naked_poc", "vp_vah", "vp_val"):
        if col in df.columns:
            near = near | (df["close"] - df[col]).abs().le(NEAR_ATR * atr)
    return sig.where(near, 0.0)


def load_frames():
    client = BinanceClient()
    frames = {}
    for sym in SYMBOLS:
        try:
            df = client.klines(sym, interval="1h", limit=LIMIT, cache_ttl=86400)
            frames[sym] = build_levels(df, features=FLAGS)
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
        return f"  {tag:<16} n=0"
    return (f"  {tag:<16} n={len(r):>4}  expectancy={r.mean():+.4f}R  "
            f"win%={100*(r>0).mean():4.1f}  totalR={r.sum():+.1f}")


def filter_analysis(frames):
    print("\n" + "=" * 72)
    print("(A) vp-proximity FILTER — pooled R-expectancy, IS(70%) vs OOS(30%)")
    print("=" * 72)
    b_is, b_oos = _split(frames, base_signal)
    v_is, v_oos = _split(frames, vp_signal)
    print("IN-SAMPLE:")
    print(_line("baseline", b_is))
    print(_line("+vp_near", v_is))
    print("OUT-OF-SAMPLE:")
    print(_line("baseline", b_oos))
    print(_line("+vp_near", v_oos))
    if len(b_oos) and len(v_oos):
        print(f"\n  OOS expectancy lift = {v_oos.mean()-b_oos.mean():+.4f}R   "
              f"trades kept = {100*len(v_oos)/len(b_oos):.1f}%")


def walkforward_crosscheck(frames):
    print("\n" + "=" * 72)
    print("(A2) walk_forward() ENGINE cross-check — mean OOS over symbols")
    print("=" * 72)
    cfg = BacktestConfig(fee_bps=FEE_PCT * 1e4 / 2, periods_per_year=24 * 365)
    print(f"  {'variant':<12} {'IS Sharpe':>10} {'OOS Sharpe':>11} {'OOS ret':>10}")
    for name, fn in (("baseline", base_signal), ("+vp_near", vp_signal)):
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


def meta_feature_analysis(frames):
    print("\n" + "=" * 72)
    print("(B) vp FEATURES — meta-model OOS CV, WITH vs WITHOUT vp features")
    print("=" * 72)
    X, y, meta = build_dataset(frames, base_signal, **BRK)
    if len(y) == 0:
        print("  no trades")
        return
    vp_cols = [c for c in VP_FEATS if c in X.columns]
    print(f"  trades={len(y)}  base_rate={y.mean():.3f}  vp_features={vp_cols}")

    def report(Xv, tag):
        rep = evaluate(Xv, y, meta, thresholds=(0.5, 0.6))
        print(f"\n  --- {tag} ---")
        for mname, mr in rep["models"].items():
            if "error" in mr:
                print(f"    {mname}: {mr['error']}")
                continue
            eg = mr.get("expectancy_gate", [])
            best = max(eg, key=lambda d: d.get("gated_expectancy_r", -9)) if eg else {}
            print(f"    {mname}: AUC={mr['auc']:.4f}  best gated_exp="
                  f"{best.get('gated_expectancy_r','-')}R lift={best.get('lift_r','-')}R "
                  f"p_perm={best.get('p_perm','-')} sig={best.get('significant','-')}")

    report(X, "WITH vp features")
    report(X.drop(columns=vp_cols), "WITHOUT vp features (control)")


def main():
    print("Fetching real Binance 1h data (top-10 majors)...", flush=True)
    frames = load_frames()
    if len(frames) < 3:
        print("Not enough data; aborting.")
        sys.exit(1)
    filter_analysis(frames)
    walkforward_crosscheck(frames)
    meta_feature_analysis(frames)
    print("\nDone.")


if __name__ == "__main__":
    main()
