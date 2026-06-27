# Management shadow re-scoring — REAL forward journal trades

Read-only counterfactual: the bot's actual resolved validated 1h trades, re-resolved under A/B/C from their post-fill bars (shared resolver, maker fees). NOT wired to live; on-demand only.

- Scored: **112** of 153 resolved validated 1h trades.

| geometry | n | mean R | win rate | total R | boot_p |
|---|---:|---:|---:|---:|---:|
| A ride-3R | 112 | -0.053 | 32% | -6.0 | 0.640 |
| B bank-half/BE (live) | 112 | -0.155 | 49% | -17.4 | 0.953 |
| C partial no-BE | 112 | -0.062 | 37% | -6.9 | 0.712 |

A−B mean delta: +0.102R (forward, n=112). Backtest reference (study #116): A−B=+0.048R.

_Forward sample is small/retrospective; treat as directional corroboration, not a fresh significance test until ≥50 NEW trades accrue._
