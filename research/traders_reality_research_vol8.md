# Traders Reality Research — Volume 8
## Tino's Hybrid System: Deep-Dive Rules, Patterns & Decision Framework
**Branch:** claude/crypto-confluences-research-cxrtp3  
**Research Date:** June 2026  
**Sources:** tradersreality.com public content, TradingView indicator docs, Scribd PDFs (TR-pdf-1, Guidebook V5, Masterclass Part 5, Indicator Settings Guide), Liberate the Pips class notes, Cryptorum guide, BTMM foundational PDFs, HowToTrade.com BTMM guide, UDCourse, Trustpilot reviews, TraderLife interview

---

## OVERVIEW

This volume compiles 10 deep-research investigations into Tino's Hybrid System, covering every publicly verifiable rule, threshold, and criterion. These are the operational rules that drive the system — what to look for, when to enter, when to stay out, and how to combine signals. Content that is behind the paid membership paywall is clearly marked as unconfirmed.

---

## SECTION 1: NEWS EVENT TRADING RULES

### 1.1 Core Philosophy: The Fast Move Is the False Move

Tino's fundamental rule for all news events:

> "When you see quick, dramatic candles form in one direction, treat it as Market Maker activity — a spike designed to induce retail traders to follow, while the MM's actual intent is to pull price in the opposite direction."

**NEVER chase the initial news move.** The first violent candle on NFP/FOMC/CPI is almost always a stop-hunt, not a genuine directional move. The entry comes *after* the spike exhausts and reverses.

### 1.2 The Rule of Threes at News Events

- Market Makers extend highs and lows in threes
- Always take notice of **three vector candles in one direction** or **three pins to a high/low** — this signals exhaustion
- After news spike: three consecutive vector candles in the news direction = MM exhaustion signal, not continuation confirmation

### 1.3 Calendar Usage: Stay Out, Not Trade In

- Tino uses **FXStreet** and **Forex Factory** to check major announcements
- Philosophy: **"No news is good news"** — the calendar tells you WHEN TO STAY OUT, not when to trade
- High-impact events (3-star) are danger zones first; only participate after the spike completes

### 1.4 News as a Brinks Box Amplifier

- If news hits during or near a Brinks Box window, it amplifies the stop-hunt dynamic
- The Brinks Box thesis (MMs trapping stops before showing true direction) is **reinforced**, not negated, by news
- Post-news: look for the Brinks Box setup to form as the dust settles

### 1.5 50 EMA as Post-News Filter

- Choppy post-news candles that whipsaw around the 50 EMA = **no-entry signal**
- Wait for price to clearly establish itself above or below the 50 EMA cloud after news volatility settles
- The 50 EMA cloud entry (vector candle + retrace + hold) still applies post-news; just requires the candle close to be clean

### 1.6 When NOT to Trade (Timing Rules)

| Avoid Trading When | Reason |
|-------------------|--------|
| Mondays | MMs setting direction traps; small moves, fake breakouts |
| End of session | London close → NY direction change; known MM trap zone |
| Weekends | No institutional participation; patterns unreliable |
| Gap downs at day open | MM stop-hunt tactic |
| During live/unclosed news candle | Never enter on an open candle |
| End of week (Friday PM) | Don't carry positions over weekend |

### 1.7 Specific Post-News Rules (Confirmed as Consistent with System Logic)

1. Wait for the initial spike to complete (typically 1-3 candles)
2. Watch for reversal vector candle forming at the spike extreme
3. Look for the 50 EMA to act as a reference — is price defending or rejecting it?
4. Three vector candles in the news direction = exhaustion; potential reversal entry
5. **Exact candle-counting rules after news are behind the paid Platinum course** — Tino's specific "X minutes before/after news" rules are not publicly available

---

## SECTION 2: BRINKS BOX COMPLETE RULES

### 2.1 Definition

The Brinks Box is:

> "An area that should be seen as the set-up for the session. This is where most stop hunts appear. It's initiating the setup of intention by the market makers. Not all brinks boxes mean that price will recover any previous move — it's a moment in the markets before the actual market opens where stops are hit to set up the market makers' intention."

### 2.2 Session Time Windows (Confirmed)

| Session | Time Window (UTC) | EST Equivalent |
|---------|-----------------|---------------|
| EU / London | **08:00–09:00 UTC** (DST OFF) | 3:00–4:00 AM EST |
| US / New York | **14:00–15:00 UTC** (~8–9 AM EST) | 9:00–10:00 AM EDT |
| Asia | Not publicly confirmed | Not confirmed |

**DST note:** The indicator has DST adjustment built in. When US/UK are both on DST, London open moves to 07:00 UTC and the EU Brinks adjusts accordingly.

**Source confidence:** EU 08:00–09:00 UTC is HIGH confidence (multiple public sources). NY 14:00–15:00 UTC is confirmed from TradingView indicator description.

### 2.3 How the Box Is Measured

- **Upper boundary = session high of the Brinks time window**
- **Lower boundary = session low of the Brinks time window**
- The indicator draws these as colored rectangles extending forward in time
- Box extends until broken; then used as ongoing S/R reference

### 2.4 Price Behavior Inside the Box

1. Price "chops" — visible consolidation
2. Market Makers are **building positions** inside the range
3. Stop hunts occur — fast wicks above AND below the box on both sides to trigger retail stops
4. This is the "Judas" move within the box: false breakout in one direction before real move

### 2.5 What Makes a Valid vs. Invalid Box

| Valid Brinks Box | Invalid / Low-Quality Box |
|-----------------|--------------------------|
| Clear consolidation during the time window | No clear range; already trending hard |
| Wicks probing both sides (stop hunt evidence) | Only one-sided movement |
| Box forms at or near a key S/R level | Box forms in empty price area |
| EMA position clear relative to box | EMAs in confusion (crossovers happening inside box) |

