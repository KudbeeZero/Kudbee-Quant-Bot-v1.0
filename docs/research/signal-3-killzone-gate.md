# Signal #3 — Killzone entry gate (validation)

**Status:** built, opt-in, default OFF, **independently validated on real data.**
**Verdict:** **FAILS — discard.** Restricting entries to London/NY/Brinks windows
*hurts* OOS expectancy on the real bracket; the hour-by-hour map shows the 1h crypto
edge lives in the OFF-killzone "bleed" hours, the opposite of the FX folklore.
No change to live defaults.

## What was built (opt-in, default OFF)

- `confluence_position(..., killzone_gate=False)` — keep entries only when one of
  `KILLZONE_GATE_FLAGS = (in_london_kz, in_ny_brinks, in_overlap)` is active (London
  KZ ET 02-05, NY Brinks ET 08:30-09:45, London/NY overlap ET 08-11). Accepts `True`
  (default windows) or a custom flag list; no-op if the flags are absent. Pure filter
  on existing causal columns — no new build columns, never a vote.

## Method

Real Binance 1h, top-10 majors, 8000 bars, canonical validated bracket.
Reproduce: `PYTHONPATH=. python scripts/validate_killzone_gate.py`.

## Results

### (A) killzone FILTER — pooled realized-R, IS(70%) vs OOS(30%) — **FAILS**

| | baseline | +killzone |
|---|---|---|
| **IN-SAMPLE** | +0.1047R (n=2118) | +0.1529R (n=1311) |
| **OUT-OF-SAMPLE** | +0.0193R (n=897) | **−0.0672R** (n=572) |

Helps in-sample, **flips OOS positive→negative** (−0.0864R lift). Same failure mode as
the removed votes and Signal #1's filter.

### (B) UTC-hour BLEED map — the real finding

Baseline expectancy by entry hour (UTC), killzone hours marked `KZ`:

| good OFF-killzone hours | weak KZ hours |
|---|---|
| **16h +0.316**, 0h +0.204, 1h +0.264, 2h +0.291, 17h +0.129, 18h +0.118 | 8h **−0.224**, 9h −0.138, 14h −0.097, 6h −0.062 |

**IN killzone: +0.0214R (n=847) vs OFF hours: +0.1019R (n=2168)** — the off-hours are
~5× better. The task's suspicion is confirmed and sharpened: **16h UTC is one of the
best hours (and is OFF-killzone), while 06h is a weak killzone hour** — so a killzone
gate *excludes the edge and keeps the chaff*. On a 24/7 crypto book the FX
London/NY/Brinks windows are not where this strategy's edge sits.

### (A2) walk_forward() engine cross-check — **CONTRADICTS (A), reported honestly**

| variant | IS Sharpe | OOS Sharpe | OOS ret |
|---|---|---|---|
| baseline | −0.219 | −1.202 | −0.2456 |
| +killzone | −0.315 | **+0.275** | **+0.0229** |

On the always-in continuous-hold engine the killzone gate turns OOS **positive**. This
conflicts with the bracket result (A). Reason: the engine holds the signal every bar,
so cutting exposure during bad continuous stretches helps it; the **bracketed strategy
is what we actually trade** (limit-retrace entry, 1.5-ATR stop, 3R target), and there
killzone-hour entries are simply lower quality. We resolve in favour of the bracket →
**the gate fails for the real strategy.**

## Recommendation (config diff)

- **Do NOT enable `killzone_gate`** — it degrades the traded (bracket) OOS expectancy
  and excludes the best hour (16h UTC). Keep the param default OFF.
- **Keep the hour map as evidence, not a tradeable rule:** picking the good hours from
  table (B) would be in-sample hour-fishing (table is full-sample, not split) — any
  hour filter needs its own IS/OOS validation before use, and risks overfitting given
  24 thin buckets.
- **Net:** an honest negative — killzone restriction is folklore that doesn't survive
  OOS on this 1h crypto book. The off-hours "bleed" is the edge, not noise.
