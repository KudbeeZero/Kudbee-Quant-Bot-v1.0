# Testable Rule Set — turning Traders Reality teachings into measurable edges

This is the bridge from the research (`tino_traders_reality.md`) to code. It
converts each *belief* into a **mechanically-defined event** with **context
features** and a **measured forward outcome**. The model "gets smarter" not by
believing harder, but by accumulating **conditional base rates** from history
and reporting them honestly — including when an edge is absent.

> Architecture: a **Conditional Event-Study Engine**. For each event type we
> compute P(outcome | context) over real data, with confidence intervals and
> an out-of-sample / multi-asset check (reusing our existing validation
> harness). No claim is trusted until it survives that bar.

Every event is timestamped in **UTC** but classified by **New York local
time** with DST handled, and tagged with a **holiday flag**.

---

## Shared context features (attached to every event)

- `session` ∈ {asian, london, ny, london_ny_overlap, off}
- `killzone` ∈ {asian, london_open, ny_forex, ny_indices, london_close, none}
- `minutes_into_session` (e.g. "3 hours into NY" = 180)
- `day_of_week` (Mon–Sun) and `week_phase` (Mon range / Tue–Thu expansion / …)
- `is_holiday`, `is_thin_liquidity` (late-Dec, pre-holiday half-days)
- `dist_to_daily_open`, `dist_to_weekly_open` (in ATR units)
- `nth_test_of_level` (1st, 2nd, 3rd touch — the user's "second test")
- `pvsra_tier` (climax / above-avg / normal) and `vector_color`
- forward outcome windows: return over next k bars; MFE/MAE; did level X get hit

---

## A. Vector-candle recovery (honoring "it always gets recovered")

**Event:** a vector (climax) candle forms (`pvsra.py` already flags these).
**Zone:** the candle's `[low, high]` box; midpoint = 50% level.
**Outcome to measure (NOT assume):**
1. `recovered_within(N)` — does price re-enter the box within N bars? Build the
   **survival/recovery curve**: fraction recovered at N = 1,5,15,60,240,1440…
   bars, **per timeframe**. This turns "always, eventually" into a real number
   like "62% within 24h on 1h BTC."
2. `reversal_at_partial` — when price penetrates 50–100% of the zone, measure
   forward return vs. a null (random equidistant level). Tests the "50–100%
   reversal" claim.
3. `magnet_test` — is an unrecovered zone reached more often than a random
   level the same distance away? (Edge only exists if yes.)

**Honesty rule:** report the recovery curve and the *base rate of any level
being revisited anyway*. If random levels get "recovered" almost as often, the
vector adds no edge — say so.

---

## B. Daily/weekly open + the "second test" (the user's Tuesday/NY example)

**Levels:** Midnight Open (00:00 ET), prior-day open, Weekly Open (Sun 18:00
ET). (We already compute PDH/PDL/PWH/PWL; add the opens.)
**Event:** price **tests** a level (touch within ε·ATR). Track `nth_test`.
**The exact study the user asked for** — "price tests the daily open for the
second time on a Tuesday, 3 hours into the NY session: up or down, and why?":

```
event   = test of daily_open
filter  = nth_test == 2  AND  day_of_week == Tue  AND  session == ny
          AND 150 <= minutes_into_session <= 210
measure = sign and size of forward return over next {15,30,60,120} min
          + which level got hit first (open reclaim vs. continuation)
```

**Benchmark:** edgeful's measured midnight-open retest base rates (ES ~58–69%,
NQ 73% on Tuesdays, BTC ~64–65%, **Gold ~50/50 → no edge**) are the yardstick.
We reproduce these on our own data before trusting any finer slice.

**Honesty rule:** conditioning on (2nd test × Tuesday × NY × 3h-in) slices the
data thin — guard against **multiple-comparisons / overfitting**: require a
minimum sample size, report the CI, and validate out-of-sample. A 73% that
rests on 30 Tuesdays is not 73%.

---

## C. Liquidity sweeps & day-of-week structure

**Sweep event** (already in `context/mm_cycle.py`): price pierces PDH/PDL/
PWH/PWL/Asian-range then closes back through. **Measure** forward return after
a sweep, conditioned on session/killzone.
**Weekly-extreme study:** does the weekly high/low actually form Tue/Wed more
than chance? **Measure** the day-of-week distribution of weekly extremes per
instrument. (Testable; sources never proved it.)
**Asian-range-sweep:** does London sweeping the Asian range precede a
directional move? Measure.

---

## D. Premium-window focus (where we actually trade)