### 2.6 Trade Direction: Against the Initial Breakout (Judas Swing)

**Critical rule:** The breakout OUT of the Brinks Box at session open is typically the **Judas Swing** — the false move designed to trap retail.

- If price breaks **UP** out of the Brinks Box → look to **short** (Judas Swing bearish)
- If price breaks **DOWN** out of the Brinks Box → look to **long** (Judas Swing bullish)

**Context-dependent exception:** Sometimes the breakout IS the real move. The determination uses PVSRA volume confirmation + ADR position + broader EMA structure. If a massive green Climax Vector breaks above the box with full EMA stack alignment → the breakout may be the real move (trade with it).

### 2.7 The 50% Midpoint

- The 50% midpoint of the Brinks Box is used as a **re-entry zone** after initial breakout
- Used as a **decision level**: price above midpoint = bullish bias; below = bearish bias
- Functions as "Consequent Encroachment" (ICT terminology) or simply the mean of the range

### 2.8 Stop Loss Placement

- **Long trade (after Judas Swing down):** Stop below the **low of the Brinks Box**
- **Short trade (after Judas Swing up):** Stop above the **high of the Brinks Box**
- Stop = opposite side of the box from the entry direction

### 2.9 Profit Targets

1. **Primary target:** Opposite boundary of the Brinks Box
2. **Extended targets:** ADR levels, AWR levels, M-Levels (psychological round numbers), Pivot Points, previous session high/low, Vector Candle Zones
3. **"Straight Away" play:** When NY opens and Brinks sends price into a stop hunt then reverses to move lower without retraces — run to full ADR target

### 2.10 How Brinks Box Integrates with BTMM (Induce-Trap-Shift)

| BTMM Phase | Brinks Box Action |
|-----------|------------------|
| Induce | Box forms; price ranges inside, setting up the trap |
| Trap | False breakout of box at session open (the Judas Swing) |
| Shift | Reversal back through the box and beyond = entry direction |

---

## SECTION 3: RISK MANAGEMENT (CONFIRMED PUBLIC RULES)

### 3.1 What Is Confirmed Publicly

**Specific percentages and formulas are in Module 5 of the paid Scalp Trading Hybrid System course.** No public source has leaked the exact numbers. What IS confirmed:

| Rule | Source |
|------|--------|
| Keep position sizes **light during drawdowns** | Blog post (squarespace) |
| "NEVER FORCE A TRADE" | Dedicated blog post title |
| Exits driven by **vector candle patterns**, not fixed R targets | Course description |
| "Losses are Gold" — reframe losses as data | Book + 64 wisdom tweets |
| "Always, Always, Always pay yourself" — longevity rule | 64 wisdom tweets |
| "You need only a 50% win rate" — money management creates profitability | 64 wisdom tweets |

### 3.2 Pattern-Driven Exits (Confirmed)

Tino's exit methodology is **not fixed-pip or fixed-R**: exits are based on vector candle patterns. The course description states: "having a set place to take profit or take loss, based off the pattern in vector candles." This means:

- When a **reversal vector candle** appears against your trade direction = consider exit
- When **3 vector candles** have pushed in your favor = consider partial exit (exhaustion)
- When price reaches a **key S/R level** (round number, pivot, Vector Candle Zone) with a reversal signal = exit

### 3.3 Scale-In Structure (BTMM-Derived)

Three-position scale-in approach (confirmed from BTMM/TDI framework):
1. **Entry 1:** Shark Fin on TDI appears
2. **Entry 2:** Market Base Line cross ("Blood in the Water") — RSI crosses yellow MBL
3. **Entry 3:** Breakout of opposite volatility band during the trend run (continuation)

### 3.4 Drawdown Survival Rules

1. Keep sizes light; withstand variance without psychological damage
2. Maintain calm through mindfulness practices
3. Use drawdowns as diagnostic tools — what fault do they expose?
4. **Do NOT increase size to "make it back"** — this compounds the drawdown
5. Time away from markets (2-week abstinence protocol) resets psychological baseline

### 3.5 Circuit Breakers (Consistent with System Logic)

- "Never trade angry" = emotion-based hard stop
- "Never be excited to trade" = excitement = red flag for ego trading
- "Two consecutive losses" implied as a signal to step back (consistent with psychology framework)

---

## SECTION 4: PVSRA ENTRY TRIGGERS — COMPLETE RULES

### 4.1 Vector Candle Color Code (Confirmed)

| Color | Type | Volume Condition | Directional Signal |
|-------|------|-----------------|-------------------|
| **Lime/Green** | Climax Up | ≥200% avg volume AND spread×vol ≥ 10-bar highest | Extreme institutional buying |
| **Red** | Climax Down | ≥200% avg volume AND spread×vol ≥ 10-bar highest | Extreme institutional selling |
| **Blue** | Rising Up | ≥150% avg volume | Above-average buying |
| **Violet/Purple** | Rising Down | ≥150% avg volume | Above-average selling |
| **Light Grey** | Normal Up | Below 150% | Price closed higher, normal vol |
| **Dark Grey** | Normal Down | Below 150% | Price closed lower, normal vol |

**Baseline:** Compared against prior **10-candle average volume.**

### 4.2 Counter-Intuitive PVSRA Interpretation

**The color does NOT mean what retail traders think:**
- Green/Blue Climax = MM *appearing* to buy — could be MM SELLING INTO retail longs (distribution)
- Red Climax = MM *appearing* to sell — could be MM BUYING from retail shorts (accumulation)

