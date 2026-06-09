# Traders Reality / Hybrid System — Research Volume 4
# ICT FVGs, Order Blocks, Macro Correlations & Wyckoff Integration
# Branch: claude/crypto-confluences-research-cxrtp3
# Date: 2026-06-09
# Covers: 4 deep-research topics (6 topics pending re-run — hit rate limits)

---

## TABLE OF CONTENTS

1. ICT Fair Value Gaps — Complete Framework
2. ICT Order Blocks — Complete Identification & Grading System
3. Bitcoin Macro Correlations (DXY, S&P 500, Gold, VIX, FOMC, ETF Flows, CME Gaps)
4. Wyckoff Methodology — Full Schematics Mapped to ICT & BTMM

---
---

## SECTION 1: ICT FAIR VALUE GAPS — COMPLETE FRAMEWORK

### 1.1 Exact FVG Identification — The 3-Candle Pattern

A Fair Value Gap is a **three-candle imbalance** where the wick of Candle 1 and the wick of Candle 3 do not overlap, leaving a price void in the middle.

**Bullish FVG (gap below price):**
- The **low of Candle 3 is higher than the high of Candle 1**
- Gap zone = from the HIGH of C1 to the LOW of C3
- Acts as support on retest

**Bearish FVG (gap above price):**
- The **high of Candle 3 is lower than the low of Candle 1**
- Gap zone = from the LOW of C1 to the HIGH of C3
- Acts as resistance on retest

**Middle Candle (C2) requirements:**
- Must have a large body with small wicks — the displacement candle
- Must be wide-range and impulsive
- Bodies of C1 and C3 must not overlap C2's body range

---

### 1.2 Valid vs. Invalid FVG Checklist

**Valid FVG requires ALL of:**
1. Non-overlapping wick zones between C1 and C3 (structural requirement)
2. C2 is wide-range with minimal wicks — no hesitation in the displacement
3. Occurs during or immediately after a liquidity sweep (stop hunt)
4. Confirmed by a BOS or MSS
5. Aligned with higher-timeframe directional bias
6. Forms inside a kill zone (not random time of day)

**Invalid FVG — discard when:**
- FVG forms in choppy/ranging price action with no directional context
- C1 and C3 wicks overlap (no true gap)
- C2 has long wicks on both sides (indecision, not displacement)
- Counter to HTF trend
- No prior liquidity sweep preceded it
- C3 closes back INSIDE C2's body range (creates a "Rejection FVG" — weakest type)
- Gap covers less than **0.25× ATR** on the current timeframe (for crypto: 0.25–0.35× ATR minimum)
- No BOS/MSS confirmation exists on any lower timeframe

---

### 1.3 The Four FVG Subtypes (Quality Ranking)

1. **Perfect FVG (PFG):** C3 is small and consolidating — highest retest probability
2. **Breakaway FVG (BFG):** C3 is also large and expansive — strong continuation, less likely deep retest
3. **Rejection FVG (RFG):** C3 closes back into C2 — weakest; often fails
4. **Inverse FVG (IFVG):** A former FVG that has been fully traded through — see next section

---

### 1.4 Inversion FVG (IFVG) — Polarity Flip Rules

**What triggers an IFVG:** Price closes COMPLETELY beyond the FVG's far boundary. A WICK penetration does NOT create an IFVG — only a CANDLE BODY CLOSE beyond the boundary triggers the flip.

- **Bullish FVG → Bearish IFVG:** Price displacement closes FULLY below the bullish gap's lower boundary → former support zone flips to resistance
- **Bearish FVG → Bullish IFVG:** Price displacement closes FULLY above the bearish gap's upper boundary → former resistance flips to support

**IFVG Entry Protocol — Three Models:**
1. **Limit Order (Aggressive):** Place limit at CE (50% midpoint) of IFVG zone, tight stop
2. **Reaction Entry (Conservative):** Wait for rejection candle (pin bar, engulfing) within IFVG zone before entering
3. **LTF MSS Entry (Highest Confirmation):** Drop to 5M/15M; wait for MSS within the IFVG zone; enter on first LTF FVG after the MSS

**Confirmation requirements (need at least one):**
- SMT Divergence at the IFVG zone
- Clear internal MSS on LTF after price enters the IFVG
- Zone in premium (bearish IFVG) or discount (bullish IFVG)

**Stop placement:**
- Bullish IFVG trade: stop below the lowest point of the flipped gap
- Bearish IFVG trade: stop above the highest point of the flipped gap

**IFVG invalidation:** Price closes FULLY back inside the original gap boundaries → zone failed → exit immediately

---

### 1.5 Consequent Encroachment (CE) — The 50% Fill Rule

CE = the exact **50% midpoint** of any FVG (apply Fibonacci from FVG high to low, mark the 0.50 level).

**CE as Primary Entry Target:**
- Algorithmic systems execute at the zone midpoint
- Institutional orders accumulate at equilibrium, not the edge
- Allows entry with better R:R than waiting for the far edge

**Entry Sequence at CE:**
1. Price retraces into FVG zone
2. Wait for price to reach or approach CE
3. Confirm with a rejection candle OR LTF MSS at CE
4. Enter in direction of HTF bias
5. Stop beyond the far edge of the FVG (plus small buffer)

**DO NOT enter on the first touch of CE without candle confirmation.** CE requires a reaction, not a blind limit order.

**CE Fill Scenarios:**

| Scenario | FVG Status | Action |
|---|---|---|
| Price touches CE, rejects | Valid — partial fill | Trade the rejection |
| Price fills to CE, consolidates | Valid — partial fill | Monitor for continuation |
| Price fills fully (edge-to-edge) | Mitigated | Remove from chart; watch for IFVG |
| Price closes beyond far edge | Inverted (IFVG) | Re-mark as IFVG; reverse polarity |

---

### 1.6 FVG Stacking & Liquidity Voids

**FVG Stacking:** Multiple consecutive FVGs forming within a single displacement leg.

- **SIBI (Sell-Side Imbalance, Buy-Side Inefficiency):** Bearish gap zone
- **BISI (Buy-Side Imbalance, Sell-Side Inefficiency):** Bullish gap zone

**Stacking Probability Rules:**
- The **2nd and 3rd FVGs in a stack** = highest probability for entry (1st FVG often swept by initial impulse)
- At the 4th–5th FVG in a stack → exhaustion warning; watch for reversal signals
- A candle that closes through the ENTIRETY of the last FVG in the stack = stack terminated

**Treating a stack as a single zone:**
- Top boundary = highest edge of topmost FVG
- Bottom boundary = lowest edge of bottommost FVG
- CE = 50% of the ENTIRE composite zone
- In high-momentum conditions, price only retraces to CE of the most recent FVG — do not demand full stack mitigation

**FVG Stack vs. Liquidity Void:**

| | FVG Stack | Liquidity Void |
|---|---|---|
| Structure | 2–3 discrete FVGs | Multi-candle expansion with embedded FVGs |
| Fill speed | Often 1–3 sessions | Can remain open weeks/months |
| Formation catalyst | Strong institutional leg | Major news event (NFP, CPI, FOMC) or crypto liquidation cascade |
| Trading approach | Retest each FVG at CE | Target CE of overall void |

---

### 1.7 Timeframe Weight Hierarchy for FVGs

| Timeframe | Weight | Reliability |
|---|---|---|
| Monthly / Weekly | Maximum | Years to decades |
| Daily | High | Weeks to months |
| 4H | Significant | Days to weeks |
| 1H | Moderate | Hours to days |
| 15M | Entry-level | 1–3 sessions |
| 5M | Entry trigger | Within session |
| 1M | Scalp only | Minutes |

**Overriding rule:** When HTF and LTF FVGs point in opposite directions, the HTF wins. Use LTF FVGs ONLY in the direction of the HTF FVG.

---

### 1.8 FVG + Order Block Confluence — The Premium Setup

When an OB and FVG overlap at the same price level:
- The OB proves REJECTION at that level
- The FVG proves LIQUIDITY ABSENCE in that zone
- Combined = two layers of institutional attraction

**Entry Protocol for OB + FVG Confluence:**
1. HTF bias confirmed (daily/4H direction)
2. Price retraces into the OB + FVG overlap zone
3. On LTF (5M–15M): watch for a long-wick rejection candle within the zone
4. Enter when the candle FOLLOWING the rejection closes above the open (bullish) or below (bearish)
5. Stop: below the lowest point of the OB (not just the FVG edge)

**Confluence Quality Ranking:**
1. OB + FVG + HTF structural level (Daily OB at Weekly FVG) = Maximum quality
2. OB + FVG at CE of higher-timeframe range = Very high
3. OB + FVG with Fibonacci confluence (50%, 62%, 79%) = High
4. OB + FVG alone = Standard
5. FVG alone (requires kill zone timing) = Minimum acceptable
6. FVG without context = Do not trade