Per the user's directive — **few, high-probability trades in peak-liquidity
windows.** Restrict live signals to the **London–NY overlap (08:00–11:00 ET)**
and the **London open killzone (02:00–05:00 ET)**, *only if* the event-study
base rates in those windows beat the all-hours base rate with statistical
significance. Size by **fractional Kelly off the measured conditional edge**
(already in `backtest/sizing.py`), capped, with the holiday filter forcing
flat.

---

## E. What "learning from the past" means here (no black box)

The engine maintains a table: `(event_type, context_bucket) -> {n, win_rate,
mean_fwd_return, CI, oos_win_rate}`. As more history accrues, estimates
tighten. "Smarter and smarter" = **more data → narrower confidence intervals
and pruning of buckets that don't beat the null** — not a model that grows
more confident on the same evidence. Every bucket carries its sample size and
out-of-sample number so we never mistake noise for a clue.

---

## Build order

1. **Add open levels** (midnight ET, weekly Sun-18:00-ET) to `context`.
2. **Event-study engine** `kudbee_quant/events/`: event detectors + the
   conditional base-rate table with CIs.
3. **Recovery-curve study (A)** — the flagship "does it get recovered" answer.
4. **Daily-open second-test study (B)** — the user's exact question, with
   multiple-comparisons guards.
5. Wire significant, OOS-surviving buckets into a strategy; validate with the
   existing correlation-adjusted multi-asset harness before any capital.

**Stay humble:** the prior from everything we've measured so far is that most
of these buckets will *not* beat the null. That's the expected, healthy
outcome. The win is finding the few that do — and knowing the difference.

---

## First measured results (BTCUSDT, 1h, 4000 bars)

The engine is built and the two flagship studies have run. Both returned the
honest verdict, not the hoped-for one.

### Vector-candle recovery — the magnet thesis fails the null

First pass used a loose definition (price re-enters the candle box) and showed
**100% recovery within 1 bar** — but that is an **artifact**: adjacent crypto
candles overlap, so the next bar is trivially "in the box." Price continuity,
not a magnet.

Corrected to the meaningful definition (price must **leave** the zone, then
**return**), with a random equal-width zone as the null:

| horizon (bars) | vector recovered | random-zone null | edge |
|---|---|---|---|
| 5 | 13.9% | 23.2% | **-9.3%** |
| 15 | 46.3% | 51.4% | -5.1% |
| 60 | 77.5% | 75.1% | +2.4% |
| 240 | 87.6% | 87.4% | +0.2% |
| 1440 | 92.1% | 93.1% | -0.9% |

**Vectors are NOT special magnets.** Price returns to a vector zone at almost
exactly the rate it returns to any random nearby zone (~92% vs ~93% over 60
days). "Always gets recovered" is true only in the trivial sense that price
wanders back to most nearby levels eventually — the vector adds **no edge over
a coin-flip level**, and is actually *slower* to recover at short horizons.

### Daily-open "second test" — the Tuesday/NY question

The exact bucket requested (2nd test of daily open, Tuesday, NY session):
**n = 6, win rate 50%, 95% CI [19%, 81%] → noise.** Across all buckets,
**none** reached the minimum sample, none survived Benjamini–Hochberg FDR, and
win rates swung 14%–78% purely from small-sample variance. Cherry-picking
"Monday London 2nd test = 77.8%!" (n = 9) would be self-deception.

Honest answer: **with 4000 hours we cannot answer this — far too few events.**
Resolving it needs years of data (and likely a more liquid, less 24/7
instrument). This is the engine working: it refuses to manufacture an edge
from noise.

### Range exhaustion — the first real regularity

Bucketing bars by the % of the 14-day average daily range (ADR) already
consumed today, then measuring forward 12-bar range (in ATR units), BTCUSDT
1h shows a **clean, monotonic decline** on large samples:

| % ADR used | forward range (ATR) | n |
|---|---|---|
| 0–25% | 4.86 | 647 |
| 25–50% | 5.03 | 1084 |
| 50–75% | 4.02 | 896 |
| 75–100% | 3.26 | 619 |
| 100–150% | 2.91 | 478 |
| >150% | 2.80 | 254 |

Once price has used most of its average daily range, further expansion
shrinks. This is the range-exhaustion thesis, and it is **actually present**.
Honest caveats: (1) this is largely the well-known *volatility mean-reversion*
/ range-clustering effect, not unique alpha; (2) there is a possible
time-of-day confound (more % used ≈ more of the day elapsed) to disentangle;
(3) "smaller forward range" is not directly tradeable without a direction.
Still — it is the first relationship here that survives a large sample and is
monotonic. Worth pursuing (e.g. as a volatility/position-sizing input, or
mean-reversion setups near ADR-high/ADR-low projections).