The context (price location, EMA position, session timing) determines whether a Climax vector is genuine accumulation or deceptive distribution.

### 4.3 Core Entry Rule 1: 50 EMA Filter (Non-Negotiable)

- **Long trades ONLY:** Price above the 50 EMA cloud
- **Short trades ONLY:** Price below the 50 EMA cloud
- Never take a trade if there is no clear expansion (fanning) of the EMAs

### 4.4 Core Entry Rule 2: Rise-Retrace-Confirmation (Primary Entry Pattern)

**For a long entry:**
1. A **green or blue vector candle** breaks through the 50 EMA cloud upward (the "Rise")
2. Price **retraces back to the 50 EMA cloud** — must be a solid retrace, NOT a quick wick
3. Price **holds the 50 EMA cloud as support** — does not close below it (the "Confirmation")
4. The confirmation candle close = **entry trigger**
5. Enter at the close of the confirmation candle or the open of the next

**For a short entry:** Mirror all conditions (red/violet vector, retrace to EMA from below, holds as resistance).

### 4.5 Core Entry Rule 3: Never Enter on the Vector Candle Itself

> "Always wait for the confirmation candle AND the retrace."

The vector candle is the SIGNAL; the confirmation candle closing in the trade direction is the TRIGGER. These are two different things and entry is always on the confirmation, never the vector.

### 4.6 Core Entry Rule 4: Vector Candle Reversal (VCR)

- **Bearish VCR:** Green Climax vector → immediately followed by Red Climax vector = MM showing hand, reversing down
- **Bullish VCR:** Red Climax vector → immediately followed by Green/Blue vector = MM done distributing, reversing up
- Three consecutive VCRs of the same type = strong directional signal: large pump (3× bullish VCR) or dump incoming

### 4.7 Core Entry Rule 5: The "First Vector" Bonus Strategy

A quick scalp setup:
1. A green/blue vector candle appears (or red/violet for shorts)
2. Enter on the close of that same vector candle in the direction it's pointing
3. Stop below/above the vector candle's wick
4. Target: nearest M-Level, pivot, or key S/R

**Note:** This is the "bonus" setup — faster, more aggressive, smaller target. The Rise-Retrace-Confirmation is the primary setup.

### 4.8 Vector Candle Zones (Unrecovered Liquidity)

- The indicator draws a **box at every vector candle location**
- The box stays active (**unrecovered**) until price moves through it completely
- **Price returning to an unrecovered Vector Candle Zone = high probability reaction point**
- Bullish zone retest + new green/blue vector = continuation long entry
- Bearish zone retest + new red/violet vector = continuation short entry
- **Opposing-color vector at zone** (e.g., red vector at bullish zone) = reversal entry signal
- Multiple zones stacked at the same price level = extremely strong S/R
- **Zone configuration:** Can use candle bodies only (tighter) or bodies + wicks (wider)

### 4.9 Key S/R Levels Where Vectors Are Expected

| Level | Priority |
|-------|---------|
| Whole numbers (1.3000, etc.) | **Most important** — consolidation above/below |
| Half numbers (1.3050) | Second most important |
| Quarter numbers (1.3025) | Third level |
| M Levels (M0–M5) | Tino's proprietary mid-point levels |
| Pivot Points (PP, R1/R2/R3, S1/S2/S3) | Standard reaction zones |
| 50 EMA zone (Dragon) | Dynamic S/R — most actively used |
| 200 EMA | Macro trend support/resistance |
| 800 EMA | Long-term macro S/R on HTF |
| Yesterday's high/low | Session range reference |
| Previous week's high/low | Weekly S/R |

### 4.10 Full Long Entry Checklist

| # | Condition | Requirement |
|---|-----------|-------------|
| 1 | Timing | Within or just after EU or US Brinks Box window (08:00–09:00 UTC or 14:00–15:00 UTC) |
| 2 | Macro trend | 50 EMA above 200 EMA on trading timeframe; 800 EMA pointing upward |
| 3 | Price location | Price above the 50 EMA cloud |
| 4 | EMA fanning | EMAs spread apart (fanned), not crisscrossing |
| 5 | Vector candle | Green (≥200% vol) or Blue (≥150% vol) at a key PVSRA zone |
| 6 | Retrace quality | Solid retrace (not quick wick) back to the 50 EMA cloud |
| 7 | Hold confirmation | Retrace holds cloud (no close below); confirmation candle closes above |
| 8 | No opposing Climax | No red Climax appearing at or before entry (would invalidate with bearish VCR) |

---

## SECTION 5: TDI — COMPLETE RULES

### 5.1 Exact TDI Version

**"TDI – Goldminds, edited for Market Makers Method by Jakub Donovan"**  
This is NOT a generic TDI. It is a BTMM-customized version.

### 5.2 Exact Settings (Confirmed)

| Parameter | Value |
|-----------|-------|
| RSI Period | **13** (original Steve Mauro used 21) |
| RSI Applied To | Close |
| Fast MA (Green Line) | **2-period Simple MA** of RSI |
| Slow MA (Signal/Red Line) | **7-period Simple MA** of RSI |
| Bollinger Band Period | **34** |
| Bollinger Band Deviation | **1.619** (NOT the standard 2.0) |
| Market Base Line (Yellow) | **34-period Simple MA** of RSI |
| Key Horizontal Levels | **32, 50, 68** |

### 5.3 TDI Line Definitions

| Line | Color | What It Is |
|------|-------|------------|
| RSI Price Line | **Green** | 2-period MA of RSI 13 — fastest, most responsive |
| Signal Line | **Red** | 7-period MA of RSI 13 |
| Market Base Line (MBL) | **Yellow** | 34-period MA of RSI 13 — the "equilibrium" |
| Volatility Bands | **Blue** | 34-period BB at 1.619 deviation around MBL |