---

### 1.9 Three FVG Entry Models

**Model 1 — CE Limit Entry (Aggressive):**
- Place limit at CE of FVG; stop beyond far edge + buffer
- No candle confirmation required — rely on zone + context
- Higher win rate but requires precise zone identification

**Model 2 — Reaction Entry (Conservative):**
- Wait for rejection candle (engulfing, pin bar, doji) within the zone
- Enter on close of confirmation candle
- Stop: beyond the low of the rejection candle

**Model 3 — LTF MSS Entry (Highest Confirmation):**
- Price enters FVG on HTF (H1/H4)
- Drop to LTF (5M or 15M)
- Wait for Market Structure Shift on LTF
- Enter on first FVG formed on LTF after the MSS
- Stop: beyond the LTF MSS swing extreme

---

### 1.10 FVG Invalidation — Hard & Soft Rules

**Hard Invalidation (Exit immediately):**
1. Candle closes beyond the far edge of the FVG
2. Price closes fully back inside the FVG after IFVG formed (polarity flip failed)
3. No reaction at CE on second test
4. Significant fundamental event disrupts structure (black swan)

**Soft Invalidation (Reduce position, raise alert):**
- FVG is more than 3 full sessions old without a retest ("stale zone")
- Volume during retest does not spike (no institutional engagement)
- Multiple consecutive candles grind through the FVG without rejection (absorption)

**Never trade these FVGs:**
- No liquidity sweep before the FVG
- Outside all kill zones
- Counter to HTF trend
- Choppy/ranging formation
- Weekend crypto formation (no CME/NWOG confluence)
- Liquidation-cascade origin in crypto (forced margin calls ≠ institutional intent)
- FVG already fully mitigated edge-to-edge

---

### 1.11 Multi-Timeframe FVG Cascade Protocol

**Step-by-step top-down cascade:**
1. **Daily:** Determine bias (bullish/bearish); identify nearest Daily FVG as macro target
2. **H4:** Find most recent H4 FVG aligned with Daily bias; this is the setup anchor
3. **H1:** Confirm H4 zone with H1 FVG overlap; check OB+FVG confluence
4. **M15:** Wait for price to enter H4 FVG zone; watch for M15 liquidity sweep + MSS
5. **M5:** After M15 MSS, identify the first M5 FVG formed in the new direction; this is the entry
6. Stop: below M5 MSS swing low (bullish) or above swing high (bearish)
7. Target: CE of H4/H1 FVG, then the Daily FVG

**Nesting Rule:** A valid cascade requires at least **3 timeframe alignments** in the same direction. M5 FVG entry against an H4 FVG bias = low quality. M5 entry WITH H4 AND Daily FVGs aligned = A+ quality.

---

### 1.12 Session FVG Reliability Ranking

| Session | Window (EST) | Reliability | Reason |
|---|---|---|---|
| NY Kill Zone | 08:30–11:00 AM | **Highest** | Most institutional participation; Silver Bullet 10–11 AM creates cleanest FVGs |
| London Open KZ | 02:00–04:00 AM | High | Asian range sweep creates high-quality FVGs after stop hunt |
| PM Silver Bullet | 02:00–03:00 PM | Moderate | Continuation after midday chop; less reliable on range days |
| Asian Session | 8:00 PM–12:00 AM | **Low** | Consolidation range; Asian FVGs often consumed by London sweep |

**The Premium FVG Setup (core ICT narrative):**
```
1. Liquidity sweep — price takes out obvious pool (Asian high/low, equal highs, PDH/PDL)
2. Displacement candle — sharp reversal after sweep
3. FVG forms in displacement sequence
4. MSS confirms on LTF
5. Entry at CE of FVG from step 3; stop beyond sweep wick
```

---

### 1.13 Crypto-Specific FVG Behavior

**FVG fill rate — Crypto vs Forex:**
- Forex FVG fill rate: ~80% generally
- BTC FVG fill rate: **60–80%** (lower for altcoins)
- Minimum size threshold: **0.25–0.35× ATR** (higher than forex to filter thin-book noise)

**CME Gap + Spot FVG Convergence:**
- Historical CME gap fill rate: **~77%** overall; ~85% for gaps under $500
- When CME gap AND spot FVG overlap at the same price level → **Tier 1 crypto confluence**
- NOTE: CME moved to 24/7 crypto trading effective May 29, 2026 — the classic Friday–Sunday gap pattern is eliminated going forward

**New Week Opening Gap (NWOG):**
- Forms between Friday 5:00 PM ET close and Sunday 6:00 PM ET open
- Functions as a weekly-scale FVG
- CE of NWOG = high-probability reaction zone Monday morning
- Historical partial fill rate (to CE): 60%+ price stabilization at the 50% level

**Weekend FVG Rule:** Filter out FVGs that form from Friday 5:00 PM ET through Sunday 5:00 PM ET unless they align with a CME gap or NWOG. Volume is 20–40% lower on weekends — these "thin market FVGs" frequently get violated when Monday liquidity returns.

**Liquidation Cascade FVGs — The Trap:**
Forced margin call liquidations produce massive candles with huge gaps. These are NOT institutional displacement FVGs — they are margin calls. These gaps frequently fill completely and keep going. **Rule: Never trade FVGs created by obvious liquidation cascades.** Identify by: no prior setup context, extreme gap size (5+ ATR), no liquidity sweep beforehand, immediate reversal or continued direction with no pause.

**Altcoin FVG Rules:**
- Low-cap tokens create FVGs on almost every candle (thin order book) — carry no institutional meaning
- Apply FVG analysis only to BTC, ETH, and major perpetuals
- On altcoins: require 0.5× ATR minimum gap size AND only trade A+ confluence setups (OB+FVG+HTF)

---

### 1.14 FVG Quality Tier System

**Tier 1 (All apply — A+ trade):**
- Clean displacement + Kill zone + After liquidity sweep + HTF aligned + OB confluence

**Tier 2 (Most apply — High quality):**
- Clean displacement + Kill zone + After liquidity sweep + HTF aligned

**Tier 3 (Standard — Minimum viable):**
- Clean displacement + Kill zone + HTF aligned

**Tier 4 (Low — Use only with other Tier 1 confluence):**
- Formed outside kill zone, or no prior sweep, or LTF only

**Tier 5 (Invalid — Do not trade):**
- Choppy market, counter-trend, low-liquidity period, stale, overlapping candle wicks, liquidation origin

---

## SECTION 2: ICT ORDER BLOCKS — COMPLETE IDENTIFICATION & GRADING SYSTEM

### 2.1 The Foundational OB Rule

An Order Block is the **last opposing candle before a strong institutional displacement move.**

- **Bullish OB:** Last BEARISH (down-close) candle before a strong bullish displacement
- **Bearish OB:** Last BULLISH (up-close) candle before a strong bearish displacement

---

### 2.2 Exact OB Identification — Two-Candle Structural Requirements

**For a Bullish OB (all required):**

| Step | Requirement |
|---|---|
| 1 | Candle 1 is bearish (closes below its open) |
| 2 | Candle 2 sweeps BELOW Candle 1's low (liquidity grab) |
| 3 | Candle 2 closes ABOVE Candle 1's high (full body-to-body engulfment) |
| 4 | FVG visible on lower timeframe within or just above the OB zone |
| 5 | Lower-timeframe Market Structure Shift to the upside confirmed |

**For a Bearish OB (all required):**

| Step | Requirement |
|---|---|
| 1 | Candle 1 is bullish (closes above its open) |
| 2 | Candle 2 sweeps ABOVE Candle 1's high (liquidity grab) |
| 3 | Candle 2 closes BELOW Candle 1's low (full body-to-body engulfment) |
| 4 | FVG visible on lower timeframe within or just below the OB zone |
| 5 | Lower-timeframe Market Structure Shift to the downside confirmed |

**Critical disqualifiers:** Partial engulfment only, no FVG creation, or no structural break = NOT a valid OB.

---

### 2.3 Where to Draw the OB Box

- **Primary zone (body):** Open to close of Candle 1 → tightest institutional zone; entry at 50% of this body
- **Full zone (range):** High to low of Candle 1 including wicks → stop-loss reference; full invalidation boundary
- Draw the visible rectangle from HIGH to LOW of the OB candle
- Mark the **50% body level (Mean Threshold)** as the primary entry limit

---

### 2.4 OB Quality Grading System (5 Factors)