### Confluence — the "stacking levels" thesis fails this test

The hypothesis: the more reference levels cluster at a zone, the higher the
reaction/reversal probability. Tested by scoring distinct levels within a
tolerance band of price and measuring reversal rate by score:

| confluence score | reversal rate | mean reaction (ATR) | n |
|---|---|---|---|
| 0 | 47–53% | 2.5 | 135–968 |
| 1 | 52–54% | 1.5–1.7 | 2042–2513 |
| 2 | 49–51% | 1.4 | 511–1815 |

Reversal rate sits at ~50% (coin-flip) **regardless** of confluence, at both
0.25 and 0.6 ATR tolerance; reaction magnitude actually *declines* with more
confluence (clustered levels occur in congested, low-volatility zones). On
BTC 1h with this level catalog, **confluence does not predict turning points
better than chance.** Caveat: scores rarely exceeded 2, so very-high-confluence
zones are rare at this timeframe; a different instrument/timeframe could
differ — but the thesis is not supported here, and we will not pretend it is.

**Net:** of everything tested, only range exhaustion shows a robust effect,
and it is a known volatility phenomenon rather than directional alpha. Staying
humble: the honest scoreboard so far is mostly nulls, which is the normal and
expected result of testing retail trading lore rigorously.

## Scenario sweep (15 directional setups) — and a caught lookahead bug

We built a battery of 15 mechanical, directional scenarios from vector candles
and the hybrid theory (vector momentum/fade, sweep reversals, ADR-band/
exhaustion fades, daily/weekly-open, Asian-range break/fade, Brinks breakout,
round-number rejection) and an OOS-ranked sweep across BTC/ETH/SOL/BNB.

First run looked like hope: `asian_break_fade` +9.56, `sweep_reversal_premium`
+5.20, `sweep_reversal` +4.78 median OOS Sharpe — 100% of assets profitable.
**Those Sharpes are higher than the fantasy dashboards we set out to debunk —
the tell of a bug, not an edge.** Root cause: the Asian-range high/low leaked
future info (full-session extreme mapped onto intraday bars). After the fix
(expose only the completed range), the same three collapsed to -0.47, -0.56,
-0.57. The full corrected board has **no scenario with a meaningful positive
edge** (best: vector_at_daily_open +0.27, ~noise on correlated assets).

Honest standing: across PVSRA-MM, vector recovery, daily-open retests,
confluence, and now 15 directional scenarios, the only survivor is range
exhaustion (a known volatility effect). The research agents surfaced many more
precise BTMM setups still worth coding (M/W second-leg + 13/50 EMA cross,
Asian stop-hunt with a <40-pip-range filter and 25-30-pip breach, railroad-
track reversals, the 5/13/50/200/800 EMA stack) — these are the next batch to
test, with the same null-first discipline that just caught a Sharpe-9.56 lie.

## BTMM/PVSRA precise-setup batch (10 more) + a permanent lookahead guard