### 5.4 TDI Crossover Signals

| Signal | Condition | Strength |
|--------|-----------|---------|
| Green/Red crossover | Green crosses above/below Red | Basic signal; stronger with steep angle |
| MBL cross ("Blood in the Water") | Green crosses above/below Yellow MBL | Medium-strong; institutional signal |
| Level 50 filter | Crossover above 50 = valid buy; below 50 = valid sell | Crossover AT 50 = lower quality |
| Yellow line level | Yellow rising from 32 zone = buy bias; falling from 68 = sell bias | |
| Band squeeze breakout | Bands compress then explode in direction of lines | Strongest signal |

### 5.5 TDI Bad Setup Filters (When NOT to Trade)

| Condition | Action |
|-----------|--------|
| Flat Market Base Line (Yellow) | **Avoid all trades** — chop environment |
| Tight/compressed Volatility Bands | Consolidation; crossovers get chopped |
| Green/Red angle nearly horizontal | No momentum; skip |
| Crossover at the 50 level | Lower quality; skip or reduce size |
| Fewer than 6 same-color candles before Shark Fin | Invalid fin — skip |
| Small/weak Shark Fin (barely outside band) | Lower quality — skip or reduce size |
| Fin after BB squeeze breakout | Risky; wait for next fin |
| RSI at 68+ for buy signal | Overbought; countertrend — skip |
| Weekend or Monday | MM traps most active — skip |

### 5.6 Shark Fin — Complete Rules

**Definition:** A Shark Fin forms when the **Green RSI Price Line breaks outside a Volatility Band** and then **reverses back inside**, creating a fin-like shape.

**Bearish Shark Fin:**
- Green RSI Line breaks **above** upper Bollinger Band (above ~68)
- Green Line then snaps **back below** that level
- Shape: fin pointing up
- Signal: price will likely continue **falling**

**Bullish Shark Fin:**
- Green RSI Line breaks **below** lower Bollinger Band (below ~32)
- Green Line then reverses **back above** that level
- Shape: inverted fin
- Signal: price will likely **rise**

**Minimum candle requirement (confirmed BTMM rule):**
- For a BUY Shark Fin: minimum **6 consecutive bearish (red) candles** before the fin
- For a SELL Shark Fin: minimum **6 consecutive bullish (green) candles** before the fin

**Quality grading:**
| Grade | Description |
|-------|-------------|
| Good | RSI barely pokes outside the band |
| Better | Larger extension, clean snap-back |
| **Best** | Large, pronounced fin visible "from space" (zoomed far out) |

**Primary scalping timeframe:** M1 (1-minute). Reported win rate: 80%+ on Gold and Indices when fins are properly identified.

**Avoid:** Fins immediately after a BB squeeze breakout — wait for the next fin setup.

### 5.7 Three-Position Scale-In Entry (Confirmed Framework)

1. **Entry 1:** Appearance of the Shark Fin on TDI
2. **Entry 2:** Market Base Line Cross ("Blood in the Water") — RSI crosses yellow MBL
3. **Entry 3:** Breakout of the opposite Volatility Band during the trend run

### 5.8 TDI + EMA Combo Rules

| Timeframe | Role |
|-----------|------|
| H4 | TDI Shark Fin on H4 = "green light for preparation" — setup alert only, not entry |
| H1 | 13 EMA crossing 50 EMA after H4 fin = swing-level entry trigger |
| M15/M5 | Exact entry timing via vector candle at 50 EMA |

**Reported backtested accuracy:** H4 Shark Fin + H1 13/50 EMA crossover + candlestick reversal at 50 EMA = ~65% accuracy.

---

## SECTION 6: COMBINED DECISION TREE (BTMM → PVSRA)

### 6.1 Critical Clarification: ICT Is NOT a Primary Pillar

Tino lists the system's influences as: "Supply and Demand, ICT, PVSRA, Price Action, BTMM, Liquidity Trading, Support and Resistance, Trendlines, Round Numbers, Psychological Levels, Divergences, and Multi-timeframe Analysis."

**ICT is one of many inputs, NOT a co-equal structural pillar.** The system is fundamentally PVSRA + Market Maker Method (BTMM). ICT vocabulary (Order Blocks, FVGs) are supplementary confluence, not the primary framework.

### 6.2 The 5-Check Decision Sequence

**All 5 must pass. Any single failure = skip or wait.**

| Check | Layer | Requirement |
|-------|-------|-------------|
| **1 — Session/Time** | BTMM Timing | Frankfurt/London (07:00–10:00 UTC) or NY (13:00–16:00 UTC). No Mondays, no weekends. |
| **2 — Cycle Position** | BTMM Macro | Where are we in the L1/L2/L3 cycle? Weekly direction from BTMM: Mon-Tue = trap, Tue-Wed = reversal, Wed-Fri = real move. W or M pattern direction established? |
| **3 — EMA Alignment** | Price Action + BTMM | Price above 50 EMA (longs) or below (shorts). EMAs "fanned" (spread apart). 50 EMA above 200 EMA for bullish trend confirmation. |
| **4 — Key Level** | S/R Confluence | Vector Candle Zone, Pivot Level, ADR boundary, psychological level, or session high/low nearby. Optional: OB or FVG coinciding with this level. |
| **5 — PVSRA Volume** | Execution | Green/Red (high vol) or Blue/Purple (medium vol) vector prints at the key level. Retrace is on low-volume gray candles. Price holds the 50 EMA without a body close through it. |

### 6.3 ICT Power of Three → BTMM Cycle Mapping

These describe the same institutional behavior under different vocabulary:

