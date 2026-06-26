# 800-EMA gate study — results (pre-registered)

Pre-registration: `studies/800_ema_study_preregistration.md` (merged to main before this run). Population = validated top-10/1h confluence trades, live bank-half/BE/ride-3R geometry, net of maker fees. 800-EMA from build_levels' `ema_800` column.

- Total trades: **3730** (excluded, 800-EMA warm-up/on-EMA: 0)

| bucket | n | mean R | win rate | total R | boot_p |
|---|---:|---:|---:|---:|---:|
| baseline (all classified) | 3730 | -0.055 | 48% | -204.9 | 1.000 |
| ABOVE 800-EMA | 1820 | -0.056 | 49% | -101.6 | 0.986 |
| BELOW 800-EMA | 1910 | -0.054 | 48% | -103.2 | 0.986 |
| ABOVE — long | 1820 | -0.056 | 49% | -101.6 | 0.986 |
| ABOVE — short | 0 | — | — | +0.0 | — |
| BELOW — long | 0 | — | — | +0.0 | — |
| BELOW — short | 1910 | -0.054 | 48% | -103.2 | 0.986 |

## Verdict (pre-registered gate)

```
REJECT — at least one pre-registered gate fails. 800-EMA gate NOT wired (hard rule; no post-hoc rescue).
  [PASS] n_above=1820 (need >= 30)
  [PASS] n_below=1910 (need >= 30)
  [FAIL] boot_p(ABOVE)=0.986 (need < 0.05)
  [FAIL] improvement=-0.001R vs baseline -0.055R (need > 0.02R)
  (context) ABOVE-BELOW spread = -0.002R
```
