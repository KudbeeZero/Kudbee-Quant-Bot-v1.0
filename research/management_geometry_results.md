# Management-geometry study — results (pre-registered)

> **CLEAN RERUN — 2026-07-01, MOMENTUM-signal population (post-PR #130), MEMORY §76.**
> The original 2026-06-26 run (#116) was population-contaminated: its entries were
> selected by the rotation-sign signal that PR #129/§74 later refuted (n=3,730;
> A −0.007R / B −0.055R / C −0.042R, A−B=+0.048R p=0.000 — preserved in git and
> quoted in MEMORY §73/§76). This rerun executes the SAME pre-registered method on
> the validated momentum population. Same directional verdict, healthier absolutes.

Pre-registration: `studies/management_geometry_preregistration.md` (merged to main before this run). PAIRED design — one common entry set (live geometry B's timeline) resolved under A/B/C via the shared resolver. Population = validated top-10/1h, net of maker fees.

- Paired entries: **8935**

| geometry | n | mean R | win rate | total R | boot_p (mean≤0) |
|---|---:|---:|---:|---:|---:|
| A ride-3R | 8935 | +0.090 | 36% | +800.3 | 0.000 |
| B bank-half/BE (live) | 8935 | +0.048 | 53% | +432.2 | 0.000 |
| C partial no-BE | 8935 | +0.054 | 38% | +483.9 | 0.000 |

## Paired deltas

| comparison | mean delta R | paired boot_p (first≤second) |
|---|---:|---:|
| A-B | +0.041 | 0.000 |
| A-C | +0.035 | 0.000 |
| C-B | +0.006 | 0.068 |

## Verdict (pre-registered gate)

```
RESULT: A (ride-3R) beats B (current live) significantly & meaningfully. C < A (A-C=+0.035R, meaningful): dropping the BE slide alone does NOT recover ride-3R — the PARTIAL CLOSE itself is the larger drag (slide piece C-B=+0.006R; partial piece A-C=+0.035R). Governance proposal: move toward ride-3R (A). NOTE: research only — a SEPARATE governance PR with human approval is required before any live management change.
  n=8935 per geometry (paired).
  A ride-3R   mean +0.090R  boot_p 0.000
  B live      mean +0.048R  boot_p 0.000
  C no-BE     mean +0.054R  boot_p 0.000
  A-B delta +0.041R (paired boot_p A<=B 0.000); A-C +0.035R; C-B +0.006R
```
