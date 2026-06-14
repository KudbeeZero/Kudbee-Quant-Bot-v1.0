"""Out-of-sample validation for Signal #1 — taker delta / CVD / delta-divergence.

Validates the signal TWO independent ways on real Binance 1h data for the
walk-forward-validated top-10 majors, on the canonical validated bracket
(config/validated_defaults.py):

  (A) delta_align FILTER on confluence_position():
        * R-expectancy on a chronological IS(70%)/OOS(30%) split, pooled across
          symbols, baseline vs +delta_align  -> does it lift OOS expectancy
          without shrinking trade count to noise?
        * walk_forward() engine cross-check (OOS Sharpe / return), per the
          "run it through walkforward.py" mandate.

  (B) delta FEATURES into the meta-model:
        * meta_model.evaluate() OOS (purged/embargoed CV) WITH the delta features
          vs WITH them dropped -> marginal OOS AUC + expectancy-gate lift.

Plus the 60% confluence-band probe: does delta_align rescue the ~0.6 band?

Prints a plain-text report to stdout. No files written, no live trading touched.
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from kudbee_quant.backtest.engine import BacktestConfig
from kudbee_quant.backtest.walkforward import walk_forward
from kudbee_quant.config.features import FeatureFlags
from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
)
from kudbee_quant.confluence.stack import confluence_position, confluence_score
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.ml.labels import build_dataset, trade_outcomes
from kudbee_quant.ml.meta_model import evaluate

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
LIMIT = 8000          # ~333 days of 1h bars
OOS_FRAC = 0.30
FLAGS = FeatureFlags(enable_taker_delta=True)
BRK = dict(target_r=TARGET_R, stop_atr=STOP_ATR, limit_retrace_atr=RETRACE_ATR,
           max_bars=MAX_BARS, entry_window=ENTRY_WINDOW, fee_pct=FEE_PCT)


def base_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True)


def delta_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True, delta_align=True)


def load_frames() -> dict:
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


def _split_expectancy(frames, signal_fn):
    """Pooled per-trade realized R, split IS/OOS by entry_bar vs the 70% cutoff."""
    is_r, oos_r = [], []
    is_pct, oos_pct = [], []     # confluence_pct at entry, for the band probe
    for df in frames.values():
        sig = signal_fn(df)
        outc = trade_outcomes(df, sig, **BRK)
        if outc.empty:
            continue
        cutoff = int(len(df) * (1 - OOS_FRAC))
        pct = confluence_score(df)["confluence_pct"].to_numpy()
        eb = outc["entry_bar"].to_numpy()
        r = outc["realized_r"].to_numpy()
        is_mask = eb < cutoff
        is_r += list(r[is_mask]); oos_r += list(r[~is_mask])
        is_pct += list(pct[eb[is_mask]]); oos_pct += list(pct[eb[~is_mask]])
    return (np.array(is_r), np.array(oos_r),
            np.array(is_pct), np.array(oos_pct))


def _exp_line(tag, r):
    if len(r) == 0:
        return f"  {tag:<22} n=0"
    return (f"  {tag:<22} n={len(r):>4}  expectancy={r.mean():+.4f}R  "
            f"win%={100*(r>0).mean():4.1f}  totalR={r.sum():+.1f}")


def filter_analysis(frames):
    print("\n" + "=" * 72)
    print("(A) delta_align FILTER — pooled R-expectancy, IS(70%) vs OOS(30%)")
    print("=" * 72)
    b_is, b_oos, b_is_pct, b_oos_pct = _split_expectancy(frames, base_signal)
    d_is, d_oos, d_is_pct, d_oos_pct = _split_expectancy(frames, delta_signal)
    print("IN-SAMPLE:")
    print(_exp_line("baseline", b_is))
    print(_exp_line("+delta_align", d_is))
    print("OUT-OF-SAMPLE:")
    print(_exp_line("baseline", b_oos))
    print(_exp_line("+delta_align", d_oos))
    if len(b_oos) and len(d_oos):
        lift = d_oos.mean() - b_oos.mean()
        kept = len(d_oos) / len(b_oos)
        print(f"\n  OOS expectancy lift = {lift:+.4f}R   trades kept = {100*kept:.1f}%")
    return (b_is_pct, b_is, b_oos_pct, b_oos, d_oos_pct, d_oos)


def band_probe(b_is_pct, b_is, b_oos_pct, b_oos, d_oos_pct, d_oos):
    print("\n" + "=" * 72)
    print("60% CONFLUENCE-BAND PROBE — expectancy by confluence_pct band")
    print("=" * 72)
    bins = [0.49, 0.55, 0.65, 0.75, 0.85, 1.01]
    labels = ["~0.50", "~0.60", "~0.70", "~0.80", "0.9-1.0"]

    def band_table(pct, r, title):
        print(f"\n  {title}")
        idx = np.digitize(pct, bins) - 1
        for i, lab in enumerate(labels):
            m = idx == i
            if m.sum() == 0:
                continue
            rr = r[m]
            print(f"    band {lab:<8} n={rr.size:>4}  exp={rr.mean():+.4f}R  totalR={rr.sum():+.1f}")

    band_table(b_is_pct, b_is, "IN-SAMPLE baseline")
    band_table(b_oos_pct, b_oos, "OUT-OF-SAMPLE baseline")
    band_table(d_oos_pct, d_oos, "OUT-OF-SAMPLE +delta_align (does it rescue ~0.60?)")


def walkforward_crosscheck(frames):
    print("\n" + "=" * 72)
    print("(A2) walk_forward() ENGINE cross-check — mean OOS over symbols")
    print("=" * 72)
    cfg = BacktestConfig(fee_bps=FEE_PCT * 1e4 / 2, periods_per_year=24 * 365)
    rows = []
    for name, fn in (("baseline", base_signal), ("+delta_align", delta_signal)):
        is_sh, oos_sh, oos_ret = [], [], []
        for df in frames.values():
            try:
                wf = walk_forward(df.reset_index(drop=True), fn, n_folds=5, config=cfg)
                is_sh.append(wf.in_sample.sharpe)
                oos_sh.append(wf.out_of_sample.sharpe)
                oos_ret.append(wf.out_of_sample.total_return)
            except Exception:  # noqa: BLE001
                continue
        rows.append((name, np.mean(is_sh), np.mean(oos_sh), np.mean(oos_ret)))
    print(f"  {'variant':<14} {'IS Sharpe':>10} {'OOS Sharpe':>11} {'OOS ret':>10}")
    for name, i, o, r in rows:
        print(f"  {name:<14} {i:>10.3f} {o:>11.3f} {r:>10.4f}")


def meta_feature_analysis(frames):
    print("\n" + "=" * 72)
    print("(B) delta FEATURES — meta-model OOS CV, WITH vs WITHOUT delta features")
    print("=" * 72)
    X, y, meta = build_dataset(frames, base_signal, **BRK)
    if len(y) == 0:
        print("  no trades — cannot evaluate"); return
    delta_cols = [c for c in ("delta_pct", "delta_z", "cvd_session_pct",
                              "cvd_roll_pct", "delta_div") if c in X.columns]
    print(f"  trades={len(y)}  base_rate={y.mean():.3f}  delta_features={delta_cols}")

    def report(Xv, tag):
        rep = evaluate(Xv, y, meta, thresholds=(0.5, 0.6))
        print(f"\n  --- {tag} ---")
        for mname, mr in rep["models"].items():
            if "error" in mr:
                print(f"    {mname}: {mr['error']}"); continue
            eg = mr.get("expectancy_gate", [])
            best = max(eg, key=lambda d: d.get("gated_expectancy_r", -9)) if eg else {}
            print(f"    {mname}: AUC={mr['auc']:.4f}  "
                  f"best gated_exp={best.get('gated_expectancy_r','-')}R "
                  f"lift={best.get('lift_r','-')}R p_perm={best.get('p_perm','-')} "
                  f"sig={best.get('significant','-')}")
        coefs = {d["feature"]: d["coef"] for d in rep["logit_coefficients"]}
        dc = {c: coefs[c] for c in delta_cols if c in coefs}
        if dc:
            print(f"    logit coefs (delta): {dc}")

    report(X, "WITH delta features")
    report(X.drop(columns=delta_cols), "WITHOUT delta features (control)")


def main():
    print("Fetching real Binance 1h data (top-10 majors)...", flush=True)
    frames = load_frames()
    if len(frames) < 3:
        print("Not enough data fetched; aborting."); sys.exit(1)
    res = filter_analysis(frames)
    band_probe(*res)
    walkforward_crosscheck(frames)
    meta_feature_analysis(frames)
    print("\nDone.")


if __name__ == "__main__":
    main()
