"""Evaluate the meta-labeling model honestly, OUT-OF-SAMPLE.

Builds the meta dataset (primary confluence signals -> did the trade reach the
target before the stop), runs purged + embargoed walk-forward CV, and prints the
gradient-boosted-tree and logistic results with Wilson CIs. The headline test:
does gating on the meta-probability raise the win-rate ABOVE the base rate with a
confidence interval that clears it? If not, the meta-model is not (yet) an edge —
and this prints that verdict plainly.

Usage:  python scripts/meta_eval.py --target-r 3.0
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kudbee_quant.universe import TOP_10_CRYPTO  # noqa: E402

UNIVERSE = list(TOP_10_CRYPTO)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--target-r", type=float, default=3.0)
    ap.add_argument("--n-splits", type=int, default=6)
    args = ap.parse_args()

    from kudbee_quant.confluence.stack import confluence_position
    from kudbee_quant.ingest import load_ohlcv
    from kudbee_quant.levels import build_levels
    from kudbee_quant.ml import build_dataset
    from kudbee_quant.ml.meta_model import evaluate

    frames = {s: build_levels(load_ohlcv(s, interval=args.interval, limit=args.limit))
              for s in UNIVERSE}
    sig = lambda d: confluence_position(d, min_pct=0.5, trend_align=True)
    X, y, meta = build_dataset(frames, sig, target_r=args.target_r)
    print(f"dataset: {X.shape} trades, base win-rate(@{args.target_r}R) "
          f"{float(y.mean()):.3f}, signal-bars {meta.attrs.get('n_signal_bars')}")
    report = evaluate(X, y, meta, thresholds=(0.5, 0.55, 0.6, 0.65), n_splits=args.n_splits)
    print(json.dumps(report, indent=2))
    # Plain-English verdict — EXPECTANCY is the metric that matters, not hit-rate.
    sig = any(g.get("significant") for m in report["models"].values()
              if isinstance(m, dict) for g in m.get("expectancy_gate", []))
    print("\nVERDICT:", "meta-gating SIGNIFICANTLY lifts OOS expectancy (permutation "
          "p<0.05) at some threshold — a real LEAD; validate on uncorrelated assets "
          "+ forward paper before trusting." if sig else
          "no threshold significantly lifts OOS expectancy — not an edge yet.")


if __name__ == "__main__":
    main()
