# Recorded setups from @KudbeeX posts (own trade calls)

Source: two X/twitter posts by @KudbeeX (the project owner), captured via the
public syndication endpoint (the pages themselves are login-gated). Charts in
the posts could not be machine-read; the mechanical core below is extracted
from the post text and mapped to our testable engine.

## Post 1 — SOL/USDT "M0 pivot + green vectors" (2025-12-31)
Verbatim: *"SOL/USDT — Hybrid system breakdown. Price kissed the M0 pivot and
bounced.. classic area for liquidity grabs. Notice green vector candles forming
at the lows: smart money accumulation in progress, retail angst in the
rearview."*

Mechanical core:
- **M0 pivot** = the monthly open (start-of-month reference level). "Kissed and
  bounced" = price tests the monthly open and reverses.
- **Liquidity grab** at that level (sweep of the lows around M0).
- **Green (bull) climax vector candles forming at the lows** = the confirmation
  / accumulation signal.
- Bias: **LONG** off the monthly open when bull vectors print into it.

Testable scenario: **bull climax vector within tolerance of the monthly open
→ long** (mirror: bear climax near monthly open → short). Optionally require a
prior sweep of the low (sweep_bias > 0). Implemented as `vector_at_monthly_open`
and tested in the sweep with the lookahead audit.

## Post 2 — SOL monthly PVSRA "imbalances / vectors" (2026-02-11)
Verbatim: *"the truth is in the vectors!! … monthly SOL chart … classic setup
using the PVSRA (Price, Volume, Support/Resistance Analysis) from Tino's Traders
Reality hybrid system"* (imbalances on the monthly timeframe).

Mechanical core: monthly-timeframe **vector candles marking imbalances** traded
against monthly **support/resistance**. This is the higher-timeframe version of
the same idea — vectors at a monthly level. Covered by the same
`vector_at_monthly_open` test plus the existing `vector_zone_retest`
(unrecovered-vector magnet) on a monthly/representative timeframe.

## Post 3 — DOT/USDT "imbalance fill" weekly target (2025-12-21)
Verbatim: *"History (2000/2008 stock crashes & past DOT cycles) proves these
imbalances drag price down to fill the zone—current level (~$1.84) doesn't
matter. Targeting $0.60 or lower with full recovery on the weekly timeframe.
#PVSRA #Polkadot"*

Mechanical core:
- An **unfilled imbalance / unrecovered vector zone** sits BELOW price on the
  weekly. Thesis: price is "dragged" down to fill it regardless of the current
  level → **directional bearish bias toward the zone** (target ~$0.60).
- This is the high-timeframe, directional version of the "vector always gets
  recovered" magnet idea: trade TOWARD the nearest large unfilled zone.

Outcome so far (as of ~2026-06): DOT fell from ~$1.84 (call) to **~$0.95** —
**directionally correct and in progress** toward the $0.60 target. Honest
caveat: one correct directional call is not statistical edge — DOT was in a
broad downtrend, so this is consistent with both "imbalance magnet" and "it
was just going down anyway." It counts as a data point, not proof.

Testable scenario: **trade toward the nearest unfilled vector/imbalance zone**
as a target/bias (distinct from fading at the zone). Worth building as a
directional "magnet target" study on higher timeframes, benchmarked against a
null (does price reach the unfilled zone more than a random equidistant level?
— our recovery study found vectors recover at ~null rate intraday, so the
honest expectation is skeptical, but HTF directional framing is untested).

## Honesty note
These are discretionary chart calls (single examples, hindsight-framed). They
become evidence only when the underlying rule is measured across many
instances out-of-sample — which is exactly what the scenario sweep does. We
record the rule, then let the data judge it; one good-looking SOL chart is a
hypothesis, not an edge.
