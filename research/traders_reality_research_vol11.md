# Traders Reality Quant Bot — Research Database Volume 11
## "Always watch the dollar" — DXY intermarket read + previous-session value-area-high trap

**Research date:** 2026-06-26
**Source:** 5 short Traders Reality (Tino) clips shared by the owner today
(IMG_9843, IMG_9844, IMG_9845, IMG_9846, IMG_9850). Caption on every clip:
*"Always watch dollar #btc #dollar #nasdaq."*
**Status:** CAPTURED, NOT VALIDATED, NOT WIRED LIVE. This is a hypothesis log,
consistent with the standing rule (`docs/MEMORY.md`, `CLAUDE.md`): the edge is
honesty + execution, not more signals — nothing here goes into the live book
without a significance-gated backtest.

---

## 1. What the clips actually say (verbatim captions, in sequence)

The five clips tell one continuous market read. Stitched together:

1. **"…trading at value area high from the previous session over…"**
   — chart shown is a volume/market-profile view; price is pressing the
   **previous session's Value Area High (VAH)**.
2. **"…for a trap to then reverse it back down again."**
   — the move into VAH is framed as a **liquidity trap**: push above the level
   to trip stops/late longs, then **reverse down**.
3. **"…of this move to the upside, euro is down / dollar [up]…"**
   — the reversal is corroborated by **intermarket**: EUR down ⇒ **DXY up**.
4. **"The Nasdaq starts to pull back, then we'll start [the move down]."**
   — dollar strength leads risk: **Nasdaq (and BTC) pull back** as the dollar
   bids.
5. **Caption throughout:** *"Always watch dollar."* — DXY is the lead tell for
   BTC/Nasdaq direction.

**Unified thesis (Tino's read):** price rallies into the *previous session's*
volume-profile **Value Area High**, prints a **trap/liquidity-grab**, and
**reverses down**; the reversal is confirmed by **DXY strength** (EUR weakness),
which drags risk assets (Nasdaq, BTC) lower. "Always watch the dollar."

---

## 2. Is this new to our database? No — it reinforces existing themes

- **DXY / dollar inverse correlation** to BTC/Nasdaq is already documented in
  this series (vols 3–9 all reference dollar correlation). Today's clips add
  conviction and a concrete *mechanism* (VAH trap + DXY confirmation) but no
  genuinely new primitive.
- **Value Area High / volume-profile levels** overlap with our existing levels
  work; the bot's confluence already scores session/profile-style levels, but it
  does **not** currently key off the *previous session's* VAH specifically, nor
  off an external DXY series.

So the two potentially-new, *testable* ideas are: (a) a **previous-session VAH
trap-reversal** entry, and (b) a **DXY-regime filter/confirmation** on existing
signals.

---

## 3. Honest applicability to THIS bot (crypto top-10, 1h, confluence-R)

The live book is: validated ≥50% confluence, 3R target, 0.25-ATR maker retrace,
both sides, TOP_10_CRYPTO on 1h. Against that:

- **DXY-regime filter (candidate, NOT live).** "Only take longs when DXY is
  not rising / only take shorts when DXY is rising." Plausible and cheap to
  test, BUT:
  - Crypto trades 24/7; DXY (futures/FX) has gaps and session-bound liquidity —
    alignment/timezone handling is non-trivial and a known foot-gun.
  - It is a **directional regime overlay**, exactly the kind of "more signal"
    the thesis warns against unless it clears the bootstrap significance gate.
  - **Required before any live wiring:** a read-only backtest that adds a DXY
    state to each 1h bar and measures expectancy *with vs without* the filter on
    the SAME validated population, gated by the existing significance harness.
    Net > 0R after fees AND `boot_p` through the gate, or it stays off.
- **Previous-session VAH trap-reversal (candidate, NOT live).** Needs (i) a
  session definition for 24/7 crypto (UTC day? CME-style?), (ii) a volume-profile
  VAH computation per session, (iii) a "sweep-then-reject" trigger. This is a
  *new entry model*, not a tweak — heavier lift, and discretionary as Tino runs
  it. Backtest-first, same gate.

**Verdict:** useful as *context/candidates*, **not** something to apply
mechanically today. Both must go through `research/`-style backtests behind the
significance gate before they could ever graduate to the live book. Wiring either
in now would violate the parsimony/no-unvalidated-signal line.

---

## 4. Concrete next step (queued, not done)

Added to `docs/research/overnight_idea_backlog.md` as an encodable hypothesis:
a **DXY-regime gate** to be measured by the existing harness (read-only, OFF by
default), since it's the cheaper of the two to test honestly. The VAH
trap-reversal entry is logged there too as a larger engine-extension idea.

*No live flag, workflow, resolver, bracket, or journal logic was touched by this
volume — it is a research note only.*
