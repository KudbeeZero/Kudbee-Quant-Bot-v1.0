# Overnight idea backlog

Candidate edges proposed by the research agents that are NOT yet encoded in
`scripts/overnight_candidates.py`, usually because they need a small engine
extension before they can be tested honestly. The overnight loop appends fresh
ideas here each cycle; encode the promising ones into the registry, then let the
harness measure them. Nothing here is believed — it is a TODO list of hypotheses.

## Needs an engine extension to `kudbee_quant/backtest/bracket.py`

The bracket backtester today supports: fixed ATR stop, fixed R target, TP1 partial
+ break-even-after-TP1, and a bar time-stop. The following need NEW path-dependent
exit logic (track MFE/MAE since entry, ratcheting stop). Add them with the same
conservative within-bar ordering (stop checked before target) so no lookahead.

1. **ATR / Chandelier trailing stop** (agents' top execution pick). Trail the stop
   at `highest_high_since_entry - mult*ATR` (long; mirror short), ratchet only
   favorably. Hypothesis: captures the fat right-tail runner the fixed 3R caps.
   Sweep mult ∈ {2.5, 3.0, 3.5}; compare to fixed-3R baseline.
2. **MAE "give-up" early exit.** If by bar K (e.g. 6) max-adverse-excursion ≥ 1.0R
   and max-favorable < 0.5R, exit at market instead of waiting for the 1.5-ATR
   stop. Cuts the average loss on wrong-thesis trades.
3. **Time-decay target.** Start target at 3R, decay linearly toward 1R as the
   trade ages over the 24-bar window — harvest stale trades instead of a random
   time-stop mark-out.
4. **Break-even-after-1R + runner** (no scale-out). Move stop to entry once MFE
   hits +1R, leave the 3R target on. (Distinct from the existing TP1 path, which
   also banks a partial.) Tests pure left-tail reduction.
5. **Target as a multiple of recent swing range** instead of ATR — anchor the
   target to realized swing amplitude (rolling 20-bar high-low) rather than smoothed
   volatility.

## Encodable now (no engine change) — enqueue when the queue runs low

- **Volume dry-up + coil combo**: coil (narrow range) AND prior-bar volume in the
  bottom quartile — the classic accumulation-then-expansion tell.
- **Inside-bar breakout entry offset**: after an inside/NR7 bar, enter at the prior
  bar's extreme in the signal direction instead of the 0.25-ATR retrace (needs the
  candidate to return a modified entry — approximate with a shallower retrace gate
  on inside-bar bars).
- **Hour-of-day expectancy** (with strict out-of-sample care; MEMORY §16 flagged
  NY hours 1–4 as suggestive but data-mining-risky — only with walk-forward).
- **Monday/weekend-gap effect** in crypto (continuation vs fade of the weekend drift).

## From Traders Reality (Tino) clips, 2026-06-26 — see research/traders_reality_research_vol11.md

- **DXY-regime gate** (cheaper to test first; needs an external DXY series + 24/7
  alignment). "Always watch the dollar": skip/penalize longs when DXY is rising
  and shorts when DXY is falling. Add a DXY state per 1h bar; measure expectancy
  WITH vs WITHOUT the gate on the SAME validated top-10/1h population, behind the
  bootstrap significance gate. Net > 0R after fees AND `boot_p` through the gate,
  or it stays OFF. Directional regime overlay — exactly the "more signal" the
  thesis distrusts, so it must clear the gate, not just look good.
- **Previous-session VAH trap-reversal entry** (larger lift — a NEW entry model,
  not a tweak). Needs a 24/7 crypto session definition, a per-session
  volume-profile Value Area High, and a sweep-then-reject trigger. Backtest-first,
  same significance gate, before any thought of live wiring.
