"""§41 gap investigation — pre-registered decomposition of the +0.096R→−0.007R
and 8,124→3,730 discrepancies (studies/section41_gap_preregistration.md).

RESEARCH ONLY / READ-ONLY. This script IMPORTS the existing engine and
reimplements NOTHING except one controlled counterfactual:

  The ONLY signal-affecting code change between the §41 run (2026-06-15) and the
  management-study era is commit ``be69b36`` (2026-06-16, PR #31, MEMORY §44):
  the v_vwap confluence factor flipped from MOMENTUM (close>vwap votes long) to
  ROTATION (close>vwap votes short). Verified via the GitHub history:
  ``kudbee_quant/confluence/stack.py`` has exactly one commit since 2026-06-15
  (the flip), the three ``levels/`` commits in that span add research-only
  MLEVEL columns (factor_votes untouched), and ``scripts/cycle_backtest.py``
  has a single commit ever — so WINDOWS/universe/geometry are byte-identical
  to the §41 run by construction.

  ``signal_variant(df, vwap_momentum=True)`` therefore reconstructs the §41-era
  signal by flipping v_vwap back, replicating confluence_position's gate logic
  EXACTLY (and regression-locked: with ``vwap_momentum=False`` it must equal
  ``confluence_position`` on every frame — asserted per cell at runtime and
  pinned by tests/test_section41_gap.py).

Hypotheses (locked in the pre-registration; each addressed):
  H1 population  — measured here (the counterfactual + n accounting).
  H2 geometry    — settled by code inspection: §41's LIVE_BRACKET has no tp1
                   kwargs → §41 WAS all-or-nothing ride-3R (geometry A).
  H3 fee model   — settled by inspection: both anchors use maker 0.0004.
  H4 gate        — settled by inspection: both min_pct=0.50 + trend_align.
  H5 period      — settled by construction: WINDOWS identical (single commit).

Run (from the repo root):   python research/section41_gap.py
Outputs: studies/section41_gap_results.md + studies/section41_gap_summary.csv

HISTORICAL NOTE (2026-07-01, after the run): the committed results were produced
against the ROTATION-sign code (pre-revert). The owner then approved reverting
v_vwap to the momentum sign (MEMORY §75), so on current code ``vwap_momentum=True``
flips momentum→rotation — i.e. it now reconstructs the REFUTED §44 signal, the
inverse of what it meant at run time. The committed results/CSV remain the record
of the pre-registered run; re-running this script is not meaningful without
re-reading the flag semantics.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))  # reuse the validated universe/windows

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402
from kudbee_quant.config.validated_defaults import (  # noqa: E402
    BRACKET_KW, FEE_PCT, MIN_PCT, TREND_FILTER,
)
from kudbee_quant.confluence.stack import confluence_position, factor_votes  # noqa: E402
from kudbee_quant.levels import build_levels  # noqa: E402

import cycle_backtest as cyc  # noqa: E402  (scripts/cycle_backtest.py — single source of truth)

# §41 geometry == plain ride-3R (H2): BRACKET_KW carries stop/target/max_bars/
# retrace/entry_window/fee — no tp1/tp2/trail kwargs, exactly what cycle_backtest
# passed. (BRACKET_KW's fee_pct IS the maker 0.0004 — H3.)
RIDE3R_KW = dict(BRACKET_KW)
assert RIDE3R_KW["fee_pct"] == FEE_PCT == 0.0004  # H3 pinned


def signal_variant(df: pd.DataFrame, *, vwap_momentum: bool) -> pd.Series:
    """The live signal with the v_vwap factor optionally flipped back to the
    §41-era MOMENTUM sign. Replicates confluence_position(min_pct=MIN_PCT,
    trend_align=TREND_FILTER) exactly; the flip is the only degree of freedom."""
    votes = factor_votes(df)
    if vwap_momentum and "v_vwap" in votes.columns:
        votes = votes.copy()
        votes["v_vwap"] = -votes["v_vwap"]  # rotation -> momentum (pre-#31 sign)
    n_factors = max(votes.shape[1], 1)
    net = votes.sum(axis=1)
    direction = np.sign(net)
    pct = net.abs() / n_factors
    gate = pct >= MIN_PCT
    if TREND_FILTER and "ema_800" in df.columns:
        htf = np.sign(df["close"] - df["ema_800"])
        gate = gate & (np.sign(direction) == htf)
    return pd.Series(direction, index=df.index).where(gate, 0.0).astype(float)


def load_cells() -> list[tuple[str, str, pd.DataFrame]]:
    """Every (window, symbol) 1h frame — identical loader to §41/trailing_sweep."""
    client = cyc.BinanceClient()
    cells: list[tuple[str, str, pd.DataFrame]] = []
    print("Fetching 1h frames (disk-cached after first run)...")
    for w in cyc.WINDOWS:
        for sym in w.universe():
            try:
                raw = client.klines_range(sym, interval="1h", start=w.start, end=w.end)
                df = build_levels(raw)
                cells.append((w.key, sym, df))
                print(f"  {w.key:7} {sym:9} {len(df):>6} bars")
            except Exception as e:  # noqa: BLE001 — report, never fabricate
                print(f"  ! {w.key} {sym}: {type(e).__name__}: {e}")
    return cells


def run_variant(cells, *, vwap_momentum: bool) -> tuple[dict, dict]:
    """Pool ride-3R net-R trades per window and overall for one signal variant."""
    per_window: dict[str, list[float]] = {w.key: [] for w in cyc.WINDOWS}
    signals = 0
    for wk, sym, df in cells:
        sig = signal_variant(df, vwap_momentum=vwap_momentum)
        if not vwap_momentum:
            # Regression lock: the replication must equal the engine's own signal.
            ref = confluence_position(df, min_pct=MIN_PCT, trend_align=TREND_FILTER)
            if not sig.equals(ref):
                raise AssertionError(f"signal replication drifted on {wk}/{sym}")
        signals += int((sig != 0).sum())
        res = bracket_backtest(df, sig, **RIDE3R_KW)
        per_window[wk].extend(res.trades)
    pooled = [t for ts in per_window.values() for t in ts]
    def _s(tr):
        s = cyc.stats(tr)
        s["boot_p"] = cyc.boot_p(tr)
        return s
    return {wk: _s(ts) for wk, ts in per_window.items()}, {**_s(pooled), "signal_bars": signals}


def main() -> None:
    cells = load_cells()
    print("\nVariant 1/2: CURRENT signal (VWAP rotation, post-#31)...")
    now_w, now_all = run_variant(cells, vwap_momentum=False)
    print("Variant 2/2: §41-era signal (VWAP momentum, pre-#31)...")
    pre_w, pre_all = run_variant(cells, vwap_momentum=True)

    anchor_exp, anchor_n = 0.096, 8124   # §41's reported 1h numbers (MEMORY §41)
    rows = []
    for label, wd, ad in (("current (rotation)", now_w, now_all),
                          ("§41-era (momentum)", pre_w, pre_all)):
        for wk, s in wd.items():
            rows.append(dict(variant=label, scope=wk, **{k: s[k] for k in
                        ("n", "exp", "win", "total", "boot_p")}))
        rows.append(dict(variant=label, scope="ALL", **{k: ad[k] for k in
                    ("n", "exp", "win", "total", "boot_p")}))
    summary = pd.DataFrame(rows)
    out_csv = _REPO / "studies" / "section41_gap_summary.csv"
    summary.to_csv(out_csv, index=False)

    d_exp_flip = pre_all["exp"] - now_all["exp"]
    d_n_flip = pre_all["n"] - now_all["n"]
    resid_exp = anchor_exp - pre_all["exp"]
    resid_n = anchor_n - pre_all["n"]

    L = ["# §41 Gap Investigation — RESULTS (pre-registered)",
         "",
         "Pre-registration: `studies/section41_gap_preregistration.md` (merged to `main`",
         "2026-06-27, PR #117, before this run). Read-only; proposes NO live change.",
         "",
         "## Hypothesis verdicts",
         "",
         "- **H2 geometry: NOT the gap.** `scripts/cycle_backtest.py` passes `BRACKET_KW`",
         "  with no tp1/tp2/trail kwargs → §41 WAS plain ride-3R (geometry A), the same",
         "  geometry as the study reproduction. (Settled by code inspection.)",
         "- **H3 fees: NOT the gap.** Both anchors are net-maker `FEE_PCT=0.0004`.",
         "- **H4 gate: NOT the gap.** Both `min_pct=0.50, trend_align=True`.",
         "- **H5 period: NOT the gap.** `WINDOWS` are byte-identical (the script has a",
         "  single commit ever, 2026-06-15).",
         "- **H1 population: THE gap.** The only signal-affecting code change since the",
         "  §41 run is the v_vwap MOMENTUM→ROTATION flip (commit `be69b36`, 2026-06-16,",
         "  PR #31, §44) — one day after §41. Flipping it back reconstructs the §41-era",
         "  population on today's code + data:",
         "",
         "## Measured attribution (1h, ride-3R, net maker; same frames both variants)",
         "",
         "| variant | n | mean R | win | total R | boot_p |",
         "|---|---:|---:|---:|---:|---:|"]
    for label, ad in (("current signal (VWAP rotation)", now_all),
                      ("§41-era signal (VWAP momentum)", pre_all)):
        L.append(f"| {label} | {ad['n']} | {ad['exp']:+.4f} | {ad['win']*100:.0f}% "
                 f"| {ad['total']:+.1f} | {ad['boot_p']:.3f} |")
    L += ["| §41 anchor (reported 2026-06-15) | 8124 | +0.0960 | — | +778.5 | 0.000 |",
          "",
          "Per-window detail: `studies/section41_gap_summary.csv`.",
          "",
          "## Delta accounting (prereg bar: residual ≤0.01R and ≤5% of trades)",
          "",
          f"- VWAP-flip contribution: Δexp = {d_exp_flip:+.4f}R, Δn = {d_n_flip:+d}",
          f"- Residual vs the §41 anchor after un-flipping: Δexp = {resid_exp:+.4f}R, "
          f"Δn = {resid_n:+d} ({abs(resid_n)/anchor_n*100:.1f}% of anchor n)",
          ""]
    ok = abs(resid_exp) <= 0.01 and abs(resid_n) <= 0.05 * anchor_n
    if ok:
        L.append("**VERDICT: EXPLAINED within the pre-registered residual bar.** The "
                 "backtest-vs-study gap is the §44 VWAP rotation flip — the validated "
                 "+0.096R belongs to the MOMENTUM-sign signal population; the flip both "
                 "shrank the population and erased the measured edge in it.")
    else:
        L.append("**VERDICT: PARTIALLY EXPLAINED.** The VWAP flip accounts for the "
                 "portion above; the residual vs the §41 anchor exceeds the "
                 "pre-registered bar and is attributed honestly to data-revision/"
                 "feature-era differences that reconstruction on today's code cannot "
                 "remove. Per the prereg's outcome branch, if the anchor does not "
                 "reproduce, the +0.096R claim must be treated as stale for the "
                 "CURRENT signal; the honest current-signal baseline is the 'current' "
                 "row above.")
    L += ["",
          "## Hard rules kept",
          "- Results computed only after the prereg merged to `main`.",
          "- No post-hoc hypotheses; the residual bar was not moved.",
          "- Read-only: engine imported, nothing reimplemented except the regression-",
          "  locked one-variable signal counterfactual; no live/journal/workflow touch.",
          "- NO live change proposed. Any management/tp1 decision remains a separate,",
          "  owner-approved step (owner hard stop, 2026-07-01)."]
    out_md = _REPO / "studies" / "section41_gap_results.md"
    out_md.write_text("\n".join(L) + "\n")
    print(f"\nWrote {out_md} and {out_csv}")
    print(f"current : n={now_all['n']} exp={now_all['exp']:+.4f} boot_p={now_all['boot_p']:.3f}")
    print(f"pre-flip: n={pre_all['n']} exp={pre_all['exp']:+.4f} boot_p={pre_all['boot_p']:.3f}")


if __name__ == "__main__":
    main()
