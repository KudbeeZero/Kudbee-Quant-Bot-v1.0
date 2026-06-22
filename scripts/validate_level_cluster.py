"""Confirmation deep-dive on the LEVEL-CLUSTER lead (MEMORY §62 addendum).

The overnight harness flagged `level_cluster` (>=3 independent levels stacking
within 0.2 ATR of price) as SUGGESTIVE: +0.11R over baseline, both halves
positive, ~3x expectancy. This script stress-tests it honestly before it could
earn a paper book — three passes, all net of fees on real Binance 1h data:

  PASS 1  Confirmation on ~3x history + grid over threshold K (>=2..>=5) and
          tolerance (0.15/0.20/0.25 ATR): does >=3 hold? does >=4 stop being thin?
  PASS 2  Ablation — drop each level-source group and see how much the edge
          depends on it (M-levels / pivots / opens / prior H-L / prev-day-opens / …).
  PASS 3  Robustness — per-symbol OOS (last 30%), pooled IS/OOS, and a bootstrap
          p-value vs the baseline. Final KEEP/PAPER/REVERT verdict.

No live trading touched, journal untouched. Writes docs/research/level_cluster_confirm.md.
Run: PYTHONPATH=. python scripts/validate_level_cluster.py
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import numpy as np

from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
)
from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.ml.labels import trade_outcomes
from kudbee_quant.universe import TOP_10_CRYPTO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab_indicators import level_cluster  # noqa: E402

LIMIT = 12000          # ~3x the overnight default (~16 months of 1h bars)
OOS_FRAC = 0.30
BRK = dict(target_r=TARGET_R, stop_atr=STOP_ATR, limit_retrace_atr=RETRACE_ATR,
           max_bars=MAX_BARS, entry_window=ENTRY_WINDOW, fee_pct=FEE_PCT)
GROUPS = ("mlevel", "pivot", "open", "prior", "range", "vwap", "round", "prevopen")
_RNG = np.random.default_rng(7)


def base_signal(df):
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True)


def _pool(frames, gate_fn):
    """Pooled (IS, OOS) realized-R for base entries kept where gate_fn(df) is True
    (gate_fn=None => the unfiltered baseline)."""
    is_r, oos_r = [], []
    for df in frames.values():
        sig = base_signal(df)
        if gate_fn is not None:
            keep = gate_fn(df).reindex(sig.index).fillna(False)
            sig = sig.where(keep, 0.0)
        outc = trade_outcomes(df, sig, **BRK)
        if outc.empty:
            continue
        cut = int(len(df) * (1 - OOS_FRAC))
        eb, r = outc["entry_bar"].to_numpy(), outc["realized_r"].to_numpy()
        is_r += list(r[eb < cut]); oos_r += list(r[eb >= cut])
    return np.array(is_r), np.array(oos_r)


def _exp(r):
    return float(r.mean()) if len(r) else float("nan")


def _boot_p(base, cand, n=2000):
    """One-sided bootstrap: P(candidate does NOT beat baseline) under resampling."""
    if len(base) == 0 or len(cand) == 0:
        return 1.0
    obs = cand.mean() - base.mean()
    pool = np.concatenate([base, cand])
    nb, nc = len(base), len(cand)
    worse = 0
    for _ in range(n):
        s = _RNG.choice(pool, nb + nc, replace=True)
        if (s[nb:].mean() - s[:nb].mean()) >= obs:
            worse += 1
    return worse / n


def main():
    out = []
    def emit(s=""):
        print(s, flush=True); out.append(s)

    client = BinanceClient()
    emit(f"Loading {len(TOP_10_CRYPTO)} symbols @ 1h, limit={LIMIT} ...")
    frames = {}
    for s in TOP_10_CRYPTO:
        try:
            frames[s] = build_levels(client.klines(s, interval="1h", limit=LIMIT, cache_ttl=86400))
        except Exception as e:  # noqa: BLE001
            emit(f"  {s}: FETCH FAILED ({type(e).__name__})")
    if len(frames) < 5:
        emit("Not enough data; aborting."); sys.exit(1)
    bi, bo = _pool(frames, None)
    base_exp_is, base_exp_oos = _exp(bi), _exp(bo)
    emit(f"Baseline: IS {base_exp_is:+.4f}R (n={len(bi)})  OOS {base_exp_oos:+.4f}R (n={len(bo)})")

    # ---- PASS 1: threshold x tolerance grid -------------------------------
    emit("\n" + "=" * 72)
    emit("PASS 1 — threshold (K stacked) x tolerance grid, OOS net-of-fees ΔR")
    emit("=" * 72)
    emit(f"  {'tol':>5} {'K':>3} {'OOS_exp':>9} {'ΔR':>9} {'n':>6}  verdict")
    best = None
    for tol in (0.15, 0.20, 0.25):
        for k in (2, 3, 4, 5):
            gate = (lambda df, t=tol, kk=k: level_cluster(df, tol_atr=t) >= kk)
            _, o = _pool(frames, gate)
            d = _exp(o) - base_exp_oos
            tag = "thin" if len(o) < 120 else ("+" if d > 0 else "-")
            emit(f"  {tol:>5.2f} {k:>3} {_exp(o):>+9.4f} {d:>+9.4f} {len(o):>6}  {tag}")
            if len(o) >= 120 and (best is None or d > best[3]):
                best = (tol, k, _exp(o), d, len(o))
    if best:
        emit(f"\n  Best non-thin OOS cell: tol={best[0]} K>={best[1]} -> "
             f"{best[2]:+.4f}R (ΔR {best[3]:+.4f}, n={best[4]})")

    # ---- PASS 2: source ablation (at the headline tol=0.20, K>=3) ----------
    emit("\n" + "=" * 72)
    emit("PASS 2 — source ablation (tol=0.20, K>=3): drop one group, watch OOS ΔR")
    emit("=" * 72)
    full_gate = lambda df: level_cluster(df, tol_atr=0.20) >= 3
    _, full_o = _pool(frames, full_gate)
    full_d = _exp(full_o) - base_exp_oos
    emit(f"  {'dropped':>10} {'OOS_exp':>9} {'ΔR':>9} {'n':>6} {'edge kept':>10}")
    emit(f"  {'(none)':>10} {_exp(full_o):>+9.4f} {full_d:>+9.4f} {len(full_o):>6} {'100%':>10}")
    for g in GROUPS:
        gate = (lambda df, gg=g: level_cluster(df, tol_atr=0.20, exclude_groups={gg}) >= 3)
        _, o = _pool(frames, gate)
        d = _exp(o) - base_exp_oos
        kept = (d / full_d * 100) if full_d else float("nan")
        emit(f"  {g:>10} {_exp(o):>+9.4f} {d:>+9.4f} {len(o):>6} {kept:>9.0f}%")

    # ---- PASS 3: robustness — per-symbol OOS + bootstrap p -----------------
    emit("\n" + "=" * 72)
    emit("PASS 3 — robustness at tol=0.20, K>=3: per-symbol OOS + bootstrap p")
    emit("=" * 72)
    gate = lambda df: level_cluster(df, tol_atr=0.20) >= 3
    pos = 0; tot = 0
    for s, df in frames.items():
        _, o = _pool({s: df}, gate)
        _, bo_s = _pool({s: df}, None)
        if len(o) >= 10:
            tot += 1; pos += int(_exp(o) > _exp(bo_s))
    ci, co = _pool(frames, gate)
    p_is = _boot_p(bi, ci)
    p_oos = _boot_p(bo, co)
    emit(f"  per-symbol OOS beats baseline: {pos}/{tot} symbols")
    emit(f"  pooled IS  ΔR {_exp(ci) - base_exp_is:+.4f} (n={len(ci)})  bootstrap p={p_is:.4f}")
    emit(f"  pooled OOS ΔR {_exp(co) - base_exp_oos:+.4f} (n={len(co)})  bootstrap p={p_oos:.4f}")
    both_halves = (_exp(ci) > base_exp_is) and (_exp(co) > base_exp_oos)

    # ---- verdict ----------------------------------------------------------
    emit("\n" + "=" * 72)
    emit("VERDICT")
    emit("=" * 72)
    winner = both_halves and p_oos < 0.05 and pos >= max(3, int(0.6 * tot))
    if winner:
        emit("  ✅ CONFIRMED on 3x history: both halves positive, p<0.05 OOS, and it "
             "holds across most symbols. Graduate to a SEPARATELY-TAGGED PAPER BOOK "
             "(not the live book) to accrue a forward record.")
    elif both_halves and p_oos < 0.15:
        emit("  🟡 STILL SUGGESTIVE on 3x history (both halves +, p borderline). Worth a "
             "paper book to gather forward trades, but not yet a luck-proof WINNER.")
    else:
        emit("  🔴 DID NOT CONFIRM on 3x history — the SUGGESTIVE read didn't survive "
             "more data. Keep top-10 baseline; do not wire or paper it.")

    stamp = _dt.date.today().isoformat()
    rep = Path("docs/research/level_cluster_confirm.md")
    rep.write_text(f"# Level-cluster confirmation (run {stamp})\n\n```\n" +
                   "\n".join(out) + "\n```\n")
    emit(f"\nWrote {rep}")
    emit("Done. (No live trading touched; data/journal.json untouched.)")


if __name__ == "__main__":
    main()
