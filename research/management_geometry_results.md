# Management-geometry study — results (pre-registered)

Pre-registration: `studies/management_geometry_preregistration.md` (merged to main before this run). PAIRED design — one common entry set (live geometry B's timeline) resolved under A/B/C via the shared resolver. Population = validated top-10/1h, net of maker fees.

- Paired entries: **3730**

| geometry | n | mean R | win rate | total R | boot_p (mean≤0) |
|---|---:|---:|---:|---:|---:|
| A ride-3R | 3730 | -0.007 | 34% | -24.8 | 0.611 |
| B bank-half/BE (live) | 3730 | -0.055 | 48% | -204.9 | 1.000 |
| C partial no-BE | 3730 | -0.042 | 36% | -155.9 | 0.989 |

## Paired deltas

| comparison | mean delta R | paired boot_p (first≤second) |
|---|---:|---:|
| A-B | +0.048 | 0.000 |
| A-C | +0.035 | 0.000 |
| C-B | +0.013 | 0.012 |

## Verdict (pre-registered gate)

```
RESULT: A (ride-3R) beats B (current live) significantly & meaningfully. C < A (A-C=+0.035R, meaningful): dropping the BE slide alone does NOT recover ride-3R — the PARTIAL CLOSE itself is the larger drag (slide piece C-B=+0.013R; partial piece A-C=+0.035R). Governance proposal: move toward ride-3R (A). NOTE: research only — a SEPARATE governance PR with human approval is required before any live management change.
  n=3730 per geometry (paired).
  A ride-3R   mean -0.007R  boot_p 0.611
  B live      mean -0.055R  boot_p 1.000
  C no-BE     mean -0.042R  boot_p 0.989
  A-B delta +0.048R (paired boot_p A<=B 0.000); A-C +0.035R; C-B +0.013R
```