We implemented the precise setups (docs/research/btmm_pvsra_setups.md): EMA
13/50 cross + close filter, 50/800 trend filter, trend-pullback, the REAL
Asian stop-hunt (smooth-range + breach-and-reclaim, no-lookahead), Brinks/
shadow-box ORB, railroad-track, M/W second-leg (swing-pivot neckline),
vector-zone retest, sweep+opposing-vector, and `vector_at_monthly_open`
(recorded from @KudbeeX's M0 call). We also added a **lookahead self-audit**
(`scenarios/audit.py`): it recomputes the full pipeline on data truncated at t
and checks signal[t] is unchanged. All 25 scenarios pass (0% leak) — the guard
that makes the Sharpe-9.56 bug impossible to ship again.

Sweep result (BTC/ETH/SOL/BNB, 1h, OOS-ranked):

| scenario | median OOS Sharpe | profitable OOS |
|---|---|---|
| ema_trend (50/800) | +2.18 | 75% |
| ema_trend_pullback | +0.59 | 75% |
| vector_at_daily_open | +0.27 | 75% |
| ema_cross_13_50 | +0.15 | 50% |
| vector_at_monthly_open | -0.00 | 50% |
| asian_stophunt | -0.15 | 50% |
| brinks_orb | -0.18 | 50% |
| railroad_track | -2.03 | 0% |
| mw_second_leg | -3.09 | 0% |
| (all others) | negative | <=50% |

**Honest read:** the only clearly-positive scenario is `ema_trend` — plain
50/800 EMA trend-following. That is **crypto beta** (trend-following a rising,
correlated market), NOT vector/hybrid alpha; it would likely fail on
uncorrelated assets and in chop, exactly like pvsra_mm did. The *precise
Traders Reality / BTMM setups* (Asian stop-hunt, Brinks ORB, railroad-track,
M/W second-leg, vector-zone retest) are flat-to-negative on BTC majors. The
recorded `vector_at_monthly_open` is dead-noise (0.00). So the mechanical,
systematic versions of these setups do not show edge here.

Important distinction: this tests the *mechanical* rule. A skilled
discretionary trader reading live context (as in the DOT imbalance call, which
is playing out directionally) may outperform the naive mechanical rule — that
is real discretionary skill, not a systematic edge we can yet encode or trust
blindly.

## Full ICT/Hybrid batch (30 scenarios, Vol 1-3) — comprehensive null

After integrating research Vol 1-3 we added the price-only microstructure
primitives (session VWAP, premium/discount dealing range, Fair Value Gaps,
macro/Silver-Bullet/Brinks time windows) and five ICT setups (vwap_reversion,
turtle_soup, fvg_fill, silver_bullet, judas_thirds). All 30 scenarios pass the
lookahead audit (0% leak). Sweep (BTC/ETH/SOL/BNB, 1h, OOS):

- Positive: `ema_trend` +2.66, `ema_trend_pullback` +1.48 — crypto
  trend-following BETA, not alpha.
- Marginal/noise: `ema_cross_13_50` +0.21, `brinks_orb` +0.13.
- Every "smart money" setup is NEGATIVE OOS: silver_bullet -0.14, turtle_soup
  -1.69, judas_thirds -1.98, fvg_fill -2.91, vwap_reversion -3.95, plus all the
  Vol-1/2 setups from before.

**Conclusion:** none of the individually-mechanized PVSRA/BTMM/ICT setups beat
the null on 1h crypto majors. The only systematic positive is trend-following
beta.

### The one faithful test still outstanding: CONFLUENCE STACKING

Crucially, the research's *own* thesis (Vol 2 §14) is not that any single
setup wins — it is that **stacked confluence** wins (Tier 1 = kill zone + AMD
phase + macro window + sweep+MSS + FVG-over-breaker + 50 EMA + HTF bias +
premium/discount + day-of-week, ALL aligned). We have been testing factors in
ISOLATION. We now hold the full factor library (FVG, premium/discount, sweep,
EMA, macro, sessions, day-of-week, vectors) needed to build the Tier confluence
score and test the actual claim: *do high-confluence bars outperform
low-confluence bars, out-of-sample?* That is the next, and most faithful, test
— and it is the methodology's real hypothesis, still unfalsified either way.
(Note: full Tier-1 also needs funding/OI/liquidation/CVD data not yet wired,
and HTF/4h-weekly timeframes where the trader actually applies these.)

### Confluence-stack test — the central thesis, falsified (price-only)

We built it (`confluence/stack.py`): each bar gets a directional vote from
every causal ICT/Hybrid factor (EMA stack/fast/cloud, VWAP, daily-open, pivot,
premium/discount, sweep, vector, FVG), summed into a confluence score; then we
measure whether forward return IN the voted direction wins more as the score
rises. Result (BTC 1h, BTC 4h, ETH 4h — consistent):

- Win-rate stays at coin-flip (~44-53%) across strength levels — **no
  monotonic climb.**
- The FDR-significant buckets are *losers* (BTC-1h strength-3 = 44.2%; ETH-4h
  strength-4 = 44.5%).
- High-strength buckets tend to *underperform* (BTC-4h strength-8 = 37.5% with
  -0.89% mean return; ETH-4h strength-7 = 38.5%) — consistent with "obvious,
  crowded setups are already priced in."

**Conclusion: stacked confluence, as a price-only mechanical signal, does not
produce the predicted edge — it is flat-to-slightly-contrarian.** Combined with
every prior null, the honest scoreboard is: nothing price-based beats the null
except trend-following beta.

### The one genuinely-different untested frontier

Everything tested so far is PRICE-derived. The Vol-3 Tier-1 factors we have NOT
wired are a different kind of data entirely: **funding rates, open interest,
liquidation heatmaps, CVD, order-book imbalance** — derivatives/order-flow
microstructure. Liquidation cascades and funding extremes are real, documented,
exploitable phenomena that price-only TA cannot see. That data layer — not more
price patterns — is the honest next hypothesis worth building. It may also be
null; but it is genuinely new information, not a recycled price signal.

### BREAKTHROUGH: the R:R lens — confluence has positive expectancy

The trader's correction: we were measuring WIN-RATE and fixed-time exits, but
the strategy is asymmetric R:R — enter at a confluence, tight stop (1R), bigger
target (2R+), willing to lose small to win big. A 38-40% win rate is profitable
at 2R (breakeven 33%). So we built a bracket (stop/target) backtester measuring
EXPECTANCY IN R, and re-ran everything.

Result (confluence_stack, BTC/ETH/SOL/BNB, 1h, OUT-OF-SAMPLE last 30%, costs in):
- Positive expectancy on ALL FOUR assets: BTC +0.266R (PF 1.46), ETH +0.117R
  (1.19), SOL +0.178R (1.30), BNB +0.294R (1.53); ~105-115 trades each.
- Beats the null: always-long brackets LOST (-0.100R median), random LOST
  (-0.063R) over the same OOS window — so this is NOT just an uptrend.
- Monotonic in confluence strength (the methodology's core claim): median OOS
  expectancy rises +0.068R (>=3) -> +0.099R (>=4) -> +0.222R (>=5) at 2R, and is
  positive across the full strength x target_R grid.

First result to survive the null tests; confirms BOTH the trader's R:R insight
AND the confluence-stacking thesis — invisible to win-rate testing.

REMAINING VALIDATION (before any capital — staying humble):
1. Correlated assets (4 majors ~ 1.2 independent bets). Need uncorrelated + more.
2. Single OOS window (~50 days, one regime). Need walk-forward incl. bear/chop.
3. Threshold/cost sensitivity; realistic scalp slippage.
4. Confluence includes trend factors, so part is well-executed trend capture
   with good R:R (better than naive trend, which lost) — to be characterized.

Status: a robust, null-beating, thesis-confirming SIGNAL on crypto majors — not
yet proven alpha, but the first real lead, and it is the trader's own framework.

### VALIDATION: confluence-R survives the full gauntlet

The lead was put through the test that killed every prior candidate: walk-forward
across 6 consecutive windows, 6 assets INCLUDING uncorrelated ones (gold, S&P),
with cost sensitivity. Result (confluence strength>=5, 2R, 0.02R cost):

- 36 cells (6 assets x 6 folds), **75% POSITIVE**, median +0.148 R/trade.
- **Cross-asset correlation 0.00** — GLD 5/6 folds positive, SPY 5/6 positive.
  The edge GENERALIZES to genuinely uncorrelated markets => it is NOT crypto beta.
- Cost-robust: 0.00R -> +0.168 (81%); 0.02R -> +0.148 (75%); 0.05R -> +0.118
  (72%); 0.10R -> +0.068 (67%). Survives heavy slippage.
- Only fold 2 was broadly weak (one regime) — honest, expected.

This is the first candidate to survive walk-forward + uncorrelated assets + cost
sensitivity. Remaining before capital: more historical eras (crypto folds span
~one era; equities span ~2y and already add regime diversity), in-sample
parameter-selection caveat (min_strength=5/2R chosen from a grid that was
positive throughout), and FORWARD/paper validation on live data. Status:
a genuine, cross-asset, cost-robust, walk-forward-validated EDGE CANDIDATE.

### Threshold calibration: confluence as a PERCENTAGE, and a ~50% floor

The trader noted the threshold should be a percentage, not 5/5 ("I'd take a 3/5
or 4/5"). Reconciled by aligning denominators: the system has ~10 factors, so
"3 of 5" = 60% = strength 6/10, NOT strength 3. Marginal (exact-strength) OOS
expectancy (crypto majors, 2R, costs in):

| exact strength | %    | win% | exp_R  |
|----------------|------|------|--------|
| 3/10           | 30%  | 33%  | -0.074 |  (loses)
| 4/10           | 40%  | 36%  | +0.013 |  (breakeven)
| 5/10           | 50%  | 42%  | +0.214 |  (edge)
| 6/10           | 60%  | 40%  | +0.142 |
| 7/10           | 70%  | 43%  | +0.224 |

So 50%+ confluence is the tradeable zone (the trader's "~3 of 5" is right once
denominators match); there is a FLOOR near 50% — below ~40% it stops paying.

Confidence-scaled SIZING was tested and did NOT help: flat full-size at >=50%
gave total +91.2R, exp +0.210, per-trade-Sharpe +0.144 — better than sizing by
confluence (+24.6R, Sharpe +0.125) or reaching down to 40% (+16.0R, +0.070).
Conclusion: take every >=50%-confluence setup at full size and stop there;
don't down-size mid setups or reach for weak ones. Threshold is now a tunable
percentage (confluence_pct / min_pct); paper-scan defaults to 0.5.
