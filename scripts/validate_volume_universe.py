"""Backtest the §B "dynamic volume universe" BEFORE wiring it live.

The owner asked to "scan the top 30-40 pairs with the most liquidity." Our own
evidence cuts against blindly doing that: §48 found the top-100 long tail BLED
(-0.50R/trade) while top-10 majors sat ~breakeven, and the live scorecard shows
even the validated top-10 core is currently net-negative. So this script ANSWERS
the question with data instead of assuming:

  1. Rank the liquid candidate pool (kudbee_quant.universe.CRYPTO_CANDIDATES) by
     mean USD (quote) volume over the lookback window — the real "most liquid" set.
  2. Run the CANONICAL validated confluence bracket on each ranked symbol, net of
     fees, and pool realized-R: IN-SAMPLE (70%) vs OUT-OF-SAMPLE (30%).
  3. Split the ranked universe into CORE (the top-10 by volume) vs the TAIL
     (ranks 11..N — the extra pairs the owner wants to add) and compare pooled
     net-of-fees expectancy. If the tail bleeds, adding it AMPLIFIES losses.
  4. Cross-check with the significance-gated universe harness (validate_frames):
     fraction profitable OOS, median OOS Sharpe, correlation-adjusted effective-N.

No live trading touched, journal untouched. Writes a dated honest report to
docs/research/volume_universe_backtest.md.

Run: PYTHONPATH=. python scripts/validate_volume_universe.py
"""
from __future__ import annotations

import datetime as _dt
import sys
import warnings
from pathlib import Path

import numpy as np

from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
)
from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.ml.labels import trade_outcomes
from kudbee_quant.universe import CRYPTO_CANDIDATES, TOP_10_CRYPTO
from kudbee_quant.universe_rank import rank_by_volume
from kudbee_quant.validation.universe import validate_frames

warnings.filterwarnings("ignore")

LIMIT = 8000           # ~11 months of 1h bars
OOS_FRAC = 0.30
TOP_N = 40             # the owner's "top 30-40"; ranker drops unfetchable tickers
CORE_N = 10            # the validated top-10 majors == the CORE split
RANK_LOOKBACK = 168    # one week of 1h bars for the liquidity ranking
BRK = dict(target_r=TARGET_R, stop_atr=STOP_ATR, limit_retrace_atr=RETRACE_ATR,
           max_bars=MAX_BARS, entry_window=ENTRY_WINDOW, fee_pct=FEE_PCT)


def base_signal(df):
    """The canonical validated entry: >=MIN_PCT confluence, trend-aligned."""
    return confluence_position(df, min_pct=MIN_PCT, trend_align=True)


def reconcile_verdict(core_oos_exp: float, tail_oos_exp: float, *,
                      tail_n: int, core_n: int, harness_robust: bool) -> str:
    """Combine the pooled-R OOS comparison with the significance harness into one
    honest code: ``PAPER`` / ``HOLD`` / ``REJECT``.

    The two must AGREE before we recommend even paper-trading the wider universe.
    A marginally-positive pooled number that the walk-forward/Monte-Carlo harness
    rejects is almost always a single favorable-regime artifact across correlated
    assets, not a real edge — that resolves to HOLD, not PAPER.
    """
    if not (tail_n and core_n):
        return "REJECT"
    pooled_ok = tail_oos_exp > 0 and tail_oos_exp >= core_oos_exp
    if pooled_ok and harness_robust:
        return "PAPER"
    if pooled_ok and not harness_robust:
        return "HOLD"
    return "REJECT"


def _pooled(frames):
    """Pooled (IS, OOS) realized-R arrays over the given {sym: frame}."""
    is_r, oos_r = [], []
    for df in frames.values():
        outc = trade_outcomes(df, base_signal(df), **BRK)
        if outc.empty:
            continue
        cutoff = int(len(df) * (1 - OOS_FRAC))
        eb = outc["entry_bar"].to_numpy()
        r = outc["realized_r"].to_numpy()
        is_r += list(r[eb < cutoff])
        oos_r += list(r[eb >= cutoff])
    return np.array(is_r), np.array(oos_r)


def _stat(r):
    if len(r) == 0:
        return dict(n=0, exp=float("nan"), win=float("nan"), tot=0.0)
    return dict(n=len(r), exp=float(r.mean()), win=float(100 * (r > 0).mean()),
                tot=float(r.sum()))


def _line(tag, s):
    if s["n"] == 0:
        return f"  {tag:<20} n=0"
    return (f"  {tag:<20} n={s['n']:>4}  expectancy={s['exp']:+.4f}R  "
            f"win%={s['win']:4.1f}  totalR={s['tot']:+.1f}")


