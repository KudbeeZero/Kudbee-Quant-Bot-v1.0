# VAH trap-reversal — PRE-REGISTRATION

- **Date written:** 2026-06-26
- **Status:** PRE-REGISTERED — written and committed BEFORE any result was viewed.
- **Audit trail:** this file is committed in its own commit, ahead of the study
  code + results commit. The git history proves the gate was not moved after the
  data came in. No post-hoc rationalisation is permitted.

## Origin

Tino / Traders Reality, captured in `research/traders_reality_research_vol11.md`:
price rallies into the **prior session's Value Area High (VAH)**, prints a
**trap** (pokes above, then closes back below), and **reverses down**. This
pre-registers a falsifiable test of that idea on the bot's ACTUAL universe
(crypto top-10 / 1h), through the existing significance gate.

## Fixed definitions (locked before results)

- **Session:** UTC calendar day (the frame's `utc_date` column).
- **Per-session volume profile:** 50 equal price bins spanning the session's
  `[min(low), max(high)]`. Each 1h bar contributes its `volume` at its typical
  price `(high+low+close)/3`. **POC** = the max-volume bin.
- **Value Area (70%):** expand outward from the POC, repeatedly adding the
  heavier of the two adjacent bins, until cumulative volume ≥ 70% of the
  session's total. **VAH** = the upper edge of that contiguous band.
- **Prior-session VAH for a bar** = the VAH of the bar's previous `utc_date`.
  Bars whose prior day has no usable profile are excluded.
- **Proximity (X):** the trade's entry price is within **0.5 × ATR** (ATR at the
  signal bar) of the prior-session VAH.
- **Rejection candle (the "trap"):** at the signal bar `t`,
  `high[t] > prior_VAH` AND `close[t] < prior_VAH` (poked above the VAH, closed
  back below).
- **Qualifying signal:** proximity AND rejection, on the validated signal
  population (top-10 / 1h, `confluence_position(min_pct=0.50, trend_align)`),
  `cycle_backtest.WINDOWS`.
- **Geometry / cost:** the live bank-half @1R + BE + ride-to-3R bracket, net of
  maker fees — the exact enumerator fidelity-locked to `bracket_backtest`.

## Hypothesis

**H1:** qualifying signals (within 0.5·ATR of the prior-session VAH AND a VAH
rejection candle) deliver statistically higher net-R/trade than the full
validated population baseline.

**H0 (null):** VAH proximity + rejection at signal time has NO statistically
significant effect on net-R/trade.

## Primary endpoint

`mean_netR(qualifying)  −  mean_netR(full population, same geometry)`.

The full-population same-geometry mean is the comparison baseline (computed from
this run; the §41 ride-3R figure ≈ +0.096R is noted for reference only — the
gate uses the apples-to-apples same-geometry baseline).

## ACCEPT iff ALL hold

1. `n_qualifying >= 30`
2. bootstrap `boot_p(qualifying) < 0.05` (one-sided, P(mean ≤ 0); §19/§23)
3. `mean_netR(qualifying) − mean_netR(baseline) > 0.02R` (meaningful, not noise)

## REJECT if any of

- `n_qualifying < 30` (insufficient power)
- `boot_p >= 0.05`
- improvement `<= 0.02R` (within margin of error)

## HARD RULE

If REJECTED, the VAH filter does **NOT** get wired. Clean negative result, no
post-hoc gate-moving. Secondary side-splits (long/short) and a
near-VAH-WITHOUT-rejection specificity cell may be reported as **descriptive
only** — they cannot rescue a rejected primary.
