"""Momentum-vs-rotation A/B for the VWAP confluence vote (one-off, offline).

Question (user, 2026-06-16): does flipping the VWAP factor from MOMENTUM
(close>vwap = long) to ROTATION (close>vwap = short, fade back to VWAP) help or
hurt the confluence edge out-of-sample? This is the honest test the in-code NOTE
(confluence/stack.py) flags before the rotation sign is treated as settled.

Method — a clean A/B that isolates ONLY the VWAP sign:
  * Pull 1h OHLCV for a basket of liquid majors via the live router (Binance
    vision mirror).
  * build_levels -> factor_votes (the rotation vote is what the code emits now).
  * Recover BOTH nets from one vote pass: momentum net = rotation net - 2*v_vwap
    (since the momentum vote is exactly the negation of the rotation vote).
  * Apply the SAME validated gate (min_pct 0.5 of n factors, §1) to each net,
    take the confluence direction, and score it two honest ways:
      A) forward-return directional win-rate over an 8-bar horizon, and
      B) run_backtest net + gross (per-bar position model, realistic costs).
  * Everything else (all other votes, threshold, horizon) is identical, so any
    difference is attributable to the VWAP sign alone.

Not the bracket model (limit-retrace/3R) — this is a relative read on the sign,
pooled across symbols for sample size (Tino's point). Run:
    python scripts/compare_vwap_rotation.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kudbee_quant.ingest import load_ohlcv
from kudbee_quant.levels.builder import build_levels
from kudbee_quant.confluence.stack import factor_votes
from kudbee_quant.backtest.engine import BacktestConfig, run_backtest

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT"]
INTERVAL = "1h"
LIMIT = 4000          # ~166 days of 1h bars per symbol
MIN_PCT = 0.5         # §1 validated confluence gate
HORIZON = 8           # forward bars for the directional win-rate measure


def gated_direction(net: pd.Series, n_factors: int, min_pct: float) -> pd.Series:
    """Replicate confluence_position's min_pct path for a given net-score series."""
    strength = net.abs()
    pct = strength / max(n_factors, 1)
    direction = np.sign(net)
    return direction.where(pct >= min_pct, 0.0).astype(float)


def score_symbol(spec: str) -> dict | None:
    try:
        raw = load_ohlcv(spec, interval=INTERVAL, limit=LIMIT)
    except Exception as e:  # network / data — be honest, skip
        print(f"  [skip] {spec}: {e}")
        return None
    if raw is None or len(raw) < 300:
        print(f"  [skip] {spec}: too few bars ({0 if raw is None else len(raw)})")
        return None

    df = build_levels(raw)
    votes = factor_votes(df)
    if "v_vwap" not in votes.columns:
        print(f"  [skip] {spec}: no v_vwap (vwap column absent)")
        return None
    n_factors = votes.shape[1]
    net_rot = votes.sum(axis=1)                 # code emits rotation now
    net_mom = net_rot - 2.0 * votes["v_vwap"]   # momentum = negate the vwap vote

    close = df["close"].astype(float).reset_index(drop=True)
    fwd = close.shift(-HORIZON) / close - 1.0

    out = {"symbol": spec, "bars": len(df), "n_factors": n_factors}
    for tag, net in (("momentum", net_mom), ("rotation", net_rot)):
        direction = gated_direction(net.reset_index(drop=True), n_factors, MIN_PCT)
        traded = direction != 0
        dir_ret = (fwd * direction)[traded].dropna()
        wins = (dir_ret > 0).mean() if len(dir_ret) else np.nan
        bt = run_backtest(df.reset_index(drop=True), direction,
                          BacktestConfig(fee_bps=0.0, slippage_bps=0.0))  # zero-fee venue
        out[tag] = {
            "trades": int(traded.sum()),
            "win_rate": float(wins) if wins == wins else None,
            "mean_dir_ret": float(dir_ret.mean()) if len(dir_ret) else None,
            "total_return_gross": float(bt.equity_curve.iloc[-1] - 1.0),
        }
    return out


def main() -> None:
    print(f"VWAP momentum-vs-rotation A/B  |  {INTERVAL}  |  gate min_pct={MIN_PCT}  "
          f"|  horizon={HORIZON} bars  |  zero-fee\n")
    rows = [r for s in SYMBOLS if (r := score_symbol(s)) is not None]
    if not rows:
        print("\nNo data fetched — cannot report. (Data source unreachable here.)")
        return

    def pool(tag: str, key: str) -> float:
        vals, wts = [], []
        for r in rows:
            v = r[tag].get(key)
            if v is not None:
                vals.append(v); wts.append(r[tag]["trades"])
        if not vals:
            return float("nan")
        return float(np.average(vals, weights=wts)) if sum(wts) else float(np.mean(vals))

    print(f"\n{'symbol':10s} {'bars':>5s} | "
          f"{'MOM win%':>8s} {'MOM ret':>8s} {'MOM n':>6s} | "
          f"{'ROT win%':>8s} {'ROT ret':>8s} {'ROT n':>6s}")
    for r in rows:
        m, t = r["momentum"], r["rotation"]
        print(f"{r['symbol']:10s} {r['bars']:>5d} | "
              f"{(m['win_rate'] or 0)*100:>7.1f}% {(m['total_return_gross'] or 0)*100:>7.2f}% {m['trades']:>6d} | "
              f"{(t['win_rate'] or 0)*100:>7.1f}% {(t['total_return_gross'] or 0)*100:>7.2f}% {t['trades']:>6d}")

    print("\n--- POOLED (trade-weighted) ---")
    print(f"  MOMENTUM: win {pool('momentum','win_rate')*100:5.2f}%  "
          f"mean_dir_ret {pool('momentum','mean_dir_ret')*100:+.3f}%  "
          f"gross_total {sum(r['momentum']['total_return_gross'] for r in rows)*100:+.2f}%  "
          f"trades {sum(r['momentum']['trades'] for r in rows)}")
    print(f"  ROTATION: win {pool('rotation','win_rate')*100:5.2f}%  "
          f"mean_dir_ret {pool('rotation','mean_dir_ret')*100:+.3f}%  "
          f"gross_total {sum(r['rotation']['total_return_gross'] for r in rows)*100:+.2f}%  "
          f"trades {sum(r['rotation']['trades'] for r in rows)}")
    print("\nNOTE: relative read on the VWAP sign only (per-bar model, not the "
          "bracket/3R strategy). Positive separation favors that sign; this is a "
          "screen, not a final validation.")


if __name__ == "__main__":
    main()
