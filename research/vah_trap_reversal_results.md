# VAH trap-reversal — results (pre-registered)

Pre-registration: `docs/research/vah_trap_reversal_preregistration.md` (committed before this run). Population = validated top-10/1h confluence trades, live bank-half/BE/ride-3R geometry, net of maker fees.

- Total trades: **3730**
- Qualifying = entry within 0.5·ATR of prior-session VAH AND rejection candle (high>VAH & close<VAH).

| cell | n | mean R | win rate | total R | boot_p |
|---|---:|---:|---:|---:|---:|
| baseline_all | 3730 | -0.055 | 48% | -204.9 | 1.000 |
| qualifying (near VAH + rejection) | 101 | -0.033 | 50% | -3.4 | 0.634 |
| near VAH, NO rejection (specificity) | 424 | -0.087 | 46% | -36.9 | 0.950 |
| qualifying — long | 70 | -0.107 | 49% | -7.5 | 0.813 |
| qualifying — short | 31 | +0.132 | 52% | +4.1 | 0.268 |

## Verdict (pre-registered gate)

```
REJECT — at least one pre-registered gate fails. VAH filter NOT wired (hard rule; no post-hoc rescue).
  [PASS] n_qualifying=101 (need >= 30)
  [FAIL] boot_p=0.634 (need < 0.05)
  [PASS] improvement=+0.021R vs baseline -0.055R (need > 0.02R)
```
