# §41 Gap Investigation — RESULTS (pre-registered)

Pre-registration: `studies/section41_gap_preregistration.md` (merged to `main`
2026-06-27, PR #117, before this run). Read-only; proposes NO live change.

## Hypothesis verdicts

- **H2 geometry: NOT the gap.** `scripts/cycle_backtest.py` passes `BRACKET_KW`
  with no tp1/tp2/trail kwargs → §41 WAS plain ride-3R (geometry A), the same
  geometry as the study reproduction. (Settled by code inspection.)
- **H3 fees: NOT the gap.** Both anchors are net-maker `FEE_PCT=0.0004`.
- **H4 gate: NOT the gap.** Both `min_pct=0.50, trend_align=True`.
- **H5 period: NOT the gap.** `WINDOWS` are byte-identical (the script has a
  single commit ever, 2026-06-15).
- **H1 population: THE gap.** The only signal-affecting code change since the
  §41 run is the v_vwap MOMENTUM→ROTATION flip (commit `be69b36`, 2026-06-16,
  PR #31, §44) — one day after §41. Flipping it back reconstructs the §41-era
  population on today's code + data:

## Measured attribution (1h, ride-3R, net maker; same frames both variants)

| variant | n | mean R | win | total R | boot_p |
|---|---:|---:|---:|---:|---:|
| current signal (VWAP rotation) | 3540 | -0.0151 | 33% | -53.5 | 0.738 |
| §41-era signal (VWAP momentum) | 8124 | +0.0958 | 36% | +778.5 | 0.000 |
| §41 anchor (reported 2026-06-15) | 8124 | +0.0960 | — | +778.5 | 0.000 |

Per-window detail: `studies/section41_gap_summary.csv`.

## Delta accounting (prereg bar: residual ≤0.01R and ≤5% of trades)

- VWAP-flip contribution: Δexp = +0.1109R, Δn = +4584
- Residual vs the §41 anchor after un-flipping: Δexp = +0.0002R, Δn = +0 (0.0% of anchor n)

**VERDICT: EXPLAINED within the pre-registered residual bar.** The backtest-vs-study gap is the §44 VWAP rotation flip — the validated +0.096R belongs to the MOMENTUM-sign signal population; the flip both shrank the population and erased the measured edge in it.

## Secondary note (honest, out-of-scope wrinkle)

The prereg quoted TWO current-signal study numbers: #116's ride-3R **−0.007R /
n=3,730** and §72's **−0.0151R / n=3,540**. This run reproduces §72's pair
exactly; the 190-trade (#116 vs §72) difference is an inter-study wrinkle between
two CURRENT-signal runs (likely cache-span/pairing differences in #116's paired
harness), not part of the §41-anchor gap this investigation attributes. Flagged,
not chased — chasing it would exceed the pre-registered scope.

## Hard rules kept
- Results computed only after the prereg merged to `main`.
- No post-hoc hypotheses; the residual bar was not moved.
- Read-only: engine imported, nothing reimplemented except the regression-
  locked one-variable signal counterfactual; no live/journal/workflow touch.
- NO live change proposed. Any management/tp1 decision remains a separate,
  owner-approved step (owner hard stop, 2026-07-01).
