# Management-Geometry Study — PRE-REGISTRATION

Date committed: 2026-06-26
Status: PRE-REGISTERED — written before any result viewed. Do not run the
backtest until this commit is on `main`.

## Why

The live management rule (bank half at TP1, slide stop to breakeven, ride the
rest to 3R) was added for psychological safety. Across the DXY/VAH/800-EMA
studies the same-geometry baseline ran ≈ −0.055R on the OOS top-10/1h pool,
while the §41 reference for plain ride-to-3R is cited at +0.096R. MEMORY §72
flagged the `be_after_tp1` question as out-of-scope-then, for a future chat. This
is that study: is the safety mechanism protecting edge or destroying it?

## Hypothesis

On the validated top-10/1h population, the bank-half/TP1/breakeven management
geometry (B) delivers statistically LOWER net-R/trade than the plain ride-to-3R
geometry (A).

## Null Hypothesis

Management geometry has no statistically significant effect on net-R/trade on
this population.

## Geometries under test (all via the unmodified `bracket_backtest`)

- **A — Ride 3R (§41 reference):** entry at the maker retrace, 1R stop, 3R
  target, no partial, no BE slide. `tp1_r=None, trailing_atr=None`.
- **B — Bank-half / BE (current live):** TP1 at 1R closes 50%, stop on the
  remainder slides to breakeven, remainder rides to 3R.
  `tp1_r=1.0, tp1_frac=0.5, be_after_tp1=True`.
- **C — Partial only (no BE slide):** TP1 at 1R closes 50%, remainder rides to
  3R with the stop left at −1R (isolates whether the BE slide specifically is
  the drag, vs the partial itself). `tp1_r=1.0, tp1_frac=0.5, be_after_tp1=False`.

All share the audited entry geometry (0.25-ATR maker retrace, 6-bar fill window,
1.5-ATR stop = 1R, 3R target, 24-bar time-stop) and maker fees. Population =
`cycle_backtest.WINDOWS` top-10/1h, `confluence_position(min_pct=0.50, trend_align)`
— identical to the prior studies. Trade lists come straight from
`bracket_backtest` (no reimplementation).

## Significance / baseline

`boot_p` = one-sided bootstrap P(mean net-R ≤ 0) per geometry (§19/§23). The
primary comparison is the **paired delta A−B** (and A−C, C−B) on the SAME pool —
an apples-to-apples relative test. NOTE (honesty): the §41 absolute +0.096R has
not been reproduced in this repo (MEMORY §72 records a −0.015R reproduction);
therefore the gate relies on the RELATIVE between-geometry delta measured here,
and the absolute numbers are reported as-measured, not assumed.

## Accept Conditions (ALL must be true) — the hypothesis "B is worse" is supported

- n >= 50 per geometry bucket
- bootstrap p < 0.05 (on the favoured geometry's net-R being > 0, AND the
  between-geometry difference established by a paired bootstrap of A−B)
- |delta| between the compared geometries > 0.015R (meaningful, not noise)

## Reject Conditions (ANY sufficient)

- n < 50 in any geometry bucket
- p >= 0.05
- delta within the 0.015R margin of error

## Hard Rules

- Results viewed only after this commit merges to `main`.
- No post-hoc geometry additions; no moving thresholds after seeing results.
- **No live management change is made by this study under any outcome.** If A
  beats B significantly, the ONLY output is a *governance proposal* in a SEPARATE
  PR requiring explicit human approval before anything touches the live system.
  The bot does not modify its own management rules — that is a human decision.
- If B ≥ A: current management validated, no change.
- If C isolates the BE slide as the drag: a targeted fix is *proposed* (same
  governance gate), not applied.

## Decision matrix (locked — the surgical read C provides)

- **B < A and C ≈ A** → the partial close is fine; the **BE slide** is the drag.
  Targeted fix proposed: drop `be_after_tp1`, keep the partial.
- **B < A and C < A** → the **partial itself** is the drag, not just the slide.
  Proposed: revert toward ride-3R (A).
- **B ≈ A** → current management **validated**; no change.

("≈" = within the 0.015R margin; "<" = worse by more than 0.015R with boot_p<0.05.)
Any proposed change goes through a SEPARATE governance PR requiring human approval
— this study itself changes nothing live.

## What this tells us

Whether the safety mechanism we added is protecting edge or destroying it.
Either answer is correct — we want the truth, not a preferred result.