| ICT Power of Three | BTMM / Tino's Hybrid Equivalent |
|-------------------|--------------------------------|
| Accumulation (ranging, smart money builds) | Asian session / Induce phase |
| Manipulation (false breakout, stop run) | London open false break / Trap phase (3 pushes) |
| Distribution (real move) | London trend / Shift phase |

Tino uses BTMM language (induce/trap/shift, L1/L2/L3), not ICT terminology.

### 6.4 ICT Order Blocks + PVSRA Zones Overlap Logic

When ICT-style Order Block AND PVSRA Vector Candle Zone coincide at the same price level:
1. OB identified on H4/15M (last bearish candle before strong bullish impulse)
2. Price returns to that zone
3. PVSRA Vector Candle Zone overlaps with the OB
4. Green Vector Candle prints inside or off that combined zone = entry
5. 50 EMA in agreement

**The overlap logic:** Two independent sources of evidence (price structure + institutional volume) converging at the same level = higher probability of reaction.

### 6.5 Named Setups in the Public Record

| Setup Name | Description |
|-----------|-------------|
| "First Vector" | Quick scalp — buy/sell the first vector candle break of EMA cloud |
| "EMA Cloud Retrace" | Primary: Vector through EMA → retrace → hold → entry |
| "Brinks Box Play" | Pre-London compression break with vector confirmation |
| "Stopping Volume Candle" | Reversal warning — not standalone entry, pre-alert |
| W Formation / M Formation | BTMM multi-push reversal patterns; structural template |
| "Vector Candle Zones" retest | Entry at unrecovered high-volume areas |
| "Spike to the High/Low" | Vector candle spikes into prior high/low; entry in opposing direction after fail |

---

## SECTION 7: ENTRY TRIGGER PRICE PATTERNS

### 7.1 Timeframe Usage

| Timeframe | Purpose |
|-----------|---------|
| **Monthly/Weekly** | Macro bias determination (EMA stack) |
| **Daily/4H** | Pattern identification, cycle positioning |
| **1H** | **Primary execution timeframe** — "the most accurate timeframe"; M and W patterns, overall structure |
| **15M** | Entry and exit execution; ID 50 setup; "better sight from close by" |
| **5M/1M** | Quick scalp entries; First Vector strategy |

### 7.2 M and W Patterns (BTMM — Confirmed Core Patterns)

**W Formation (Bullish Reversal):**
- **Leg 1:** Price closes outside the 13 EMA above (for W = closes below 13 EMA on bearish), then closes back inside the 13 EMA, creating an angle
- **Leg 2:** Price moves out of the 13 EMA again in the same direction, then closes back inside/through → at this close, one of three entry trigger candles must appear: **RR (Railroad Tracks), Morning Star, or COW candle**
- **TDI Confirmation:** RSI must be above/below the Moving Band Line (MBL) and crossing the signal line at time of entry

**Advanced W/M Rule (Consolidation Variant):**
- Leg 1 does NOT need to close beyond the 13 EMA
- Instead, price **consolidates in a range of 8 or more candles** below/above the 13 EMA
- The consolidation range = accumulation/distribution zone
- RSI starts outside the band on Leg 1; returns and crosses signal line on Leg 2

**London Pattern Types:**
| Type | Description |
|------|-------------|
| Type 1 | M or W forms ABOVE or BELOW the Asian range high/low |
| Type 2 | M or W forms WITHIN the Asian range |
| Type 3 (50/50/50) | Price bounces off 50 EMA; RSI above/below MBL and 50 static line, crossing signal line; pattern at 50% of Asian range |

### 7.3 Railroad Tracks (RR) — Exact Rules

**Definition:** Two consecutive candles of approximately equal size and opposing direction, with very little wicking — resembling two rails.

**Rules:**
- The second candle must close in the **opposite direction** of the first candle
- Both candles must have **comparable body sizes** (within ~10% of each other)
- **Small wicks** — if large wicks are present, it degrades quality
- Appears at the end of the **second leg** of an M or W pattern

**Relationship to M/W:** RR tracks are "an anomaly of an M or W pattern" — a compressed, faster version where the full M or W completes in just two candles. Standard M/W = 30–90 minutes; RR = two consecutive candles.

**Usage:** Also appears at **ID 50 bounce** (50 EMA touch on 15M chart).

### 7.4 The Half Batman Pattern — Exact Rules

**Full Batman:** Strong trend → retracement/spike into S/R → consolidation → second push rejected = Batman logo shape

