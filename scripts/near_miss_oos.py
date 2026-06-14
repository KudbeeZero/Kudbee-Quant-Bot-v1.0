"""STEP 4 — OUT-OF-SAMPLE discipline for the near-miss autopsy.

The in-sample autopsy (scripts/near_miss_autopsy.py) ran on the ~5-day forward
journal (one regime, n~118). That is NOT enough to trust a config change. Here we
re-ask the SAME questions on a long 1h history via the project's walk-forward
bracket harness, scoring ONLY out-of-sample folds, so an in-sample-only win is
exposed as overfit.

Questions:
  Q1  Does OOS expectancy IMPROVE as the confluence threshold rises 0.5->0.6->0.7?
      (If yes, dropping the low bands generalises; if the 0.6 gate is no better
      than 0.5 OOS, the in-sample 'drop 60%' win was regime luck.)
  Q2  Does a LOWER target rescue the low band OOS, or is it structurally negative
      at every target (the in-sample finding)?
  Q3  Does trend-alignment (price vs 800-EMA) help the marginal band?

Cost: reported at a believable round-trip fee_r; the autopsy's live book is taker-
poisoned on sub-hourly TFs (MEMORY §35/§37), so 1h is the fair OOS venue.
"""
from __future__ import annotations

import statistics


from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.router import load_ohlcv
from kudbee_quant.levels import build_levels
from kudbee_quant.validation.bracket_validation import walkforward_bracket

# Walk-forward validated majors (MEMORY §1) — the honest OOS universe.
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
INTERVAL = "1h"
LIMIT = 4000          # ~166 days of 1h
FOLDS = 6
FEE_R = 0.05          # believable 1h round-trip in R (sensitivity noted separately)


def build_frames() -> dict:
    frames = {}
    for s in SYMBOLS:
        try:
            frames[s] = build_levels(load_ohlcv(s, interval=INTERVAL, limit=LIMIT))
            print(f"  built {s}: {len(frames[s])} bars")
        except Exception as e:
            print(f"  ! {s}: {type(e).__name__}: {e}")
    return frames


def evaluate(frames: dict, min_pct: float, target_r: float, trend_align: bool,
             fee_r: float = FEE_R) -> dict:
    """Aggregate OOS cells across asset x fold for one (threshold, target) config."""
    exps, totals, trades = [], 0.0, 0
    pos = 0
    for df in frames.values():
        sig = confluence_position(df, min_pct=min_pct, trend_align=trend_align)
        for cell in walkforward_bracket(df, sig, FOLDS, target_r=target_r, fee_r=fee_r):
            if not cell["sufficient"]:
                continue
            exps.append(cell["expectancy_r"])
            totals += cell["total_r"]
            trades += cell["n_trades"]
            pos += cell["expectancy_r"] > 0
    n = len(exps)
    return {
        "min_pct": min_pct, "target_r": target_r, "trend": trend_align,
        "cells": n, "trades": trades,
        "frac_pos": (pos / n) if n else float("nan"),
        "median_exp": statistics.median(exps) if exps else float("nan"),
        "mean_exp": (sum(exps) / n) if n else float("nan"),
        "total_r": totals,
    }


def _print(rows: list[dict], title: str) -> None:
    print(f"\n{title}")
    print(f"  {'thr':>4}{'tgt':>5}{'trend':>7}{'cells':>6}{'trades':>7}"
          f"{'frac+':>7}{'medExp':>8}{'totR':>8}")
    for r in rows:
        print(f"  {r['min_pct']:>4.2f}{r['target_r']:>5.1f}{str(r['trend']):>7}"
              f"{r['cells']:>6}{r['trades']:>7}{r['frac_pos']*100:>6.0f}%"
              f"{r['median_exp']:>8.3f}{r['total_r']:>8.1f}")


if __name__ == "__main__":
    print(f"building {len(SYMBOLS)} frames ({INTERVAL}, {LIMIT} bars)...")
    frames = build_frames()
    print(f"OOS: {FOLDS} folds/asset, fee_r={FEE_R}\n" + "=" * 64)

    # Q1: threshold sweep at the live 3R target.
    q1 = [evaluate(frames, p, 3.0, False) for p in (0.4, 0.5, 0.6, 0.7)]
    _print(q1, "Q1 — threshold sweep @ 3R (does higher confluence => better OOS?)")

    # Q2: target sweep at the 0.5 and 0.6 gates.
    q2 = [evaluate(frames, p, t, False)
          for p in (0.5, 0.6) for t in (1.5, 2.0, 3.0)]
    _print(q2, "Q2 — target sweep @ 0.5 and 0.6 gates (does lower target rescue?)")

    # Q3: trend-alignment at the marginal gates.
    q3 = [evaluate(frames, p, 3.0, ta) for p in (0.5, 0.6) for ta in (False, True)]
    _print(q3, "Q3 — trend-align on/off @ 3R")

    # Cost sensitivity on the key cell (0.6 gate, 3R).
    print("\ncost sensitivity @ 0.6 gate, 3R (median OOS expectancy by fee_r):")
    for f in (0.0, 0.02, 0.05, 0.10):
        r = evaluate(frames, 0.6, 3.0, False, fee_r=f)
        print(f"  fee_r={f:.2f}  medExp={r['median_exp']:+.3f}  frac+={r['frac_pos']*100:.0f}%")
