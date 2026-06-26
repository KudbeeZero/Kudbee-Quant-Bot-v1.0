# DXY-regime effect on the validated crypto book — results

Read-only study. Population = validated top-10/1h confluence trades (`cycle_backtest.WINDOWS`), live bank-half/BE/ride-3R geometry, net of maker fees. DXY regime = `get_dxy_regime()` over daily ICE DXY as-of entry.

- Trades analyzed: **3730** (skipped, no DXY as-of: 0)
- Significance gate: one-sided bootstrap `boot_p < 0.05` AND `n >= 30` per cell.

## Net-R by DXY regime x side

| regime | side | n | mean R | win rate | total R | boot_p |
|---|---|---:|---:|---:|---:|---:|
| USD_BULL_CONFIRMED | all | 1932 | -0.042 | 49% | -81.2 | 0.953 |
| USD_BULL_CONFIRMED | long | 927 | -0.057 | 49% | -52.5 | 0.947 |
| USD_BULL_CONFIRMED | short | 1005 | -0.029 | 48% | -28.7 | 0.788 |
| USD_APPROACHING_KEY | all | 1090 | -0.097 | 47% | -105.9 | 0.998 |
| USD_APPROACHING_KEY | long | 517 | -0.111 | 46% | -57.5 | 0.991 |
| USD_APPROACHING_KEY | short | 573 | -0.085 | 47% | -48.4 | 0.966 |
| USD_BASE_BUILDING | all | 649 | -0.021 | 50% | -13.7 | 0.679 |
| USD_BASE_BUILDING | long | 343 | +0.021 | 52% | +7.1 | 0.356 |
| USD_BASE_BUILDING | short | 306 | -0.068 | 47% | -20.8 | 0.866 |
| USD_WEAK | all | 59 | -0.069 | 51% | -4.1 | 0.696 |
| USD_WEAK | long | 33 | +0.036 | 52% | +1.2 | 0.440 |
| USD_WEAK | short | 26 | -0.202 | 50% | -5.3 | 0.883 |

## Directional lean (descriptive only — NOT a significance result)

| regime | long mean R | short mean R | long−short |
|---|---:|---:|---:|
| USD_BULL_CONFIRMED | -0.057 | -0.029 | -0.028 |
| USD_APPROACHING_KEY | -0.111 | -0.085 | -0.027 |
| USD_BASE_BUILDING | +0.021 | -0.068 | +0.089 |
| USD_WEAK | +0.036 | -0.202 | +0.238 |

## Verdict

```
INCONCLUSIVE — no regime/side cell clears boot_p<0.05 AND n>=30. Macro layer stays INERT (correct result; do not wire).
```
