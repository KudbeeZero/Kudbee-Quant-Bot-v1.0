# Signal #1 — Taker Delta / CVD / Delta-Divergence (validation)

**Status:** built, gated OFF by default, **independently validated on real data.**
**Verdict:** _split_ — as a confluence **FILTER it FAILS OOS (discard);** as a
**meta-model FEATURE it PASSES (keep, opt-in/research).** No change to live defaults.

## What was built (all opt-in, default OFF)

- `ingest/binance.py` — retain `taker_buy_base`/`taker_buy_quote` (were parsed then
  **dropped**); `ingest/resample.py` sums them through non-native timeframes.
- `levels/delta.py` `add_taker_delta()` — causal bar delta, `delta_pct`, `delta_z`,
  session CVD (`cvd_session_pct`), rolling CVD (`cvd_roll_pct`), absorption
  `delta_div`. Truncation-invariance test proves no lookahead.
- `config/features.py` `FeatureFlags(enable_taker_delta=False)` — env `ENABLE_TAKER_DELTA`.
- `build_levels(..., features=)` adds the columns **only when the flag is set**.
- `confluence_position(..., delta_align=False)` — opt-in CONFIRMATION FILTER (never a
  vote, per the parsimony mandate). `ml/labels.make_features` picks up the 5 delta
  features when present.

## Method

Real Binance 1h, top-10 majors (BTC/ETH/SOL/BNB/XRP/ADA/DOGE/AVAX/LINK/DOT), 8000
bars each (~333 d). Canonical validated bracket (`config/validated_defaults.py`:
min_pct 0.50, trend_align, target 3R, stop 1.5×ATR, 0.25-ATR retrace, 24-bar stop,
maker fee 0.0004). Reproduce: `PYTHONPATH=. python scripts/validate_taker_delta.py`.

## Results

### (A) `delta_align` FILTER — pooled realized-R, IS(70%) vs OOS(30%) — **FAILS**

| | baseline | +delta_align |
|---|---|---|
| **IN-SAMPLE** | +0.1047R (n=2118) | **+0.1654R** (n=1666) |
| **OUT-OF-SAMPLE** | **+0.0193R** (n=897) | **−0.0093R** (n=698) |

The filter improves expectancy **in-sample only** and **turns OOS positive→negative**
(−0.0286R, keeps 78% of trades). This is the exact failure mode of the 5 removed
votes — "helps IS, hurts OOS" = discard. **Do not enable `delta_align`.**

_Engine cross-check (`walk_forward()`, always-in position): both variants net-negative
OOS Sharpe (baseline −1.20, +delta_align −0.92); delta is marginally less bad on the
continuous-hold view but that path is not the bracketed strategy — the bracket R above
is the truth, and it says discard._

### (B) delta FEATURES into the meta-model (purged/embargoed CV) — **PASSES**

3015 trades, base rate 0.356. Best expectancy-gate threshold:

| model | gated expectancy | lift vs base | perm p | significant |
|---|---|---|---|---|
| GBT **with** delta | **+0.3287R** | +0.2274R | **0.0073** | **YES** |
| GBT **without** (control) | +0.2345R | +0.1332R | 0.0643 | no |
| logit with/without | ~+0.14R | — | >0.24 | no |

Adding the delta features flips the GBT expectancy-gate from **not significant
(p=0.064) to significant (p=0.0073)** and lifts best-threshold OOS gated expectancy
**+0.094R**. AUC barely moves (0.5065→0.5071) — the value is in the **confident tail,
not global ranking**, and is **nonlinear** (GBT only; logit can't use it, delta_z
coef ≈ −0.08). Meets the keep-criterion: improves OOS expectancy without shrinking
trade count (gating is downstream).

### 60% confluence-band probe

The task's stale figure (60% band = −31R of −32.57R forward loss) **does not reproduce
on this window**: OOS the ~0.60 band is **+0.2505R (n=146, +36.6R)** — one of the
*better* bands, not a loss. `delta_align` does **not** rescue it (it *reduces* it to
+0.156R). Conclusion: the −31R was window/universe-specific (consistent with the §36
edge-decay note); **re-measure on the original window before excluding the band** — and
no new filter here is the rescue.

## Recommendation (config diff)

- **Keep `ENABLE_TAKER_DELTA` defaulting OFF.** Live confluence votes / `confluence_position`
  default path are byte-identical — nothing to change there.
- **Do NOT use `delta_align`** (fails OOS).
- **Enable `ENABLE_TAKER_DELTA=true` only in the meta-model training/eval path** to get
  the GBT feature lift; do not wire it into the live vote gate.
- **Caveats (honest):** single window/universe; AUC ≈ 0.507 (tail-only edge); the
  significance flip (0.064→0.007) sits near the boundary — **re-validate forward** before
  any live meta-gating. Linear models see nothing.