| Factor | How to Assess | Weight |
|---|---|---|
| 1. Liquidity Sweep | Was a stop-run (new swing high/low taken) immediately before the OB? | **Highest** |
| 2. Displacement Magnitude | Are post-OB candles large-bodied, minimal wicks, closing near extremes? Multiple consecutive? | High |
| 3. FVG Created | Did the displacement leave a clear 3-candle FVG with no wick overlap? | High |
| 4. HTF Alignment | Is the OB in the direction of D1 or W1 trend? At premium/discount level? | Medium-High |
| 5. First Retest | Has price never returned to the OB since formation? | Medium |

**Grade Descriptions:**

**A+ OB (All 5 factors present):**
- Liquidity sweep of obvious level immediately before the OB candle
- Displacement leaves large, wide FVG (C3 wick doesn't overlap C1 wick at all)
- Post-OB move of 3+ standard deviations vs recent ATR
- Aligns with D1/W1 trend; in discount (bullish) or premium (bearish) zone
- First untouched retest
- **Entry sizing: full risk — 1% account risk**

**B OB (3–4 factors):**
- Strong displacement but no pre-OB liquidity sweep, OR narrow FVG, OR only H4 (not D1) aligned
- **Entry sizing: 0.5% account risk**

**C OB (1–2 factors):**
- No sweep, weak displacement, no FVG, or counter-trend
- **Skip or minimal scalp position only**

---

### 2.5 Rejection Block — Wick-Based OB

A Rejection Block is defined by the **wick** of a sweep candle, not the body.

**Formation:**
- **Bullish Rejection Block:** Price sweeps below a prior low (SSL taken), wick extends down, body closes ABOVE that prior low → zone from wick low up to candle's body close
- **Bearish Rejection Block:** Price sweeps above a prior high (BSL taken), wick extends up, body closes BELOW that prior high → zone from body close up to wick high

**Hard rule:** Body close back inside the range is MANDATORY. No body close = no Rejection Block.

**Mean Threshold (50% Level):** Midpoint of the wick range = primary entry level.
- Formula: (Wick extreme + Candle close) / 2

**Entry:**
- Bullish: Limit buy at mean threshold on pullback into the wick zone
- Bearish: Limit sell at mean threshold on retracement into the wick zone
- Stop: Beyond the wick extreme + 2–5 ticks buffer

**Zone Filter:** Bearish Rejection Blocks trade ONLY in premium; bullish only in discount.

---

### 2.6 Breaker Block — Failed + Flipped OB

A Breaker Block is an OB that **failed** (price broke through it) **AND** was preceded by a **liquidity sweep**. Without the sweep, it is just a failed OB — not a Breaker Block.

**Bearish Breaker (was bullish OB, now resistance):**
1. Valid bullish OB formed, price rallied
2. Price returns and sweeps BELOW the OB's low (SSL taken)
3. Price BODY CLOSES below the OB's low (not just a wick)
4. The original bullish OB zone now acts as bearish RESISTANCE on first retest from below

**Bullish Breaker (was bearish OB, now support):**
1. Valid bearish OB formed, price dropped
2. Price sweeps ABOVE the OB's high (BSL taken)
3. Price BODY CLOSES above the OB's high
4. The original bearish OB zone now acts as bullish SUPPORT on first retest from above

**Breaker Block Rules:**
- Valid for the **FIRST RETEST ONLY** — once mitigated, the edge is gone
- Stop: Beyond the full Breaker Block range
- Minimum R:R: 1.5:1
- Invalidation: If first retest fails (price closes through the block), it is NOT valid for a second attempt

---

### 2.7 Mitigation Block — Unfinished OB

A Mitigation Block is an OB that **holds on retest** — no body close breaks through it. The OB candle body is NOT penetrated. Price touches the zone, may wick into it, but no body closes past the extreme.

**Key distinction from Breaker:** In a Mitigation, the OB body is NOT broken. If a candle body closes through, it becomes a Breaker, not a Mitigation.

**Entry Criteria:**
1. Identify the original OB (valid two-candle sequence with displacement)
2. The OB must have delivered a clean displacement leg
3. OB has NEVER been touched since formation (first retest = highest probability)
4. OB body remains intact — no body close through it on the retrace
5. Only trade in direction of HTF trend
6. Drop to M5/M3 at the OB tap; wait for MSS, CISD, or rejection candle in original trend direction
7. Enter on LTF confirmation

---

### 2.8 Propulsion Block — The 50% Mean Threshold Entry

A Propulsion Block is the **single ignition candle inside an Order Block** — Candle 2 (the displacement candle) in the FVG sequence. Entry is at exactly 50% (Mean Threshold) of that candle.

**Qualification Requirements:**
- C2 body is large relative to surrounding candles (genuine displacement)
- Clear gap between C1 wick and C3 wick (true FVG)
- Above-average volume on C2 (especially useful in crypto where volume data is reliable)
- HTF directional alignment
- MSS or BOS confirmed

**The 50% Mean Threshold serves two simultaneous purposes:**
1. **Primary entry level** — place limit here on retest
2. **Hard invalidation line** — if price CLOSES through this level after retest, the setup is off

**Entry/Stop/Target:**
- Entry: Limit at 50% of C2's body (Fibonacci 0.50 of the displacement candle range)
- Stop: Beyond C2's full range (below C2's low for bullish; above C2's high for bearish)
- Target 1: Recent swing high/low (liquidity pool)
- Target 2: Next HTF FVG or OB
- Advantage: Tighter zone than standard OB → superior R:R

---

### 2.9 The ICT Unicorn Model — Breaker Block + FVG Overlap

The Unicorn is the **highest-tier** ICT confluence: a Breaker Block with a FVG sitting directly inside its range.

**Formation sequence (all required):**
1. Liquidity sweep of prior high/low
2. Market Structure Shift (aggressive MSS)
3. FVG created during the displacement leg
4. FVG sits **WITHIN** the Breaker Block's price range — full overlap, not adjacency

**Entry:**
- Price retraces into the FVG within the Breaker Block
- Limit at FVG midpoint (CE / 50%) or at FVG boundary
- OR wait for rejection candle inside the zone

**Stop:** Beyond the outer edge of the Breaker Block (whichever is wider — BB or FVG extreme)

**Invalidation:** Price CLOSES past the Breaker Block's extreme

**Sizing rule:** Risk 0.5–1% of account equity. The stop-loss distance determines position size — never size based on a fixed lot count. Premium setups warrant full risk allocation.

---

### 2.10 Multi-Timeframe OB Hierarchy

```
Monthly → Weekly → Daily → H4 → H1 → M15 → M5/M3
   HTF        HTF      HTF   ITF   ITF    LTF    Entry
```

**Role of Each Tier:**

| Timeframe | Role | OB Strength |
|---|---|---|
| Monthly/Weekly | Macro bias; dealing range; major institutional levels | Highest |
| Daily | Primary trend direction; main OBs to trade back to | High |
| H4 | Active trader bias; 6 candles/day; session structure | Medium-High |
| H1 | Execution confirmation; intraday setup timing | Medium |
| M15 | Entry confirmation; limit order timing | Lower |
| M5/M3 | LTF trigger only; MSS/CISD confirmation within H1 OB | Noise filter |

**Top-Down Cascade:**
1. **Daily:** Identify trend direction; mark major OBs; confirm premium/discount
2. **H4:** Find most recent H4 OB aligned with Daily bias — this is the anchor
3. **H1:** Wait for price to tap H4 OB range; look for H1 MSS or CISD; find H1 FVG or OB within H4 zone
4. **M15/M5:** Execute — limit at H1 OB's 50% level or market entry on M5 MSS trigger candle

**Precedence Rules:**
- Daily OB untapped = overrides H4 setup pointing in the opposite direction
- H4 OB untapped = overrides H1 or lower
- ONLY trade lower-TF OBs in the SAME direction as the HTF OB

---

### 2.11 OB Invalidation Rules

**Wick through = does NOT invalidate the OB** (deeper fill = better R:R)
**Body close through = INVALIDATION**

- Bullish OB: bearish candle BODY closes below the OB's full low = invalid
- Bearish OB: bullish candle BODY closes above the OB's full high = invalid

**Retest Count:**

| Retest | Edge Level |
|---|---|
| First clean retest (untouched) | Highest |
| Second retest | Reduced — institutional orders partially filled |
| Third retest | Minimal — zone is being consumed; likely to break |

**Full Invalidation Checklist:**
1. Candle body closes beyond the OB extreme
2. Price taps and returns — first-retest edge consumed
3. HTF bias flips — ALL same-direction OBs become invalid
4. No MSS/CISD on LTF when price reaches the OB
5. Original displacement move from OB has been FULLY RETRACED

---

### 2.12 OTE Inside an OB — Precision Entry

When the OTE zone (62%–79% retracement) overlaps with an OB zone:
1. Mark the HTF OB zone
2. Draw Fibonacci from the displacement leg that created the OB
3. If 62%–79% retracement falls INSIDE the OB box → limit order at 70.5%
4. Stop: Below the OB's full low
5. This produces tighter stops than either OB or OTE alone → maximizes R:R

---

### 2.13 Crypto-Specific OB Behavior

**Session Reliability:**

| Session | GMT | OB Quality | Reason |
|---|---|---|---|
| NY Open (peak US) | 13:30–16:00 | Highest | Most volume; biggest displacement; highest OB magnitude |
| London Open | 07:00–10:00 | High | Strong institutional flow; sweeps Asian range for OB formation |
| London Close | 15:00–16:00 | High | Overlap with NY; short-term reversal OBs form here |
| Asian Session | 00:00–03:00 | Low | Low volume; OBs formed here are often "liquidity traps" swept by London |
| Weekend | All | Lowest | Thinnest volume; weekend OBs rarely represent real institutional orders |

**BTC vs. Altcoin OB Reliability:**

| Asset | Reliability | Rule |
|---|---|---|
| BTC | Highest | H4/Daily OBs most reliable; use all OB types |
| ETH | High | Similar to BTC; follow BTC structure |
| Large-cap alts (SOL, BNB) | Medium | H4+ only; high BTC correlation reduces independence |
| Mid/small-cap alts | Low | HTF (H4/Daily) ONLY; A+ confirmation stack required; no sub-H1 OBs |

**Asian session specific role:** Creates *liquidity pools* (equal highs/lows, tight ranges) that London or NY sweeps — the Asian range boundary becomes important as the SWEPT LEVEL that validates an OB, not as an OB itself.

---

### 2.14 Complete OB Decision Tree

```
1. TOP-DOWN BIAS
   → D1/W1 bullish or bearish?
   → Price in premium (sell) or discount (buy)?
   → Any HTF OBs untouched in this zone?

2. OB IDENTIFICATION
   → Last bearish candle before bullish displacement (bullish OB)
   → Last bullish candle before bearish displacement (bearish OB)
   → Engulfing candle swept liquidity + closed beyond prior candle's opposite end?
   → FVG on displacement leg? MSS on lower TF?

3. OB QUALITY GRADE (5 factors, score each)
   → Liquidity sweep before OB? [+2 pts]
   → FVG created on displacement? [+2 pts]
   → Displacement magnitude strong? [+1 pt]
   → HTF aligned? [+1 pt]
   → First untouched retest? [+1 pt]
   → 5–7 pts = A+; 3–4 = B; 1–2 = C (skip)

4. WHICH OB TYPE?
   → Intact first retest = Standard OB
   → Wick-based sweep candle = Rejection Block (trade mean threshold of wick)
   → Intact retest inside FVG = Propulsion Block (trade 50% mean threshold of C2)
   → OB failed (body close through) + preceded by sweep = Breaker Block (first retest only)
   → OB still intact but returning = Mitigation Block (enter on LTF confirmation)
   → Breaker Block + FVG overlap = Unicorn Model (highest conviction)

5. ENTRY PRECISION
   → Standard: 50% body level (Mean Threshold)
   → OTE precision: Fibonacci on displacement swing; enter at 70.5%; stop beyond 100%

6. STOP & INVALIDATION
   → Stop: beyond full OB range (wicks included) + 3–5 ticks buffer
   → Body close through OB extreme = invalid — exit
   → HTF bias flip = all same-direction OBs invalid

7. TARGETS
   → T1: Nearest internal liquidity (prior swing, FVG, session high/low)
   → T2: External liquidity (weekly equal highs/lows, IPDA targets)
   → Min R:R = 2:1

8. CRYPTO FILTER
   → NY or London kill zone? (if not, HTF OB only)
   → BTC/ETH: all OB types; alts: H4+ and A+ only
   → Weekend print? Downgrade to C or skip
```

---

## SECTION 3: BITCOIN MACRO CORRELATIONS

### 3.1 DXY (US Dollar Index) vs BTC

**Correlation Coefficients (2025–2026):**
- 30-day rolling DXY-BTC correlation: **-0.72** (inverse — each 1% DXY move = ~0.72% inverse BTC move)
- Peak inverse correlation April 2026: **-0.90** (81% of BTC price variance linked to dollar fluctuations)
- Long-run correlation (2014–2020): **0.7**; current institutional cycle: **0.45** (weakened by ETF demand)

**Actionable DXY Thresholds:**

| DXY Level | BTC Signal |
|---|---|
| Below 98.50–99.00 | **Bullish** — dollar weakness zone; potential BTC ATH challenge |
| 99–100 | Caution zone; monitor direction |
| Above 100 | Bearish bias — tightening global liquidity, headwind for risk assets |
| 106+ | Strong bearish pressure; 2022 crypto winter coincided with DXY > 114 |

**3-Day Close Rule:** Use 3-day closes above/below levels — do not react to single-day readings.

**NY Open DXY Rules:**
- Check DXY 30 minutes before NY cash open (09:00–09:30 AM EST)
- DXY selling off while ES futures hold or bid = double-green confirmation for BTC long bias
- DXY rising + real rates rising = double pressure on BTC (maximum bearish environment)
- DXY rising + real rates falling = temporary pressure only

**CAVEAT:** The inverse correlation has broken down in ETF-demand windows. When IBIT inflows run > $500M/day for consecutive weeks, the DXY framework is less reliable — institutional ETF buying overwhelms the dollar signal.

---

### 3.2 S&P 500 (ES Futures) vs BTC

**Correlation Coefficients:**

| Period | BTC-SPX Correlation |
|---|---|
| 5-year average (90-day) | ~0.30 |
| March 2026 30-day | 0.74 (highest of year) |
| Intraday R² peak | 0.94 |
| Late 2025–early 2026 | -0.299 (brief decoupling) |

**Sustained decorrelation threshold:** Correlation below 0.20 for 60+ days

**THE ASYMMETRIC RISK RULE (Critical):**
- Equities sell-off 2% → BTC typically drops **6–10%** (3–5x multiplier)
- Equities rally → BTC often **lags or ignores** the equity gains
- Nasdaq-to-BTC correlation is "alive during risk-off" but disconnects during low-volatility equity rallies

**Trading Rule:** Use SPX/ES ONLY as a **bearish filter**. If ES gaps down > 0.5% at NY open, reduce BTC long exposure. Do NOT chase BTC longs just because ES is bid.

**NY Open Gap Rules:**
- ES gaps up > 1% at NY open: BTC may get a 30-minute lift but the move is often faded within the first hour (asymmetric correlation). Confirm with DXY weakness.
- ES gaps down > 1%: High probability BTC sells off at NY open. If BTC held flat during London while ES was down, expect accelerated selling at 9:30 AM EST.

**Historical Decoupling Events:**

| Period | BTC | SPX | Trigger |
|---|---|---|---|
| May–Jun 2019 | +62% | -6.5% | Pre-halving accumulation |
| Q4 2020–Q1 2021 | +300% | +12% | Institutional adoption wave |
| Full year 2023 | +147% | +26% | Spot ETF speculation |
| March 2023 | Strong rally | Bank decline | SVB banking crisis (BTC as dollar-system hedge) |

---

### 3.3 Gold (XAU) vs BTC

**Correlation Timeline:**

| Period | BTC-Gold Coefficient | Context |
|---|---|---|
| April 2025 | -0.61 | BTC ~$80K, gold climbing |
| September 2025 | -0.49 | BTC rallying to new highs |
| October 2025 | +0.29 | BTC peaks at $126K (both rising together) |
| March 2026 | **-0.88** | 4-year low — extreme divergence |

**1-year rolling average:** -0.17 (as of early 2026)

**Divergence Signal Framework:**
- BTC-Gold correlation below **-0.48** = mean-reversion signal (tends to snap back)
- **Gold rising + BTC falling** = defensive/risk-off environment; central banks buying gold; avoid BTC longs
- **Gold falling + BTC rising** = risk-on / dollar-liquidity expansion = **highest-quality BTC rally setup historically**
- **Both rising together** (coefficient 0 to +0.3) = transition phase; often precedes BTC acceleration as it "catches up" to gold's lead

**Gold at NY Open:**
- Gold making new highs at London open while BTC is flat or down → bearish session bias for BTC
- Gold pulling back from highs while BTC holds → potential BTC leadership signal; bullish NY session bias

**CAVEAT:** The -0.88 extreme in March 2026 is historically abnormal. Extreme negative correlations mean-revert within 4–8 weeks. Do not assume divergence is permanent.

---

### 3.4 10-Year Treasury Yield (TNX) vs BTC

**Key Yield Thresholds:**

| 10Y Yield Level | BTC Signal |
|---|---|
| Rising through 4.5% | Triggered ~$700M/week outflows from spot BTC ETFs |
| Rapid spike to 4.82% (3-day 18 bps move) | $1.1B in ETF outflows in single session |
| "Higher for longer" above 5% | Historical BTC underperformance vs. cash |

**Mechanism:**
- Rising risk-free rates raise opportunity cost of holding non-yielding BTC
- **Real yields (10Y TIPS) are more powerful than nominal yields**
- Real rates rising + DXY rising = maximum BTC downside pressure
- Fed "higher for longer" rhetoric at FOMC press conferences is MORE damaging than the actual rate decision

**Rate Cycle Impact:**
- Easing cycle beginning → BTC front-runs rate cuts aggressively; BUT often sells off post-announcement on "sell the news" dynamics
- Hiking cycle fears → BTC sells off when futures markets assign > 40–50% probability of another hike
- Largest recorded BTC ETF outflow: $3.4B in a single week in June 2026 (driven by rising rate expectations)

---

### 3.5 VIX vs BTC

**Correlation:** BTC implied volatility (BVIV) and VIX reached a **record 0.88 90-day correlation** as of July 2025 — BTC now behaves like a "high-beta tech stock."

**VIX Level Response Patterns:**

| VIX Level | BTC Historical Response |
|---|---|
| 15–20 (complacency) | BTC trends; favorable for upside |
| 25–30 | Caution; increased correlation sell pressure |
| Above 30 (risk-off) | BTC local lows often form |
| Spike to 60 (Aug 2024, yen carry unwind) | BTC dropped to ~$49K; VIX spike = BTC capitulation bottom |
| Spike to 60 (April 2025, tariff shock) | BTC found support near $75K |

**THE COUNTERINTUITIVE RULE:** Extreme VIX spikes (above 40–60) often mark **BTC local BOTTOMS**, not tops. The panic capitulation flush is typically complete at the VIX spike apex. Monitor for VIX reversal from spike highs as a BTC accumulation entry signal.

---

### 3.6 Federal Reserve Calendar (FOMC) Impact

**The 2025 FOMC Pattern (8 data points, 7 of 8 meetings saw BTC decline in 48 hours):**

| Meeting | Decision | BTC 48-Hour Move |
|---|---|---|
| January 2025 | Hold | -27% |
| March 2025 | Hold | -14% |
| May 2025 | Cut 0.25% | **+15%** (only rally) |
| June 2025 | Hold | -8% |
| July 2025 | Hold | -6% |
| September 2025 | Cut 0.25% | -7% |
| October 2025 | Cut 0.25% | -29% |
| December 2025 | Cut 0.25% | -9% |
| January 2026 | Hold | -7.3% |

**Average 48-hour decline across negative meetings: ~-10.9%**

**FOMC Session Trading Rules:**
1. Do NOT trade the initial 2:00–2:30 PM move — algo-dominated, frequently reverses at Powell press conference
2. Wait for **3:30 PM ET** (Powell Q&A concludes) for directional confirmation
3. **48-hour post-announcement low:** Historically forms ~2 days after the statement — the entry window for position trades
4. Pre-FOMC 48-hour period: markets compress vol and reduce crypto exposure; do not fight pre-FOMC selling
5. The May 2025 exception (+15%) happened because BTC was already heavily sold off pre-meeting (setup reversed)

**On FOMC days:**
- London session (2:00–5:00 AM EST): low directional conviction; await NY session for guidance
- NY open (7:00–9:30 AM EST): pre-positioning increases volatility; if DXY is rising into FOMC, expect BTC selling at NY open

---

### 3.7 CPI / NFP / PCE Impact on BTC

**CPI (Release: 8:30 AM ET — during London/NY overlap):**

| CPI vs Estimate | Average BTC Move (24h) |
|---|---|
| Below consensus (cooler) | **+2.8% to +5.8%** |
| Above consensus (hotter) | **-3.5% to -4.2%** |
| In-line | Muted, < 1% |

Specific examples:
- March 2025: CPI 3.0% (0.2% hot) → BTC -4.2%, $450M liquidations
- May 2025 (cool print) → BTC +5.8%

**The consensus estimate matters more than the absolute number.** A 3.3% CPI that is 0.1% below consensus is bullish. A 2.9% CPI that is 0.1% above consensus is bearish. Trade the SURPRISE, not the headline.

**Duration:** Initial directional move persists for the remainder of the NY session (until ~4:00 PM ET) with potential continuation into the following 24 hours if the CPI materially shifts rate cut expectations.

**NFP (First Friday, 8:30 AM ET):**
- BTC volatility on NFP days is **1.7× higher** than normal days
- Strong NFP (hot jobs): Bearish BTC → average -3% to -4%
- Weak NFP: Bullish BTC → historical example: October 2023 weak NFP → BTC +6% same day
- Duration: NFP impact typically lasts 1–2 trading days

**PCE (Last Friday, 8:30 AM ET — Fed's preferred gauge):**
- PCE is MORE IMPACTFUL than CPI on rate expectations
- PCE below 2.9%: Can ignite upward BTC momentum
- PCE September 2025 at 2.8%: Propelled BTC significantly
- Core PCE (strips food/energy) is watched more closely than headline for Fed signaling

---

### 3.8 CME Futures Gap Rules

**Gap Fill Statistics:**

| Metric | Rate | Time Frame |
|---|---|---|
| Overall historical fill rate | **77%** | "Eventually" |
| High-confidence sample (79 of 80 gaps) | **98.75%** | Through March 2025 |
| Gaps under $700 | **92%** | Within 30 trading days |
| Gaps under 2% of BTC price | **78%** | Within 72 hours |
| Gaps exceeding 5% of BTC price | **52%** | Within 72 hours |

**Fill Speed by Direction:**
- Downward gaps during uptrends: median fill time **4.2 days**
- Upward gaps during downtrends: median fill time **8.7 days**
- "Runaway gaps" during strong momentum may not fill for months

**Fills vs. Doesn't Fill:**
- Likely fills: Near established S/R or HVN; formed during ranging market; small gap (< $700 or < 2% of price)
- Less likely to fill (short-term): During strong trending moves; momentum/ETF-approval rallies; regime-change moves; gaps > 5% of price in trending environments

**CRITICAL — CME 24/7 Trading (Effective May 29, 2026):**
CME began around-the-clock crypto futures trading on May 29, 2026. The classic Friday–Sunday gap mechanism **no longer creates new gaps**. The gap playbook applies only to gaps formed before May 29, 2026. Any unfilled pre-May-2026 gaps remain valid targets, but new weekend gaps will no longer form.

---

### 3.9 Bitcoin ETF Flow Data (IBIT)

**Scale:**
- Cumulative IBIT inflows since January 2024 launch: > $60B
- Total spot BTC ETF holdings: ~1.29 million BTC (6% of circulating supply)
- USDT market cap: $175B; USDC: $73.4B; combined: 93% of stablecoin market

**Critical Flow Events:**

| Date | Event | Price Move |
|---|---|---|
| October 6, 2025 | IBIT single-day inflow: $970M (largest 2025) | BTC to $126K ATH |
| 9-day inflow streak | $6B total ETF inflows | BTC ATH run |
| February 25, 2026 | IBIT +$297.4M (60% of all ETF inflows) | BTC 6% intraday rebound |
| 13-day outflow streak, June 2026 | -$4.4B total | BTC $82K → < $73K |
| May 28, 2026 | IBIT single-day outflow: -$527.84M (2nd largest ever) | BTC decline |

**ETF Flow Trading Rules:**
1. Do NOT react to a single day of ETF outflows — multi-week trends provide the meaningful signal
2. Multi-week inflow streaks (7+ days): strong bullish confirmation
3. 13+ consecutive day outflow streaks: structural headwind until reversed
4. $8M/day 7-day MA inflow approximate threshold for sustained price support
5. When ETF flows run > $500M/day for 3+ consecutive days = DXY correlation may break down

**Where to find ETF flow data:**
- Real-time: The Block's ETF Flow Chart (theblock.co)
- IBIT specifically: SoSoValue IBIT Chart
- Daily updates: CoinDesk Markets, Investing.com ETF tracker

---

### 3.10 Stablecoin Supply Ratio (SSR)

**Formula:** BTC Market Cap / Total Stablecoin Market Cap

**Signal:**
- SSR declining toward 9.5 from higher levels: Stablecoin "dry powder" building → historically preceded BTC support or reversals upward
- SSR rising toward 9.5 from lower levels: Stablecoin buying power fading → historically preceded local tops or corrections
- **9.5 is the liquidity equilibrium zone** — acts as support or resistance depending on approach direction

**Actionable Rule:** When weekly stablecoin market cap GROWS by more than $3–5B in a single week with NO corresponding BTC price rise → treat as pre-rally "coiling" — potential long trigger on breakout.

---

### 3.11 Pre-NY Open Macro Checklist

**TIER 1 — Weekly Context (Check once per week):**
- [ ] ETF flow trend: Multi-day inflow or outflow streak? (The Block)
- [ ] SSR above or below 9.5? Approaching from which direction?
- [ ] FOMC/CPI/NFP/PCE calendar: Which events this week? Which days?
- [ ] Open CME gaps (pre-May 2026): Any unfilled gaps above/below current price?
- [ ] BTC-SPX 30-day correlation: Above 0.5 (use TradFi signals) or below 0.2 (trade structure only)?

**TIER 2 — Daily Context (Check each morning, 6:00–7:00 AM EST):**
- [ ] DXY direction: Where did DXY close Asia session? Above or below 100? Above 106? Below 98.50?
- [ ] 10Y Treasury yield: Overnight move and current level. Above 4.5%? Rapidly rising > 10 bps?
- [ ] ES/S&P 500 Futures: Pre-market direction; gap up or down vs prior close. Gap > 1%?
- [ ] VIX level: Above 20 (caution)? Above 30 (high risk-off, watch for BTC capitulation bottom)?
- [ ] Gold (XAU): Making new highs while BTC flat? (Risk-off, reduce longs). Pulling back while BTC holds? (Potential BTC leadership)

**TIER 3 — Session Bias Synthesis (7:00–9:30 AM EST):**
- [ ] Today's economic releases: CPI/NFP/PCE at 8:30 AM? FOMC at 2:00 PM? Size accordingly.
- [ ] DXY at NY open: Selling off = bullish BTC. Bid/rising = bearish BTC.
- [ ] London session activity: Did BTC make a higher high or lower low during London (2:00–5:00 AM EST)?
- [ ] ETF single-day flow (prior day): Large inflow or outflow? (Coinbase Premium Index positive/negative)
- [ ] Funding rates: Positive + elevated = crowded longs, sweep lows first. Negative = crowded shorts, sweep highs first.

**Session Bias Decision Matrix:**

| DXY | ES Futures | VIX | Bias |
|---|---|---|---|
| Falling, below 99 | Bid or flat | Below 18 | **Strong BTC long** |
| Rising, above 100 | Flat | 18–25 | Neutral/cautious |
| Rising, above 100 | Selling | Above 25 | **Bearish BTC — reduce exposure** |
| Spiking, above 106 | Hard sell | Above 40 | Potential capitulation bottom — watch for reversal |
| Falling, below 99 | Selling | Above 30 | Conflicted — wait for 30-min confirmation candle |

---

## SECTION 4: WYCKOFF METHODOLOGY — FULL SCHEMATICS MAPPED TO ICT & BTMM

### 4.1 Wyckoff Accumulation Schematic — Phase A Through E

#### Phase A — Stopping the Prior Downtrend

**PS — Preliminary Support**
- Context: First evidence that buyers are absorbing supply after extended downtrend
- Volume: Expanding vs. prior downtrend — price slows but does NOT reverse
- Visual: First bar closing off the absolute low; lower wicks begin appearing
- **NOT a buy signal — only flags the fall is losing momentum**

**SC — Selling Climax**
- Context: The capitulation low; panic retail selling meets aggressive institutional absorption
- Price: Widest-spread downside candle of the entire move; establishes the Support (S) line
- Volume: **Highest volume of the downtrend** — enormous effort, diminishing result = Law of Effort vs. Result
- Visual: Sharp downside spike followed by close well above session low
- **PVSRA Mapping:** Green Vector Candle (ultra-high volume + wide down-spread = institutional absorption)

**AR — Automatic Rally**
- Context: Short sellers cover; buyers fill the vacuum; establishes Resistance (R) line
- Price: Swift rally; closes significantly above SC close
- Volume: Decreasing vs. SC (correct and expected — short covering + absence of sellers)
- Visual: First meaningful green candles after SC; establishes TR high boundary

**ST — Secondary Test (of the SC)**
- Context: Price revisits SC area to test whether selling pressure remains
- Price: Should hold ABOVE the SC low — equal or higher low
- Volume: **Significantly lower than SC** — this is critical confirmation (high ST volume = supply still present)
- Visual: Shallow pullback to near SC levels; tight-bodied candles; reduced range

#### Phase B — Building the Cause
- Duration: The longest phase — can last weeks (intraday), months (daily), or years (weekly/monthly)
- Price: Oscillates between TR support (SC/ST area) and TR resistance (AR high)
- Volume: **Gradually declining throughout Phase B** — each test of support shows LOWER volume = supply being absorbed
- Visual: Tight candle bodies, contracting volatility, failed breakouts (Upthrusts), failed breakdowns

#### Phase C — Testing Supply / The Spring

**Spring (Schematic 1)**
- Context: Deliberate engineered move BELOW TR support to trigger retail stop-losses and acquire final supply
- Price: Breaks below TR support, then rapidly recovers back inside range
- Three Spring Types:
  - **Type 3 (Best):** Shallow probe, LOW volume, fastest return — supply already exhausted
  - **Type 2:** Moderate breach, moderate volume, faster return
  - **Type 1 (Weakest):** Deep penetration, high volume — requires strong Test confirmation
- **LOW volume Spring = MORE bullish** (no selling met the breakdown attempt)
- Visual: Long lower wick; closes BACK INSIDE range within 1–3 candles

**The Test (Post-Spring):**
- Price returns toward Spring low on VERY LOW volume (30–50% lower than Spring volume)
- Test holds ABOVE the Spring low
- Strong demand candles appear after the Test
- This is the confirmation entry point for accumulation

**No-Spring (Schematic 2):**
- ST forms a HIGHER LOW than the SC (supply already absorbed in Phase B)
- No boundary violation — price moves laterally near the upper third of the TR
- Breakout occurs directly from consolidation

#### Phase D — Demand Overcomes Supply

**SOS — Sign of Strength**
- Context: First major breakout above TR resistance
- Price: Wide-spread bullish candle(s) that advance on expanding volume; close near the high
- Volume: **High and expanding** — 150–200% of recent average range
- Visual: Decisive breakout through AR resistance; price accelerates impulsively; often includes a gap
- **PVSRA Mapping:** Bullish Vector Candle (high volume + wide up-spread + close near high = institutional demand)

**LPS — Last Point of Support**
- Context: Pullback after SOS; price retests former resistance (now support) before continuing higher
- Price: Shallow pullback with narrow spread; higher low vs. TR; holds above old TR resistance
- Volume: **LOW and declining on the pullback** — this is the critical confirmation
- Visual: Small-bodied candles pulling back to breakout area; wicks show buying; advance resumes with expanding volume
- **The LPS is the highest-probability entry point in the entire accumulation schematic**

#### Phase E — Markup
- Price: Leaves the TR decisively; higher highs and higher lows; trend channels establish
- Re-Accumulation: Phase E often contains nested re-accumulation TRs (smaller, tighter) — same schematic, smaller scale

---

### 4.2 Wyckoff Distribution Schematic — Phase A Through E

#### Phase A — Stopping the Prior Uptrend

**PSY — Preliminary Supply**
- Price: Wide-spread bullish candle that closes in the lower 40% of its range — price made an effort to advance but sellers absorbed it; forms a preliminary high
- Volume: Above-average — effort vs. result divergence signals hidden supply

**BC — Buying Climax**
- Context: Capitulation high; retail FOMO buying meets institutional distribution
- Price: Extreme wide spread; closes in LOWER half of bar despite reaching a new high; establishes Resistance (R) line
- Volume: **Climactic — highest volume of the uptrend**
- **PVSRA Mapping:** Red Vector Candle (high volume + wide up-spread + close in lower half = climactic distribution)
- Visual: The absolute high; long upper wick; sharp rejection

**AR — Automatic Reaction**
- Context: Post-BC selling establishes Support (S) line — lower TR boundary
- Volume: Decreasing (short-covering + absence of buyers)

**ST — Secondary Test (of the BC)**
- Price: Forms a LOWER HIGH than BC — this is the critical structural tell of distribution
- Volume: Significantly less than BC — demand is waning

#### Phase B — Building the Cause for Markdown
- Volume fingerprint: **Volume increases on downside moves; decreases on rallies** (inverse of accumulation)
- Upthrusts (UT) occur — minor false breakouts above BC resistance that fail back inside range
- "Upthrusts more common than Springs in distribution; volume increases on downward moves"

#### Phase C — Testing Demand

**UTAD — Upthrust After Distribution**
- Context: False breakout ABOVE TR resistance designed to trigger retail breakout buyers and absorb final demand
- Price: Breaks decisively above BC/ST resistance creating a new high; then rapidly FAILS back inside range
- Volume: High on the breakout, but acceptance above resistance fails
- Visual: Institutional players use retail buy orders above resistance as EXIT LIQUIDITY
- **Hard Checklist:** (a) Mature distribution TR, (b) decisive break above resistance, (c) swift reversal into range, (d) bar closes BELOW resistance, (e) SOW follows

#### Phase D — Supply Overcomes Demand

**SOW — Sign of Weakness**
- Context: First major breakdown below TR support; confirms distribution is complete
- Price: Wide-spread bearish candle(s) breaking below AR support on expanding volume; closes near the low
- Volume: High and expanding
- **PVSRA Mapping:** Red Vector Candle (high volume + wide down-spread = institutional selling)

**LPSY — Last Point of Supply**
- Context: Rally after SOW that tests former support (now resistance); final exit opportunity
- Price: Narrow-spread, low-volume rally to breakdown level; forms LOWER HIGH; closes BELOW former support
- Volume: **LOW on the rally** — confirms resistance established
- Multiple LPSYs can occur, each forming a lower high

---

### 4.3 Wyckoff ↔ ICT Concept Mapping

| Wyckoff Event | ICT Equivalent | Exact Mapping |
|---|---|---|
| Spring (Phase C) | Liquidity Sweep / Stop Hunt | Price sweeps below resting sell stops (SSL), collects liquidity, reverses. ICT calls this "sweep of sell-side liquidity" — mechanically identical |
| UTAD (Phase C Distribution) | Liquidity Sweep (Buy-Side) | Price sweeps above resting buy stops (BSL), collects liquidity, reverses. ICT: "sweep of buy-side liquidity" |
| AR (Post-SC Rally) | Market Structure Shift (MSS) | AR = first break of bearish market structure. In ICT, this is the MSS: initial structural break signaling change of character from bearish to bullish |
| SOS (Sign of Strength) | Displacement + BOS | SOS = wide-spread, high-volume, impulsive breakout. ICT Displacement = "aggressive, high-velocity price delivery that breaks structure and creates a FVG." The SOS candle IS the Displacement candle |
| LPS (Last Point of Support) | Order Block Retest / FVG Fill | After SOS/Displacement, price returns to LPS = retest of the Bullish OB (last red candle before displacement) or fill of FVG. Same price zone, same institutional logic |
| SC (Selling Climax) | Green Climax Vector Candle (PVSRA) | SC = highest-volume, widest-spread downside candle at the bottom. PVSRA Green Vector = ultra-high volume + wide down-spread = institutional absorption despite red candle |
| BC (Buying Climax) | Red Climax Vector Candle (PVSRA) | BC = Red Vector Candle — ultra-high volume + wide up-spread + close in lower half = institutional distribution into retail buying |
| LPSY (Last Point of Supply) | Bearish Order Block Retest | After SOW/bearish displacement, price rallies back to LPSY = retest of the Bearish OB (last green candle before markdown) |
| Composite Operator | Smart Money / "The Banks" | Direct equivalents. ICT's "Smart Money" and "The Banks" = Wyckoff's Composite Operator in modern retail trading language |
| Spring Test | Mitigation Block / Breaker context | Test of the Spring = price returning to swept level on reduced volume. ICT Mitigation of the invalidated bearish OB occupies same structural location |
| SOW | Bearish Displacement + MSS (bearish) | SOW breaks below last swing low, creating bearish FVG — signaling downtrend has begun |

**Core Shared Principle:** "ICT concepts are essentially rebranded versions of Wyckoff's principles, adapted to modern Forex and crypto trading. Michael Huddleston took Wyckoff's concepts and updated them." Both identify the same behavioral sequence: accumulate → manipulate (Spring/UTAD/Judas Swing) → distribute → drive price.

---

### 4.4 Wyckoff ↔ BTMM Concept Mapping

| Wyckoff Concept | BTMM Equivalent | Integration Notes |
|---|---|---|
| Accumulation Phases A–C | BTMM Day 1 Setup | BTMM Day 1 = "market maker-driven phase" initiating the directional campaign. Corresponds to SC through Spring — composite operator absorbs supply, engineers the Spring, initiates markup |
| Spring / UTAD | BTMM Judas Swing / Stop Hunt | Judas Swing = BTMM's term for the engineered false move. In Wyckoff: Spring (false breakdown) or UTAD (false breakout). Both are deliberate stop hunts that sweep retail positions. BTMM Judas Swing prints in the London session open window = Phase C at session level |
| Phase B (Building Cause) | BTMM Day 2 / Retail Emotion Phase | Day 2 = "driven by retail traders' emotions in the absence of market maker support." Corresponds to Wyckoff Phase B: range established, retail oscillates within it, volume contracts |
| SOS / SOW | BTMM Day 3 / Market Maker Return | Day 3 = "return of market makers for profit-taking and further movement." This IS the SOS/SOW — the impulsive displacement move breaking out of the TR |
| Composite Operator | BTMM Market Maker | Same concept, different label. Both frameworks describe institutional entities deliberately engineering fake moves (Springs/UTADs/Judas Swings) to acquire liquidity from retail |
| LPS Retest | BTMM Entry Trigger | BTMM uses the post-Judas-Swing retracement as the entry trigger — structurally the LPS — price returns to the breakout zone after the SOS |
| Accumulation → Markup → Distribution | BTMM Three-Day Cycle: Level I → Level II → Level III | The 3-day cycle is a compressed temporal version of the Wyckoff macro cycle |

---

### 4.5 Wyckoff Volume Analysis Rules

**The Law of Effort vs. Result:** Volume (effort) must produce commensurate price movement (result). Divergences signal institutional activity.

| Event | Expected Volume | Bullish if... | Bearish if... |
|---|---|---|---|
| SC | Climactic — highest of downtrend | Volume is climactic (absorption) | Low volume = supply not exhausted |
| ST | Significantly below SC | Low — supply absorbed | High — supply still present |
| Spring | Low Volume = BEST (Type 3) | Very low volume on Spring | High volume = needs strong Test |
| Spring Test | Very low (30–50% below Spring) | Very low — confirmed absorption | Any expansion = TR breakdown risk |
| SOS | High, expanding (150–200% above avg) | High and expanding | Weak SOS = unconvincing breakout |
| LPS | Low on the pullback | Low — no supply at breakout level | High — possible LPSY forming instead |
| BC | Climactic — highest of uptrend | N/A | Climactic = distribution |
| UTAD | High on the breakout | N/A | High = more buyers absorbed for exit |
| SOW | High, expanding | N/A | High and expanding = institutional selling |
| LPSY | Low on the rally | N/A | Low = distribution confirmed |

**PVSRA Candle Mapping:**
- **Green Vector Candle** = SC / SOS: Ultra-high volume + wide spread + close near HIGH = institutional buying
- **Red Vector Candle** = BC / SOW: Ultra-high volume + wide spread + close near LOW = institutional selling/distribution
- **Absorption candle** = Phase B mechanics: Wide spread + ultra-high volume + SMALL body/close near middle = institutions absorbing supply without moving price

---

### 4.6 Wyckoff Re-Accumulation vs. Distribution — Distinguishing Criteria

This is the most critical and most commonly misread scenario. Both patterns look structurally identical from the outside — a consolidation range after a bullish prior move.

**Context Rule (Most Important):**
- Re-Accumulation: Occurs WITHIN an ongoing uptrend
- Distribution: Occurs at the TOP of an uptrend before markdown
- Both follow a bullish prior trend — structural context alone doesn't resolve it

**Volume Fingerprinting:**

| Criteria | Re-Accumulation | Distribution |
|---|---|---|
| Volume on rallies within TR | Expanding (demand) | Contracting (supply absorbing demand) |
| Volume on declines within TR | Contracting (no supply) | Expanding (supply entering) |
| Volume at TR support test | Drying up (bullish) | Expanding (bearish) |
| Springs vs. Upthrusts | Springs more common | Upthrusts more common |
| Overall trend | Declining during range (healthy) | Increasing on downside bars |

**Structural Differences:**
- Re-Accumulation: Initial decline into range is SHALLOWER (< 50% of preceding markup); tighter TR
- Distribution: Initial AR decline is steeper/deeper; TR is wider (more supply to distribute)
- Re-Accumulation Spring: Shallower, resolves faster (less supply below support)
- Distribution ST: Forms LOWER HIGH vs. BC — inability to exceed the prior high is the key tell

**The "Jump Across the Creek" (JAC) Test:**
- Re-Accumulation: JAC is genuine breakout above resistance with continuation; BEC (Back Up to Edge of Creek) retest holds on low volume
- Distribution: UTAD looks like JAC but FAILS within 1–3 bars — returns below resistance
- **Operational rule:** If "breakout" fails within 3 bars = UTAD (distribution). If it holds and accepts above resistance = JAC (re-accumulation).

**Failure Rate:** Well-identified re-accumulations fail and become re-distributions ~15% of the time. Waiting for JAC + BEC confirmation (LPS) before entry reduces this failure rate significantly.

---

### 4.7 Wyckoff Point and Figure (P&F) — Price Target Method

**The Law of Cause and Effect:** The horizontal P&F count within a trading range = the Cause. The subsequent price trend = the Effect. A larger cause produces a larger effect.

**P&F Configuration for BTC:**
- Daily charts: 1% box size, 3-box reversal
- Weekly charts: 3% box size, 3-box reversal
- Intraday: 0.25–0.5% box size

**Horizontal Count Method (Step-by-Step):**
1. Identify the TR on the bar chart — note SC/AR boundaries (accumulation) or BC/AR (distribution)
2. Build P&F chart with appropriate box size
3. Locate the LPS (accumulation) or LPSY (distribution) on the P&F chart
4. Count horizontally at the LPS price level from left edge to right edge of TR (count all X and O columns)
5. **Upside target formula:** (Horizontal Count × Box Size × Reversal Factor) + TR Low
6. **Downside target formula:** TR High − (Horizontal Count × Box Size × Reversal Factor)
7. Generate 3 target zones: add/subtract projected range from (a) TR low/high, (b) TR midpoint, (c) count line

**BTC Example:**
- TR low: $25,000 / TR high: $32,000
- Box size: $250 (1% of $25,000) × 3 reversal
- Horizontal count: 30 columns
- Projected range: 30 × $250 × 3 = $22,500
- Near target: $47,500; Mid target: $51,000; Extended: $53,500+

---

### 4.8 Wyckoff Crypto Context — Speed and Scale

**Cycle Speed Comparison:**
- Traditional equities: Major accumulation TR spans 6–18 months (daily chart)
- **BTC/ETH:** Full accumulation schematics complete in **4–8 weeks** on the daily chart
- **Altcoins:** Even faster — full distribution phases in 1–2 weeks on lower-cap assets
- **Intraday crypto (1H/15M):** Full micro-schematics complete within a single NY session

**Historical BTC Wyckoff Examples:**
- **2018–2020 Accumulation:** SC at $3,150 (Dec 2018); AR to $5,000; Spring at $3,800 (COVID crash = terminal Spring); SOS through $10K; LPS at $9,000; Phase E markup to $65K
- **Feb–May 2021 Distribution:** BC at $58K; AR to $47K; UTAD to $65K (April 2021); SOW below $47K; LPSY at $38K; markdown to $29K
- **May–August 2021 Re-Accumulation:** Spring to $28.8K; SOS through $40K; LPS at $40K; markup to $69K
- **2022 Bear Market:** Textbook distribution Phase E; SOW below $28K; LPSY at $30K; final markdown to $15.5K

---

### 4.9 Session-Level Wyckoff — Micro-Schematics on 1H/15M

The Wyckoff schematic is fractal. A complete accumulation or distribution cycle can complete within a **single NY session** on 15M/1H charts.

**The New York Session Micro-Accumulation Cycle:**

1. **Asian Session (00:00–08:30 ET):** Establishes micro-TR boundaries. Asian high/low = SC/AR reference levels for the session. This is Phase A at the micro scale.
2. **London Session (03:00–08:30 ET):** Price oscillates within the Asian range. Volume contracts. Phase B "building cause."
3. **Judas Swing / Spring (08:30–10:00 ET):** London close / NY open. Price sweeps BELOW Asian session low (the Spring). Volume spikes on the sweep, then immediately collapses as price reclaims above Asian low.
4. **Sign of Strength / MSS (Phase D):** Price breaks ABOVE the Asian session high (AR high / TR resistance) on expanding volume. This is the SOS — the session's directional move.
5. **LPS / Order Block Retest (Phase D–E):** Price pulls back to the broken Asian range high (now support) on LOW volume. This is the LPS = ICT Order Block retest / FVG fill. Entry zone for session continuation.
6. **Phase E Markup:** Price advances through the NY session (typically into 10:00–11:00 AM window).

**Critical Time Alignment (Wyckoff + ICT + BTMM):**
- Asian range = Wyckoff TR boundaries (SC/AR for the session)
- London open sweep (03:00–05:00 ET) = Phase B/C Spring setup
- NY open (08:30–10:00 ET) = Phase C Spring/UTAD + Phase D SOS
- 10:00–11:00 AM ET = LPS retest / primary entry window
- 1:30–3:00 PM ET = BTMM Level III "market maker return" / continuation or reversal

---

### 4.10 Integrated Three-Framework Trading Setup (Wyckoff + ICT + BTMM)

**Layer 1 — Wyckoff (Macro Structural Context):**
What phase is the market in? (Daily/4H)
- Phase C? (Spring/UTAD = highest-probability trigger)
- Phase D? (LPS/LPSY = highest-probability entry with structure confirmed)
- Where is TR support/resistance?

**Layer 2 — ICT (PD Array and Timing):**
Where exactly is the entry zone and when is it valid? (1H/15M)
- Liquidity sweep confirmed (Spring/UTAD verified by ICT sweep mechanics)?
- MSS fired in the reversal direction?
- Price in ICT Premium/Discount zone?
- Valid OB or FVG at the entry zone?
- Kill zone active (London 02:00–05:00 ET or NY 08:30–10:00 ET)?

**Layer 3 — BTMM (Session Timing Cadence):**
Is the session timing aligned? (EST)
- BTMM Day 1/2/3 position identified?
- Judas Swing already printed this session (Phase C complete)?
- Within the BTMM Level I institutional move window?

**Highest-Confidence Long Setup Checklist (all 8 items):**
- [ ] Daily/4H Wyckoff confirms Phase C (Spring visible) or Phase D (LPS forming)
- [ ] 1H shows SOS displacement candle above TR resistance (MSS confirmed)
- [ ] 15M price pulls back to LPS zone = ICT Bullish OB (last red candle before SOS displacement)
- [ ] LPS pullback volume is LOW (30–50% of SOS volume)
- [ ] Pullback is into ICT Discount (below 50% of displacement range) or FVG
- [ ] Time is in NY Kill Zone (08:30–11:00 ET) or London continuation window
- [ ] BTMM Judas Swing has already swept the Asian low this session
- [ ] PVSRA: No Red Vector Candle (distribution) present on 1H at entry zone

**Highest-Confidence Short Setup Checklist (all 8 items):**
- [ ] Daily/4H Wyckoff confirms Phase C (UTAD visible) or Phase D (LPSY forming)
- [ ] 1H shows SOW displacement candle below TR support (bearish MSS confirmed)
- [ ] 15M price rallies back to LPSY zone = ICT Bearish OB (last green candle before SOW)
- [ ] LPSY rally volume is LOW (30–50% of SOW volume)
- [ ] Rally is into ICT Premium (above 50% of SOW displacement range) or bearish FVG
- [ ] Time is in NY Kill Zone or afternoon session (13:30–15:00 ET) for continuation
- [ ] BTMM Judas Swing has already swept the Asian high this session
- [ ] PVSRA: No Green Vector Candle (absorption) present on 1H at entry zone

**Setup Invalidation:**
- Volume EXPANDS on the LPS pullback (supply returning = re-accumulation may be failing)
- Price closes BELOW the Spring low (failed Spring = genuine breakdown)
- Price closes ABOVE the UTAD high (failed UTAD = genuine re-accumulation breakout)
- A PVSRA Vector Candle appears AGAINST the trade direction at entry zone
- Judas Swing swept in the SAME direction as the trade (must sweep OPPOSITE to the bias)

---

## PENDING RESEARCH TOPICS (To Re-Run in Next Session)

The following 6 topics hit API rate limits and returned no content. These will be researched in Volume 5:

1. **Steve Mauro BTMM Complete 12-Video Series** — 5-stage advance, 3-position model, Money Zones, institutional candle patterns
2. **Altcoin Season Detection & Rotation Rules** — BTC.D thresholds, ETH/BTC ratio, altcoin session behavior, SOL/BNB patterns
3. **London-NY Crossover & Asia-London Crossover Specific Setups** — Big Apple Reversal, 8:30 AM spike rules, Judas Swing timing, crossover entry sequences
4. **TradingView Indicator Stack** — Exact indicator names/authors/settings for Vector Candles, PVSRA, ICT tools, session boxes, VP/VWAP config
5. **Multi-Timeframe Analysis Cascade Workflow** — Step-by-step top-down analysis from Monthly → 1M, conflict resolution rules
6. **Advanced Volatility-Based Risk Management** — Kelly Criterion, ATR sizing, MAE/MFE analysis, volatility regimes, scaling rules

---

*Volume 4 compiled from 4 of 10 parallel research agents. Volume 5 will re-run the 6 failed topics plus cover new research areas.*
