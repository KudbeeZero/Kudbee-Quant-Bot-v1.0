# Signal #2 — Per-session Volume Profile: POC / VAH / VAL / naked POC (validation)

**Status:** built, gated OFF by default, **independently validated on real data.**
**Verdict:** _mixed-positive but not conclusive._ The proximity FILTER lifts OOS
expectancy yet **degrades in-sample** (unstable); the distance FEATURES pass the
meta-gate but **near the significance boundary.** Keep OFF; **forward-validate before
enabling either path.** No change to live defaults.

## What was built (all opt-in, default OFF — `ENABLE_VOLUME_PROFILE`)

- `levels/volume_profile.py` `add_volume_profile()` — per NY-session-day volume-by-price
  histogram → **POC** (busiest price), **value area** (70% band → **VAH/VAL**), and the
  nearest untouched prior POC (**naked POC**). Exposed to the *next* session (shift one
  day), like `prior_ny_high`/pivots → strictly causal (truncation-invariance test).
- `vp_poc, vp_vah, vp_val, vp_naked_poc` appended to `LEVEL_COLUMNS` (the scorer skips
  absent columns, so this is behaviour-preserving by default).
- Scale-free features `dist_vp_poc_atr, dist_vp_naked_poc_atr, in_value_area, near_vp_poc`
  picked up by `ml/labels.make_features` when present.

## Method

Identical to Signal #1: real Binance 1h, top-10 majors, 8000 bars each, canonical
validated bracket. Reproduce: `PYTHONPATH=. python scripts/validate_volume_profile.py`.

## Results

### (A) vp-proximity FILTER (entries only within 0.5 ATR of a VP level) — **mixed**

| | baseline | +vp_near |
|---|---|---|
| **IN-SAMPLE** | +0.1047R (n=2118) | **+0.0303R** (n=1071) |
| **OUT-OF-SAMPLE** | +0.0193R (n=897) | **+0.0760R** (n=465) |

OOS expectancy lift **+0.0568R** (4× baseline, win% 34.6→36.6), keeping 52% of trades —
but it **cuts in-sample expectancy by ~70%**. A stable structural edge should not
*destroy* the in-sample edge while helping OOS; this IS/OOS sign flip reads as
window/regime-dependent, not a durable filter. Engine cross-check (`walk_forward()`):
OOS Sharpe essentially flat (−1.19 vs baseline −1.20), OOS return less negative
(−0.112 vs −0.246). **Inconclusive — do not enable; forward-test only.**

### (B) vp distance FEATURES into the meta-model — **passes, but fragile**

3015 trades, base rate 0.356. Best expectancy-gate threshold:

| model | gated expectancy | lift | perm p | significant |
|---|---|---|---|---|
| GBT **with** vp | **+0.3286R** | +0.2272R | **0.0053** | **YES** |
| GBT **without** (control) | +0.2345R | +0.1332R | 0.0643 | no |
| logit (either) | ~+0.11–0.16R | — | >0.24 | no |

Same shape as Signal #1: the vp features flip the GBT gate from non-significant
(p=0.064) to significant (p=0.0053), AUC 0.5065→0.5102, +0.094R best-threshold OOS
expectancy; logit sees nothing (nonlinear/tail-only). **Caveat — fragility:** the
control sits right on the boundary (p=0.064), and *both* Signal #1's delta features
*and* these vp features tip it to ~p=0.005 with a near-identical best gated expectancy
(~0.329R). That the GBT lands in the same place from two different feature sets suggests
the marginal lift is **small and near the noise floor**, not a large independent edge.

## Recommendation (config diff)

- **Keep `ENABLE_VOLUME_PROFILE` defaulting OFF.** `LEVEL_COLUMNS` lists the vp levels
  but the scorer ignores absent columns → live path byte-identical.
- **Do NOT wire the vp-proximity filter into the live strategy** (helps OOS but
  destabilises IS — not validated).
- The vp FEATURES are a **research-only** meta-model input: enable the flag in the
  training/eval path only, and **re-validate forward** before any live meta-gating —
  the significance is near-boundary and shared with Signal #1, so treat the lift as
  provisional, not banked.
- **Net:** the volume-profile levels are a clean, causal, parsimony-respecting addition
  to the level catalog. The strongest honest claim is "promising on this window,
  unproven forward" — consistent with the project thesis (don't over-claim).