**Half Batman** (Tino's version — only ONE wing has formed):

**Type 1 (Outside Structure):**
1. Price makes a strong move and closes **beyond** the 13 EMA (outside main structure)
2. Price returns to challenge the first leg's extreme level
3. **Critical rule: Price fails to reach the original leg by 10 pips** (it CANNOT revisit that level fully — this is the first indication MM doesn't want price going further)
4. A **"shift candle"** of 10–12 pips fires — this candle must close **beyond the apex** (midpoint structure between the two legs)
5. TDI confirmation: RSI cross of signal line
6. Stop: Above/below where the shift candle closed beyond the 13 EMA

**Type 2 (50 EMA Trap):**
1. Price closes beyond the 13 EMA
2. Price then **traps off the 50 EMA** — finds support/resistance there
3. Price will **NOT retrace back through the 13 EMA** — the 50 acts as a ceiling/floor
4. Same shift candle + TDI confirmation requirements

**Why it's called "half":** The MM avoids giving trapped traders a profitable exit from the first leg, so it moves price away immediately instead of making a second move back.

**Invalidation rule:** If price returns to and fully retests the original leg (comes within 10 pips of it) → Half Batman is invalidated → may become full M or W.

### 7.5 The COW Candle

One of three main entry trigger candles (alongside RR and Morning/Evening Star) used at the second leg of M/W patterns.

**Confirmed function:** Signals two things — Railroad Tracks back-to-back, or M or W by itself. It is a high-confidence reversal signal at the second leg confirming the market maker's hand. Precise acronym not publicly defined.

### 7.6 Spike Candle Entry Rules

**Definition:** Large, fast-moving candle that pushes quickly into a zone (HOD/LOD, psychological level).

**"Spike to the High/Low Vector Candle" setup:**
1. Green or Red vector candle (high volume) spikes into a prior high or low
2. Signal: MM is running stops at that level
3. Entry is **NOT in the direction of the spike**
4. Entry: **opposite direction** after the spike fails
5. Confirmation: stopping volume candle or reversal candle at the extreme

### 7.7 Snowflake System (EMA Break Signals)

| Snowflake Level | Condition | Signal Strength |
|----------------|-----------|----------------|
| White snowflake | 13 EMA break (most common) | Basic reversal signal |
| | 21 EMA break (requires prior 13 break) | Moderate |
| | 50 EMA break (requires prior 13 and 21 breaks) | Strong |
| **Purple snowflake** | All EMAs violated (13/21/50/200 cloud) | **Highest probability reversal signal** — price very extended, strong correction expected |

### 7.8 Displacement Candle and OTE

**Displacement candle:** High-momentum move characterized by large-bodied candles with very little wicking. Required to validate the OTE setup.

**OTE (Optimal Trade Entry) Fibonacci Levels:**
| Level | Description |
|-------|-------------|
| 0.618 (61.8%) | Minimum retracement for OTE zone to be valid |
| **0.705 (70.5%)** | **Sweet spot — "algorithmic re-entry" level** |
| 0.786 (78.6%) | Upper boundary of OTE zone |

**Application rule:** After a strong displacement move, Fibonacci drawn from swing low to high (bullish) or high to low (bearish). Only when price crosses below 50% AND enters 62%–79% band does OTE setup become valid. Entry within the zone at 70.5%.

### 7.9 False Break Avoidance Rules (Complete List)

1. **Fast move = false move:** Any dramatic spike is treated as a potential trap — do not enter in the spike direction
2. **Closed candle only:** Never enter on a candle that hasn't closed — probe that closes back inside = false break
3. **Confirmation candle requirement:** After trigger candle, a confirmation candle closing in trade direction is required
4. **Second leg requirement:** Never enter on first leg or first retrace — wait for second leg with trigger candle
5. **10-pip rule (Half Batman):** If price returns to within 10 pips of original leg = Half Batman invalidated
6. **EMA cloud hold rule:** EMA cloud retrace must hold — if it closes back through the cloud = setup invalidated
7. **TDI divergence filter:** RSI must be crossing signal line at the correct side — if not, entry is invalid

---

## SECTION 8: PSYCHOLOGY AND MINDSET FRAMEWORK

### 8.1 Core Philosophy

Three foundational beliefs:
1. **Zero-sum game acceptance:** Someone must lose for someone to win. Full acceptance required before anything else.
2. **"It's me against myself":** The primary battle is never the market — it is the trader's own mind.
3. **Mind management > technical edge:** A perfect methodology still fails if psychology is not addressed.

> "If there is no enemy within, the enemy outside can do you no harm." — African proverb (Tino's guiding mantra)

### 8.2 Core Trading Mantras (Complete List)

| Mantra | Context |
|--------|---------|
| "Trade Carefree My Friends" | Ultimate psychological end-state |
| "It's Me Against Myself" | Internal battle is primary |
| "Some Will, Some Won't, So What — Next Trade" | Anti-FOMO, anti-revenge, detachment |
| "Losses are Gold" | Reframe losses as learning currency |
| "The Money Will Come" | Process focus over profit obsession |
| "Always, Always, Always, pay yourself" | Longevity — take profits |
| "It's OK to be wrong" | Core acceptance principle |
| "Trade light, monitor losses" | Drawdown survival |
| "Market Is Always Right" | Ego-removal mantra |
| "NEVER FORCE A TRADE" | Core discipline rule |
| "Trading must be boring for you" | Detachment indicator |
| "Never be excited to trade" | Excitement = red flag |
| "It's all down to the Law of Large Numbers" | Probability framework |
| "Unless You Accept Uncertainty, You Will Forever Have Expectations That Will Lead You To Losses" | Foundational acceptance |

### 8.3 The 64 Trading Wisdom Rules (Key Rules)

**On Losses:**
- "Losses are Gold to every trader" — they reveal what needs improving
- "Learn from losses to save money; study wins to make money"
- "Keep losses small; they're indefinite in this game"
- "Admitting that you lose is the first step to transitioning as to why you lose"

**On FOMO:**
- "FOMO guarantees losses; cash is a valid position"
- Do not chase trades you missed — this is a direct FOMO rule

**On Emotions:**
- "Observe Your Enemies (Emotions) — They Highlight Your Faults"
- "Never be excited to trade" — excitement = setting up for ego loss
- "Irrational thinking becomes your adversary; fix thinking to see trading clearly"

**On Discipline:**
- "Safe trading is habitual discipline protecting your capital"
- "Make systematic, objective decisions undeterred by mental conflicts"
- "You will only improve if you allow yourself to close losing and winning positions when your rules tell you to"

**On Detachment:**
- "Once you detach from the money, you then become a trader"
- "Practice detachment from caring about results until it becomes subconscious execution"
- "Don't fool yourself into thinking the current trade is the final one"

### 8.4 Pre-Session Mental Preparation Rules

1. **Emotional gate check:** Only enter a session when feeling mentally "good" — if not, don't trade
2. **Distraction elimination:** Remove all environmental noise before the session
3. **Active hours only:** Trade during peak market activity windows (London/NY)
4. **Meditation (15–20 minutes):** Daily breathing meditation before trading — "#1 factor in transformation"
5. **Thought journal review:** Identify recurring emotional patterns before session begins
6. **Written commitment declaration:** Signed commitment to rules, kept physically at the trading desk

### 8.5 Thought Journal — Tino's Primary Psychology Tool

Focus areas for the journal (NOT trade results — emotional states):
- Emotional states during trades
- Recurring negative self-talk
- Physical tension responses when positions move against
- Behavioral triggers leading to early exits or over-holding
- Identification of recurring destructive patterns

### 8.6 Discipline Protocol

1. **Habit formation over willpower:** Build discipline by forming habits, not trying harder
2. **System removes discretion:** Rules-based system eliminates emotional discretion
3. **2-week abstinence protocol:** Complete withdrawal from all trading, news, and market content — resets psychological baseline
4. **Module pacing:** Enforced 2-day delays between course sections — intentionally builds patience as trained habit

### 8.7 Books Tino Recommends

1. Mark Douglas — *Trading in the Zone*
2. Yvan Byeajee — *Paradigm Shift*
3. Yvan Byeajee — *The Essence of Trading Psychology in One Skill*
4. The film **21** — sample size and probability thinking (card counting analogy)

---

## SECTION 9: CRYPTO PAIR SELECTION AND ADAPTATION

### 9.1 Instruments Traded

| Instrument | Tier | Evidence |
|-----------|------|---------|
| **BTC/USDT (Bitcoin)** | Primary | Overwhelmingly dominant in all public content |
| **ETH/USDT (Ethereum)** | Secondary | Joint "Bitcoin Live: Ethereum Live" sessions |
| **SOL (Solana)** | Occasional | Added to watchlist Oct 2025 deep-dive content |
| **Forex pairs** | Original system | System was forex-first; extended to crypto |
| **Indices (NAS100, S&P)** | Also traded | Course demos include indices |
| Altcoins | Not publicly taught | Course covers only Forex, indices, and Bitcoin |

### 9.2 Timeframes for Crypto

| Timeframe | Use |
|-----------|-----|
| **5-minute** | Primary crypto scalping (dedicated "5 Minute Bitcoin Strategy" video) |
| **1-hour** | Structure and cycle positioning; primary execution TF for swing entries |
| **Daily** | Range context, higher-bias |
| Any TF | "The system works on any timeframe" per course description |

### 9.3 Session Structure Applied to 24/7 Crypto

**Forex session logic applied directly to Bitcoin via session boxes:**

| Session | Box | Priority |
|---------|-----|---------|
| Frankfurt/London Brinks | 07:00–09:00 UTC | First major daily trigger; highest probability reversal |
| New York Brinks + first hour after | 13:00–15:00 UTC | Highest volume; most reversals occur here |
| Asian range | 00:00–07:00 UTC | Used as reference range for false move; consolidation |
| Weekend | ALL | **Explicitly avoided** — "every weekday" qualifier on Brinks Box money trade |

**Confirmed:** Tino explicitly advises avoiding weekend trading for crypto.

### 9.4 Macro Filters for Crypto

| Filter | Confirmed | Rule |
|--------|-----------|------|
| **DXY (Dollar Index)** | YES (public post) | Dollar weakens = BTC bid; dollar strengthens = BTC pressure |
| BTC Dominance (BTC.D) | NOT confirmed | Not in any public content; may be inside Platinum |
| SMT Divergence (BTC/ETH) | **NOT confirmed** | No Traders Reality content uses this ICT term |
| Fear and Greed Index | Not confirmed publicly | |

### 9.5 Day Selection Process

1. **Vector Candle formation:** Green/blue vector printing through EMA Cloud = trade readiness
2. **EMA Cloud posture:** Clear EMA stack relationship established
3. **Brinks Box setup forming:** Pre-session consolidation visible
4. **Session timing:** Frankfurt, London, or NY open window
5. **DXY context:** Dollar direction confirming BTC bias
6. **Psychological price ranges (Psy Ranges):** Used to set trade targets
7. **"False move" detection:** Watch for the MM-generated false move out of Asian range before true move begins

---

## SECTION 10: WEEKLY AND MONTHLY BIAS FRAMEWORK

### 10.1 Top-Down Analysis Process

| Step | Timeframe | What to Check |
|------|-----------|--------------|
| 1 | **Monthly** | EMA stack (50/200/800 arrangement); monthly open; Psychological High/Low ranges; macro bias |
| 2 | **Weekly** | EMA stack; Last Week's High and Low; weekly open position; Psychological High/Low for week; EMA cloud; weekly bias |
| 3 | **Daily** | EMA arrangement; Daily Open level; 3-day cycle phase (Mon-Tue trap or Tue-Wed reversal); false move or reversal in play |
| 4 | **4H** | EMA alignment; Vector Candle Zones; M/W patterns relative to 50 EMA; L1/L2/L3 cycle positioning |
| 5 | **1H** | Primary execution — First Vector setup; 50 EMA cloud; fanned EMAs; entry (rise-retrace-confirmation) |
| 6 | **15M/5M** | Entry precision; First Vector bonus scalp |

### 10.2 EMA Crossover Hierarchy for Bias

| Crossover | Significance |
|-----------|-------------|
| 5/13 cross | Short-term reversal; pattern lock confirmation |
| 13/50 cross | Level I trend confirmation |
| **50/200 cross (Golden/Death)** | **Level II — major bias shift; take notice** |
| 50/800 cross | Level III — overall dominant long-term trend |

### 10.3 BTMM Weekly Cycle (Confirmed)

| Day of Week | Phase | Expectation |
|-------------|-------|-------------|
| **Monday** | Trap/Induce setup | False move; small targets (30–50 pips); reduce size |
| **Tuesday** | Trap deepens | Midweek reversal beginning |
| **Wednesday** | **Midweek reversal** | Highest-probability reversal pivot; real move begins |
| **Thursday–Friday** | Real directional move | Best trading days; hold positions; most profitable window |
| Weekend | No trading | Explicitly avoided |

**Two overlapping 3-day cycles within the week:**
- Cycle 1: Mon → Tue → Wed (false move + reversal)
- Cycle 2: Wed → Thu → Fri (real directional move)

**Critical note:** The weekly pattern is observed on 15M, 1H, or 4H charts — NOT the weekly chart itself.

### 10.4 Agreeing Timeframes Rule

| Timeframe Alignment | Conviction | Position Size |
|--------------------|------------|--------------|
| Monthly + Weekly + Daily + 4H all agree | Maximum conviction | Full position size |
| Monthly + Weekly agree; Daily conflicts | Moderate | Reduced size; wait for lower TF confirmation |
| Monthly + Weekly conflict | Low | Stand aside or very short-term intraday only |
| All EMAs crisscrossing on execution TF | None | No trade — wait for clarity |

### 10.5 Weekend Analysis Checklist (Inferred from System Logic)

1. Review weekly candle close relative to 50 EMA on weekly chart
2. Note where Last Week's High and Low were formed
3. Identify monthly open and where price sits relative to it
4. Project likely phase for coming week (setting up for bullish or bearish midweek cycle?)
5. Mark Psychological High/Low levels for coming week
6. Check EMA fanning or compression (convergence = potential big move imminent)
7. Identify any vector candle zones from prior week that remain unrecovered

### 10.6 ICT Weekly Profiles vs. BTMM Cycle

Tino does NOT use ICT weekly profile names in public teaching. However, the concepts overlap:

| ICT Profile Name | BTMM/Tino Equivalent |
|-----------------|---------------------|
| Classic Tuesday Low (bullish week) | BTMM midweek reversal — low forms Mon-Tue, expansion Wed-Fri |
| Wednesday Reversal | BTMM midweek reversal on Tuesday-Wednesday |
| Consolidation Reversal | L2 chop then L3 push |
| Seek and Destroy Friday | End-of-week stop hunt before direction reversal |

**Tino uses BTMM language; the patterns are the same as ICT weekly profiles under different names.**

---

## APPENDIX: MASTER CONFLUENCE CHECKLIST FOR 1H HYBRID ENTRIES

**Combine every section above into a single pre-trade checklist:**

### Timing Layer (BTMM)
- [ ] Session: Frankfurt/London (07:00–10:00 UTC) or NY (13:00–16:00 UTC)?
- [ ] Day of week: Tuesday–Friday? (Monday = avoid)
- [ ] Weekly phase: Wednesday–Friday = real move confirmed?
- [ ] Not weekends and not within 15 min of high-impact news?

### Macro Structure (Top-Down EMA)
- [ ] Monthly EMA: 50 above 200? (macro bullish bias)
- [ ] Weekly EMA: 50 above 200? (weekly bullish bias)
- [ ] Daily EMA: fanned in trade direction?
- [ ] 4H EMA: aligned with daily and weekly?
- [ ] 1H: Price above 50 EMA cloud (for longs)?
- [ ] 1H EMAs fanned (5 > 13 > 50 > 200)?

### Pattern Layer (BTMM)
- [ ] BTMM cycle phase: Are we in L1/L2/L3 push?
- [ ] Weekly structure: Does W or M pattern on 4H/1H confirm direction?
- [ ] Half Batman: Is there a half-batman setup in play?
- [ ] Brinks Box: Has a Brinks Box formed? What is the stop-hunt direction?

### Level Confluence
- [ ] Is there a key S/R level present (Pivot, Round Number, Vector Zone, ADR level)?
- [ ] Does this level align with the 50 EMA cloud?
- [ ] Is there an unrecovered Vector Candle Zone at this level?
- [ ] Optional: Does an ICT Order Block or FVG coincide with this level?

### Volume Confirmation (PVSRA)
- [ ] Has a green/blue vector candle (≥150% vol) appeared at the level?
- [ ] Is the retrace to the 50 EMA on low-volume gray candles?
- [ ] Does the retrace HOLD the EMA (no body close through it)?
- [ ] Is the confirmation candle closing above the cloud?
- [ ] No opposing red Climax vector at the entry point?

### TDI Confirmation
- [ ] Green line above red line (for longs)?
- [ ] Both lines above yellow MBL?
- [ ] Yellow MBL above 50 level (for longs)?
- [ ] Volatility bands expanding (not flat/tight)?
- [ ] No Shark Fin in wrong direction at entry?

### Macro Score (Vol 7)
- [ ] S&P direction: uptrend? (additive)
- [ ] DXY: below 100 or declining? (additive)
- [ ] VIX: below 25? (normal) or below 15? (favorable)
- [ ] No FOMC/CPI/NFP within 24h?
- [ ] Macro score: ≥ +2 for standard entry; ≥ +4 for full size?

**Count of checks passed → higher count = higher conviction → adjust leverage accordingly.**

---

*Volume 8 complete. Volume 9 will cover externally verified additional confluences (Volume Profile, VWAP, Liquidation Heatmaps, CVD, Options Data, Open Interest, On-Chain Metrics, Time-of-Day Statistics, Fear & Greed Index, Divergences) — research agents currently running.*
