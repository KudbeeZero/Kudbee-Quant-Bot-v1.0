# §41 Gap Investigation — PRE-REGISTRATION

Date committed: 2026-06-26
Status: PRE-REGISTERED — written before any analysis is run. Do not run the
investigation until this commit is on `main`. (Static code/config was read to
write an informed method; NO comparison/backtest has been executed.)

## Why this is the most important question in the repo right now

The management study (#116) found ride-3R (geometry A) beats the live bank-half/BE
geometry by +0.048R/trade — but A itself is only **−0.007R** on the OOS pool. The
validated backtest §41 reported **+0.096R** net-maker on 1h. That is a **~0.10R
per-trade discrepancy on the same system**, and it sits underneath every overlay
study this session. Before ANY live-management change is proposed, this gap needs
an explanation — switching management on a book that is −0.10R below its own
validation would be optimizing something that is underwater relative to itself.

## The two measured anchors

- **§41 (validated, 2026-06-15):** 1h, validated config (`min_pct=0.5`,
  `trend_align=True`, 3R, 1.5-ATR stop, 0.25 maker retrace, `max_bars=24`),
  over `cycle_backtest.WINDOWS` (2018/2022 chop analogs + recent), **+0.096R
  net-maker, n=8,124**, bootstrap p<0.001. (MEMORY §41.)
- **This session's studies (OOS-now):** the SAME validated config + windows via
  `trailing_sweep.load_cells`, ride-3R geometry (A) = **−0.007R, n=3,730**
  (and §72 recorded a separate ride-3R reproduction at −0.0151R / n=3,540).

**Two gaps, not one:** an R-level gap (≈0.10R) AND a trade-count gap (8,124 vs
3,730, ≈2.2×). The n-gap is the strongest lead — a population this different is
likely the dominant driver and may explain much of the R-level gap too.

## Primary deliverable

Decompose and attribute BOTH gaps. For each hypothesis below, change exactly one
variable from this session's study config toward the §41 `cycle_backtest` config
(or vice-versa), one at a time, and record how much of the n-gap and the R-gap
each variable accounts for. Output: a table attributing the +0.096R→−0.007R and
8,124→3,730 deltas to specific, named causes.

## Hypotheses (ranked by prior; locked before results)

1. **Population / trade-count (strongest prior).** The 2.2× n-gap means the two
   runs are not scoring the same trades. Candidate causes: universe membership
   (`Window.universe()` `LISTED`-date filter), overlap handling (`allow_overlap`),
   confluence-band counting, or which windows/timeframes are pooled. Reconcile by
   running `cycle_backtest` exactly as §41 did and confirming n=8,124 @ +0.096R is
   reproducible at all, then diffing its cell/trade set against `load_cells`.
2. **Geometry mismatch.** Whether §41's +0.096R was all-or-nothing ride-3R (A) or
   the bank-half/BE rule (B). If §41 == A, geometry is NOT the gap (same geometry,
   different result → points back to population). If §41 == B, the management
   study's A−B sign must be re-read against it.
3. **Fee model.** §41 quotes +0.096R net-MAKER (and +0.060R net-full-taker). The
   studies use `FEE_PCT` (maker). Confirm both are the same maker basis; if so,
   fees are not the gap. (Listed for completeness — low prior.)
4. **Confluence gate.** Both use `min_pct=0.50, trend_align=True`. Confirm
   identical; low prior.
5. **Time period / regime.** `WINDOWS` are fixed date ranges, so the data should
   be near-identical between 2026-06-15 and now (only the "recent" window end may
   differ slightly). Confirm the window bounds match; if they do, period is not
   the gap. (Low prior given fixed windows.)

## What counts as "explained"

The gap is EXPLAINED when the attributed deltas (per hypothesis) sum to the full
+0.096R→−0.007R and 8,124→3,730 difference within a small residual (≤0.01R and
≤5% of trades), with each contribution traced to a specific config difference.

## Possible outcomes (all acceptable — we want truth)

- **§41 reproduces (+0.096R/n=8,124)** and a named config difference explains the
  studies' lower figure → we know which population/setting the live edge lives in.
- **§41 does NOT reproduce** (as §72 hinted) → the +0.096R is stale/non-reproducible
  and the honest baseline is ~breakeven; the management finding (B worse than A)
  still stands on its own paired pool, and the "validated +0.096R" claim must be
  retired in MEMORY.
- **Partial** → attribute what we can; flag the residual honestly.

## Hard Rules

- Results viewed only after this commit merges to `main`.
- No post-hoc hypothesis additions; no moving the "explained" bar after seeing data.
- READ-ONLY: the investigation reuses `cycle_backtest`/`bracket_backtest`/the
  shared resolver and touches NO live execution, signal, journal, or workflow code.
- This investigation proposes NO live change. It informs whether a management
  governance proposal is even meaningful; any live change remains a separate,
  human-approved decision.
