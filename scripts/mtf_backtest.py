"""Multi-timeframe MTF backtest — STANDALONE, read-only.

Hypothesis line: take a lower-TF PVSRA climax CONTRARIAN to the spike but WITH the
higher-TF EMA trend (long a bear climax in an up-bias; short a bull climax in a
down-bias). The higher-TF bias is merged onto the entry bars CAUSALLY — an entry
decision at time t may use only the higher-TF bar that has ALREADY CLOSED at/before
t, never the forming one (the merge that makes or breaks an MTF study).

Runs a 2x2 matrix: {15m entry / 30m bias, 2h entry / 4h bias} x {full-ride 3R,
TP1 scale-out (half at 1.5R + breakeven, rest to 3R)}.

Does NOT touch live trading, the validated stack, the workflow, or the journal.
Run: PYTHONPATH=. python scripts/mtf_backtest.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from kudbee_quant.backtest.bracket import bracket_backtest
from kudbee_quant.config.validated_defaults import MAX_BARS, STOP_ATR, TAKER_FEE_PCT, TARGET_R
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.ingest.resample import resample_ohlcv
from kudbee_quant.levels import build_levels
from kudbee_quant.signals.pvsra import pvsra_vector_candles
from kudbee_quant.universe import TOP_10_CRYPTO

sys.path.insert(0, os.path.dirname(__file__))
from overnight_research import _bootstrap_p, _pool_expectancy  # noqa: E402

FEE_PCT = TAKER_FEE_PCT    # MARKET entry on the climax -> taker cost is the honest fee

# (label, entry interval, fetch limit, entry minutes, bias resample rule, bias minutes)
TIMEFRAMES = [
    ("15m/30m", "15m", 16000, 15, "30min", 30),
    ("2h/4h",   "2h",   6000, 120, "4h",   240),
]
# (label, bracket exit kwargs)
EXITS = [
    ("full-ride 3R",        {"target_r": TARGET_R}),
    ("scale-out 1.5R/3R",   {"tp1_r": 1.5, "tp1_frac": 0.5, "be_after_tp1": True,
                             "target_r": TARGET_R}),
]


def compute_bias(dfb: pd.DataFrame) -> pd.Series:
    """+1 when ema_5>ema_13>ema_50 (stacked up), -1 when stacked down, else 0."""
    e5, e13, e50 = dfb["ema_5"], dfb["ema_13"], dfb["ema_50"]
    up = (e5 > e13) & (e13 > e50)
    dn = (e5 < e13) & (e13 < e50)
    return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=dfb.index).astype(float)


def causal_bias_merge(lv: pd.DataFrame, dfb: pd.DataFrame,
                      entry_minutes: int = 15, bias_minutes: int = 30) -> pd.DataFrame:
    """Align ``dfb['bias30']`` onto the entry frame WITHOUT lookahead.

    A higher-TF bar at ``timestamp`` T closes at T+bias_minutes; an entry bar at
    ``timestamp`` t decides at t+entry_minutes. We backward-asof-join so each entry
    decision picks the most recent higher-TF bar that has ALREADY CLOSED at/before
    the decision — never the forming one. Returns ``lv`` (original order) + ``bias30``.
    """
    left = lv.copy()
    left["decision_time"] = pd.to_datetime(left["timestamp"], utc=True) + pd.Timedelta(minutes=entry_minutes)
    right = dfb[["timestamp", "bias30"]].copy()
    right["close_time"] = pd.to_datetime(right["timestamp"], utc=True) + pd.Timedelta(minutes=bias_minutes)
    right = right[["close_time", "bias30"]].sort_values("close_time")
    merged = pd.merge_asof(
        left.sort_values("decision_time").reset_index(drop=True),
        right, left_on="decision_time", right_on="close_time", direction="backward",
    )
    merged["bias30"] = merged["bias30"].fillna(0.0)
    return merged


def mtf_signal(frame: pd.DataFrame) -> pd.Series:
    """CONTRARIAN: FADE the climax in the direction of the higher-TF trend.
    +1 (long) on a BEAR climax during an up-bias; -1 (short) on a BULL climax
    during a down-bias."""
    vec = frame["vector"]
    bias = frame["bias30"]
    long_ = (vec == "bear_climax") & (bias > 0)
    short_ = (vec == "bull_climax") & (bias < 0)
    return pd.Series(np.where(long_, 1.0, np.where(short_, -1.0, 0.0)), index=frame.index)


def prep_symbol(client: BinanceClient, symbol: str, entry_tf: str, limit: int,
                entry_min: int, bias_rule: str, bias_min: int):
    """Fetch + build + signal once for a (symbol, timeframe). Returns (frame, signal)."""
    df = client.klines(symbol, interval=entry_tf, limit=limit, cache_ttl=86400)
    dfb = build_levels(resample_ohlcv(df, bias_rule))
    dfb = dfb.assign(bias30=compute_bias(dfb))
    lv = pvsra_vector_candles(build_levels(df))
    frame = causal_bias_merge(lv, dfb, entry_min, bias_min)
    return frame, mtf_signal(frame)


def eval_exit(frame: pd.DataFrame, sig: pd.Series, exit_kw: dict) -> list:
    """Per-trade R for one exit config (chronological)."""
    res = bracket_backtest(frame, sig, stop_atr=STOP_ATR, max_bars=MAX_BARS,
                           fee_pct=FEE_PCT, limit_retrace_atr=None, **exit_kw)
    return list(res.trades)


def _summary(label: str, trades: list, h1: list, h2: list):
    n, exp, win = _pool_expectancy(trades)
    _, e1, _ = _pool_expectancy(h1)
    _, e2, _ = _pool_expectancy(h2)
    p = _bootstrap_p([0.0] * len(trades), trades) if n else 1.0
    edge = exp > 0 and e1 > 0 and e2 > 0 and p < 0.05
    verdict = "✅ EDGE" if edge else "🔴 NOT AN EDGE"
    print(f"  {label:<20} n={n:>5}  exp={exp:+.4f}R  win={100*win:4.1f}%  "
          f"h1={e1:+.4f} h2={e2:+.4f}  p={p:.3f}  {verdict}")


def main():
    client = BinanceClient()
    print(f"Contrarian MTF backtest — {len(TOP_10_CRYPTO)} majors, market entry, "
          f"taker fee={FEE_PCT}, stop={STOP_ATR}ATR, max_bars={MAX_BARS}\n")

    for tf_label, entry_tf, limit, entry_min, bias_rule, bias_min in TIMEFRAMES:
        print("=" * 78)
        print(f"TIMEFRAME {tf_label}  (entry {entry_tf}, bias {bias_rule}, "
              f"max_bars={MAX_BARS} = {MAX_BARS*entry_min/60:.0f}h horizon)")
        print("=" * 78)
        preps = {}
        for s in TOP_10_CRYPTO:
            try:
                preps[s] = prep_symbol(client, s, entry_tf, limit, entry_min, bias_rule, bias_min)
            except Exception as e:  # noqa: BLE001
                print(f"  {s}: PREP FAILED ({type(e).__name__}: {e})")
        # per-symbol (both exits side by side)
        print(f"  {'symbol':<10} {'n':>5} {'fullR':>9} {'scaleR':>9}")
        pooled = {lbl: [] for lbl, _ in EXITS}
        halves = {lbl: ([], []) for lbl, _ in EXITS}
        for s, (frame, sig) in preps.items():
            row = [s]
            n_show = None
            for lbl, kw in EXITS:
                t = eval_exit(frame, sig, kw)
                pooled[lbl] += t
                mid = len(t) // 2
                halves[lbl][0].extend(t[:mid]); halves[lbl][1].extend(t[mid:])
                _, exp, _ = _pool_expectancy(t)
                row.append(exp); n_show = len(t)
            print(f"  {s:<10} {n_show:>5} {row[1]:>+9.4f} {row[2]:>+9.4f}")
        print()
        for lbl, _ in EXITS:
            _summary(lbl, pooled[lbl], halves[lbl][0], halves[lbl][1])
        print()


if __name__ == "__main__":
    main()