def main():
    client = BinanceClient()
    out_lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        out_lines.append(s)

    emit("Ranking the liquid candidate pool by mean USD (quote) volume...")
    ranked = rank_by_volume(list(CRYPTO_CANDIDATES), interval="1h",
                            lookback_bars=RANK_LOOKBACK, client=client)
    ranked = ranked[:TOP_N]
    if len(ranked) < CORE_N + 3:
        emit(f"Only {len(ranked)} symbols ranked — not enough to test. Aborting.")
        sys.exit(1)
    ranked_syms = [s for s, _ in ranked]
    emit(f"Ranked {len(ranked_syms)} symbols (most-liquid first):")
    for i, (sym, qv) in enumerate(ranked, 1):
        tag = "  [core]" if i <= CORE_N else ""
        emit(f"   {i:>2}. {sym:<11} avg_quote_vol={qv:,.0f}{tag}")

    emit("\nFetching 1h history + building levels (this takes a minute)...")
    frames = {}
    for sym in ranked_syms:
        try:
            df = client.klines(sym, interval="1h", limit=LIMIT, cache_ttl=86400)
            frames[sym] = build_levels(df)
        except Exception as e:  # noqa: BLE001 — a bad feed must not abort the study
            emit(f"   {sym}: FETCH FAILED ({type(e).__name__})")
    got = [s for s in ranked_syms if s in frames]
    if len(got) < CORE_N + 3:
        emit(f"Only {len(got)} frames loaded — aborting.")
        sys.exit(1)

    core_syms = got[:CORE_N]
    tail_syms = got[CORE_N:]
    core_frames = {s: frames[s] for s in core_syms}
    tail_frames = {s: frames[s] for s in tail_syms}
    all_frames = {s: frames[s] for s in got}

    emit("\n" + "=" * 74)
    emit("POOLED net-of-fees R-expectancy on the canonical validated bracket")
    emit(f"(confluence>={MIN_PCT}, {TARGET_R}R target, {STOP_ATR}-ATR stop, "
         f"maker retrace, fee_pct={FEE_PCT})")
    emit("=" * 74)
    for label, fr in (("CORE (top-10 by vol)", core_frames),
                      (f"TAIL (ranks 11-{len(got)})", tail_frames),
                      (f"ALL (top-{len(got)})", all_frames)):
        i_r, o_r = _pooled(fr)
        emit(f"\n{label}:")
        emit(_line("  IN-SAMPLE", _stat(i_r)))
        emit(_line("  OUT-OF-SAMPLE", _stat(o_r)))

    # The OOS comparison: does the TAIL add or bleed, by pooled R?
    _, core_oos = _pooled(core_frames)
    _, tail_oos = _pooled(tail_frames)
    cs, ts = _stat(core_oos), _stat(tail_oos)
    emit("\n" + "-" * 74)
    if cs["n"] and ts["n"]:
        delta = ts["exp"] - cs["exp"]
        emit(f"OOS pooled expectancy:  core {cs['exp']:+.4f}R   tail {ts['exp']:+.4f}R   "
             f"(tail - core = {delta:+.4f}R)")

    emit("\n" + "=" * 74)
    emit("Significance-gated universe harness (walk-forward + Monte-Carlo) on the TAIL")
    emit("=" * 74)
    rep = None
    try:
        rep = validate_frames(tail_frames, base_signal)
        emit(f"  frac profitable OOS : {rep.frac_profitable_oos:.0%}")
        emit(f"  median OOS Sharpe   : {rep.median_oos_sharpe:.3f}")
        emit(f"  median P(profit)    : {rep.median_oos_prob_profit:.2f}")
        emit(f"  effective N (corr-adj): {rep.effective_n:.1f} of {len(tail_frames)}")
        emit(f"  robust?             : {rep.robust}")
        emit(f"  verdict             : {rep.verdict}")
        for note in rep.notes:
            emit(f"   - {note}")
    except Exception as e:  # noqa: BLE001
        emit(f"  harness error: {type(e).__name__}: {e}")

    # RECONCILED verdict — pooled-R AND the rigorous harness must AGREE before we
    # recommend even paper-trading the tail. A marginally-positive pooled number
    # that the walk-forward/Monte-Carlo harness rejects is almost always a single
    # favorable-regime artifact across correlated assets, not a real edge.
    emit("\n" + "=" * 74)
    emit("RECONCILED VERDICT (pooled-R + significance harness must agree)")
    emit("=" * 74)
    code = reconcile_verdict(cs["exp"], ts["exp"], tail_n=ts["n"], core_n=cs["n"],
                             harness_robust=bool(rep is not None and rep.robust))
    if code == "PAPER":
        emit("  ✅ PAPER IT (tagged experiment). Both the pooled net-of-fees OOS "
             "expectancy AND the walk-forward/Monte-Carlo harness agree the tail "
             "adds edge. Still NOT straight-to-live — run it as a separately-tagged "
             "paper book first (like §C) and revert if forward-negative.")
    elif code == "HOLD":
        emit("  🟡 DO NOT WIRE — pooled R is marginally positive OOS but the "
             "significance harness REJECTS it (not robust): the tail's apparent "
             "gain is concentrated in a few correlated assets over one OOS regime, "
             "not a stable cross-asset edge. Keep the validated top-10 only. "
             "Re-test on more history / across regimes before reconsidering.")
    else:
        emit("  🛑 DO NOT WIRE — the wider universe does not beat the validated "
             "top-10 net of fees. This matches §48 (the long tail bled). Keep "
             "the top-10-only live book.")

    # Write the dated report.
    stamp = _dt.date.today().isoformat()
    report = Path("docs/research/volume_universe_backtest.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(out_lines)
    report.write_text(
        f"# Volume-ranked universe — backtest before wiring (run {stamp})\n\n"
        "The owner asked to scan the top 30-40 most-liquid pairs. This is the "
        "backtest-first answer (per our honesty rule: not validated unless a test "
        "backs it). Static validated forward book = `TOP_10_CRYPTO`; this study "
        "only measures whether the WIDER ranked universe adds edge.\n\n"
        f"```\n{body}\n```\n"
    )
    emit(f"\nWrote {report}")
    emit("Done. (No live trading touched; data/journal.json untouched.)")


if __name__ == "__main__":
    main()
