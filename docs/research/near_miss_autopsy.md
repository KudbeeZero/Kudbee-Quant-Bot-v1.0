# Near-miss autopsy + scenario re-simulation — report

**Date:** 2026-06-14 · **Scope:** research only, live config UNTOUCHED · **Verdict:**
the in-sample "fix" (drop the 60% band / lower the target) is **OVERFIT** — the OOS
engine refutes it. The two changes that *do* survive OOS (trend-filter, drop the
fee-poisoned sub-hourly book) are **already live**. One modest, OOS-supported tweak
remains: optionally tighten the confluence gate `0.50 → 0.60`, best run as a forward
shadow-test first.

Reproduce: `PYTHONPATH=. python scripts/near_miss_autopsy.py` (in-sample, real bars)
and `… scripts/near_miss_oos.py` (out-of-sample walk-forward). Per-trade MFE/MAE in
`data/excursion_audit.json`.

---

## 0. Method + reconciliation

- **STEP 1** re-fetched the real bars each of the 118 resolved bracket trades lived
  through (`filled_at → resolved_at`) and measured MFE/MAE in R (direction-aware,
  normalised by the trade's own stop). **STEP 2/3** re-resolved the *same* forward
  bars via the project's shared `backtest/resolver.resolve_bracket` at targets
  1.0–3.0R and under per-band rules.
- **Windowing audit:** re-resolving every trade at its original **3R** reproduced the
  journal's recorded outcome **sign 99/100** and within 0.25R **99/100**. The replay
  is faithful, so the swept numbers are trustworthy.

## 1. Near-miss list (the headline the user asked for)

Many 60%-band losses were genuine **near-wins** — they ran far in our favour, then
reversed to the stop. The table below is **filtered to the 60% band** (the band under
investigation); the full, unfiltered ranking is in `data/excursion_audit.json` (the
single largest-MFE near-miss overall is actually a 70%-band BNBUSDT 5m at +9.67R).
Top 60%-band near-miss losses:

| symbol | tf | dir | band | MFE (R) | MAE (R) | outcome |
|---|---|---|---|---|---|---|
| SOLUSDT | 5m | L | 60% | +4.43 | −1.72 | −1.0 |
| SOLUSDT | 15m | L | 60% | +3.20 | −1.24 | −1.0 |
| DOTUSDT | 2h | S | 60% | +2.92 | −1.23 | −1.0 |
| LINKUSDT | 5m | L | 60% | +2.70 | −3.02 | −1.0 |
| SOLUSDT | 1h | S | 60% | +2.40 | −1.72 | −1.0 |

These reached +2.4 to +4.4R before stopping — which is *why* a "lower the target"
idea looks tempting on this window. STEP 2 tests whether it actually helps.

## 2. In-sample target sweep (NET of fees, 118 trades, the 06-09→14 journal)

| gate | 1.0R | 1.5R | 2.0R | 2.5R | 3.0R |
|---|---|---|---|---|---|
| **OVERALL** netR | −37.8 | −39.8 | −43.8 | −45.3 | −54.4 |
| **50%** netR | −21.7 | −23.7 | −28.7 | −28.2 | −21.7 |
| **60%** netR | −16.4 | −17.9 | −20.4 | −25.9 | −38.4 |
| **70%** netR | −1.4 | −0.9 | +1.6 | +4.1 | 0.0 |

In-sample reads, honestly:
- **No target rescues the 60% band** — it is net-negative at *every* target (best
  −16.4R at 1.0R; the answer to "does 60% flip positive at 1.5R?" is **no**, −17.9R).
- **At NET, the 50% band also bleeds** (best −21.7R) — it only looked "flat" *gross*;
  fees (sub-hourly taker, §35/§37) roughly double the loss. Only **≥70% is positive**.
- **Dropping the 60% band** (rest at 3R) → **−16.0R** vs −54.4R baseline; far better
  than the best adaptive target map (−40.9R). So in-sample, *band-carving beats R:R
  tuning* — and dropping 60% (or all of <70%) is the frontrunner.

**But n=118 over ~5 days is one regime, heavily sub-hourly + fee-poisoned. STEP 4 is
the arbiter.**

## 3. Out-of-sample walk-forward (1h majors, 10 assets × 6 OOS folds, fee_r=0.05)

| gate (≥pct) @ 3R | cells | trades | frac+ | median exp (R) | total R |
|---|---|---|---|---|---|
| 0.40 | 60 | 3739 | 50% | +0.002 | +20.9 |
| 0.50 | 60 | 3102 | 50% | +0.017 | +135.8 |
| **0.60** | 60 | 1762 | **55%** | **+0.100** | +107.6 |
| 0.70 | 1 | 15 | — | — | (insufficient) |

Target sweep OOS (does a lower target rescue the low gate?):

| gate | 1.5R | 2.0R | 3.0R |
|---|---|---|---|
| 0.50 median exp | −0.008 | −0.000 | **+0.017** |
| 0.60 median exp | −0.036 | +0.003 | **+0.100** |

Trend-align (price vs 800-EMA) @ 3R: 0.50 gate frac+ 50%→**62%**, exp +0.017→+0.034;
0.60 gate exp ~flat (+0.100→+0.095) but total +107.6→**+150.8**. Cost sensitivity @
0.60/3R: median exp +0.150 → +0.050 across fee_r 0.00 → 0.10 (stays positive).

**OOS verdict — the opposite of in-sample:**
- **Expectancy RISES with the confluence gate** (0.5→0.6: +0.017→+0.10). The
  confluence ordering works OOS — higher % is better, not worse.
- **Lowering the target HURTS OOS** at both gates; **3R is correct**, 1.5R goes
  negative. The in-sample "lower target" idea does **not** generalise.
- **The 60% gate is net-POSITIVE OOS** and robust to cost — so **dropping it would be
  fitting to the 5-day forward regime.**
- **Trend-alignment is mildly, robustly positive** (matches the edge-lab split-half
  claim).

## 4. Why the journal bled (reconciliation)

The −32.6R came from signals that the OOS engine shows were handicapped two ways the
*live config has since fixed*:
1. **Sub-hourly fee poison** — the bleed is concentrated in 5m/15m, where the taker in
   R is on the order of the edge (§35/§37). **5m was already paused (§37).**
2. **No trend filter** — the losing trades are labelled `confluence_r_*pct` with **no
   `_tf`**, i.e. generated before `--trend-filter` was enabled. **The hourly Action
   already runs `--trend-filter`** (`.github/workflows/paper-trade.yml`).
3. A chop/whipsaw 5-day regime (high MFE then reversal — the near-miss pattern).

## 5. Recommendation (for approval — NOT applied)

**Do NOT** drop the 60% band and **do NOT** lower the target — both are in-sample-only,
**flagged OVERFIT**, and the OOS engine refutes them. The two fixes the autopsy
validates (trend-filter on, 5m paused) are already deployed.

**Optional, OOS-supported tweak — tighten the confluence gate, as a forward test:**

```diff
# .github/workflows/paper-trade.yml  (hourly scan) — PROPOSED, pending approval
-            --min-pct 0.5 \
+            --min-pct 0.6 \
```

Evidence: OOS median expectancy +0.017R (0.5) → **+0.10R (0.6)**, frac-positive
50%→55%, robust to cost to fee_r=0.10; the marginal 0.5–0.6 cohort is only ~+0.02R/
trade and was the in-sample bleed. Trade count roughly halves — so this is a
quality-over-quantity tightening, not a structural claim.

**Caveat (honesty):** frac-positive at 0.6 is 55% — supportive but not overwhelming
over one 166-day, correlated-majors window. Recommend shadowing the 0.6 gate forward
(or A/B 0.5 vs 0.6 in the journal) before committing, rather than a hard flip. Keep
3R, keep trend-filter, keep 5m paused.

### Direct answer to "does dropping the 60% band beat any target tweak?"
In-sample, **yes** (−54→−16R, beating every R:R change). **Out-of-sample, no** — the
60% gate is positive, so dropping it overfits the forward window. The journal's
per-band bleed is a sub-hourly-fee + no-trend-filter + chop artifact, already addressed
in live config. The robust lever is *tightening the threshold*, not carving out a band.
