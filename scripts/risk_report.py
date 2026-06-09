"""Risk / leverage report for the validated strategy — and the QUANTIFIED payoff
of KudbeeX's fast-fail early-exit (§21) on safe leverage.

Builds the real per-trade R + adverse-move distribution across the top-10 (1h),
then prints Kelly, risk-of-ruin, optimal-f, and the perp MAX-SAFE-LEVERAGE — for
the baseline vs the show-me early exit — so we can see, in one number, how much
cutting the loss tail raises the leverage you can survive.

Usage:  python scripts/risk_report.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    import numpy as np

    from kudbee_quant import risk
    from kudbee_quant.confluence.stack import confluence_position
    from kudbee_quant.ingest import load_ohlcv
    from kudbee_quant.levels import build_levels
    from kudbee_quant.ml.labels import trade_outcomes
    from kudbee_quant.universe import TOP_10_CRYPTO

    frames = {s: build_levels(load_ohlcv(s, interval="1h", limit=4000)) for s in TOP_10_CRYPTO}

    def distribution(mae_giveup=None):
        R, adverse = [], []
        for d in frames.values():
            sig = confluence_position(d, min_pct=0.5, trend_align=True)
            t = trade_outcomes(d, sig, mae_giveup=mae_giveup)   # exit-aware R + MAE
            R += t["realized_r"].tolist()
            adverse += t["adverse_pct"].tolist()
        return np.asarray(R, float), np.asarray(adverse, float)

    print("=== Validated strategy risk/leverage report (top-10, 1h) ===\n")
    for label, giveup in (("BASELINE (1.5 stop / 3R)", None),
                          ("FAST-FAIL show-me (exit if not +0.5R by bar 3)", (3, 0.0, 0.5))):
        R, adverse = distribution(giveup)
        s = risk.summary(R, adverse_moves=adverse, n_trades=len(R), alpha=0.01, mmr=0.005)
        print(f"-- {label}")
        print(f"   n={s['n_trades']}  meanR={s['mean_r']:+.4f}  stdR={s['std_r']:.3f}")
        print(f"   Kelly f*={s['kelly_full']:.3f}  (¼-Kelly risk/trade={s['risk_per_trade_frac']*100:.2f}%)"
              f"  optimal_f={s['optimal_f']:.3f}")
        print(f"   RoR(¼-Kelly, 50% DD)={s['ror_quarter_kelly']*100:.2f}%")
        print(f"   MAX SAFE LEVERAGE (P(liq)<1% over {s['n_trades']} trades) = {s['max_safe_leverage']:.1f}x\n")
    print("Read: compare the two MAX SAFE LEVERAGE numbers — the gap is the leverage")
    print("headroom the fast-fail rule buys you by shrinking the loss tail. 20x is")
    print("almost certainly above both ceilings; size to the number, not the dial.")


if __name__ == "__main__":
    main()
