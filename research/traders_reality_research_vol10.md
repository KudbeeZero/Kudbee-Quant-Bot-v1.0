# Traders Reality Quant Bot — Research Database Volume 10
## Advanced Frameworks: ICT, BTMM, Wyckoff, Harmonics, Trade Management, Position Sizing, MTFA

**Research Date:** June 2026  
**Status:** Sections 1–7 complete; Sections 8–10 pending agent completion  
**Branch:** claude/crypto-confluences-research-cxrtp3

---

## ⚠️ CRITICAL DATABASE CORRECTION — READ FIRST

**Steve Mauro (BTMM) uses EMA 13, NOT EMA 12.**

Multiple primary-source PDF documents confirm this consistently. Any prior reference in this database to "EMA 12" in the context of BTMM is incorrect. The correct BTMM EMA stack is:

- **EMA 5** — Yellow ("Mustard")
- **EMA 13** — Red ("Ketchup")  ← CORRECTED from any prior "12" reference
- **EMA 50** — Light Blue ("Water")
- **EMA 200** — White ("Mayonnaise")
- **EMA 800** — Dark Blue ("Blueberry")

The "13/50 EMA cross" referenced in Vol 8 is correctly labeled for the 13; verify all other EMA 12 references in the codebase.

---

## SECTION 1: ICT INNER CIRCLE TRADER — COMPLETE FRAMEWORK

### 1.1 PD Array Hierarchy (Draw on Liquidity Priority)

Price is always drawn toward liquidity. The institutional order of priority:

| Priority | Level Type | Notes |
|---|---|---|
| #1 | Old Highs / Old Lows (BSL/SSL) | Buy-side and sell-side liquidity; primary draw |
| #2 | Order Blocks (OB) | Last opposing candle before a displacement |
| #3 | Fair Value Gaps (FVG) | 3-candle imbalance; price seeks to fill |
| #4 | Breaker Blocks | Failed Order Blocks that flip function |
| #5 | Mitigation Blocks | OB that was partially mitigated |
| #6 | Rejection Blocks | Wick-heavy candles acting as zones |
| #7 | Volume Imbalances | Gap between candle bodies (not wicks) |

**Application rule:** Before entry, identify which PD Array level price is currently targeting as the next "draw on liquidity." Only take trades where the target is the next PD Array in the hierarchy — not against it.

### 1.2 OTE (Optimal Trade Entry) Zone

The ICT Optimal Trade Entry uses Fibonacci retracement of an identified swing:

- **Entry start:** 0.62 (62%) retracement
- **Precise sweet spot:** 0.705 (70.5%)
- **Outer limit:** 0.79 (79%)

**Extension targets from OTE entries:**
- TP1: -0.27 extension
- TP2: -0.62 extension  
- TP3: -1.0 extension (full measured move)
- TP4: -2.0 extension
- TP5: -2.5 extension

**Entry invalidation:** Candle body close beyond the 1.0 level (the original swing extreme). A wick through 1.0 is NOT invalidation — body close only.

### 1.3 Killzones — Exact Time Windows

Killzones are periods of highest institutional activity. All times Eastern (ET):

| Session | Window | Notes |
|---|---|---|
| Asian Killzone | 8:00 PM – 12:00 AM ET | Sets Asian range; often manipulates before London |
| London Killzone | 2:00 AM – 5:00 AM ET | Highest probability for London-driven setups |
| New York Killzone | 7:00 AM – 10:00 AM ET | Primary execution window; overlap with London |
| London Close | 10:00 AM – 12:00 PM ET | Reversal window; London positions close |

**UTC equivalents:** London = 07:00–10:00 UTC; NY = 12:00–15:00 UTC

### 1.4 ICT Silver Bullet — Exact Windows

**VERIFIED: Only 3 Silver Bullet windows exist.** The 8 PM ET window is NOT a legitimate Silver Bullet — this was adversarially verified and refuted.

| Window | ET Time | UTC | Description |
|---|---|---|---|
| Silver Bullet 1 | 3:00 AM – 4:00 AM ET | 08:00–09:00 UTC | London open FVG setup |
| Silver Bullet 2 | 10:00 AM – 11:00 AM ET | 15:00–16:00 UTC | NY AM session FVG |
| Silver Bullet 3 | 2:00 PM – 3:00 PM ET | 19:00–20:00 UTC | NY PM session FVG |

**Silver Bullet setup rules:**
1. Identify a Fair Value Gap that forms during the first 15 minutes of the window
2. Wait for price to retrace INTO the FVG
3. Enter on the FVG fill (at or inside the gap)
4. Target: the next PD Array above (for longs) or below (for shorts)
5. Stop: below the low of the FVG candle (for longs)

### 1.5 ICT Macro Times — Specific 20-Minute Windows

ICT macro times are 20-minute algorithmic windows where price regularly displaces:

| Time (ET) | Window | Notes |
|---|---|---|
| 2:33 AM – 3:00 AM | Pre-London Macro | Sets up London direction |
| 4:03 AM – 4:30 AM | London Open Macro | Post-London open displacement |
| 8:50 AM – 9:10 AM | Pre-NY Macro | Highest institutional activity |
| **9:50 AM – 10:10 AM** | **NY Golden Window** | **Highest probability of all ICT macros** |
| 10:50 AM – 11:10 AM | Late AM Macro | Continuation or reversal |
| 1:10 PM – 1:40 PM | PM Macro | Sets up afternoon direction |
| 2:10 PM – 2:40 PM | Pre-Close Macro | Afternoon reversal window |
| 3:15 PM – 4:00 PM | Closing Macro | Final push before close |

**Rule:** During macro windows, reduce position size — the mechanical displacement can run stops. Wait for the displacement to complete, then enter on the subsequent retracement.

### 1.6 Market Maker Buy Model (7 Steps)

The institutional accumulation-to-delivery sequence:

1. **Old Lows swept** — Price takes out sell-side liquidity below a prior swing low (stop hunt)
2. **MSS (Market Structure Shift)** — A candle BODY closes above the last lower high (not just a wick)
3. **FVG created** on the displacement candle above
4. **Price retraces into the FVG**
5. **Entry zone** — enter long inside the FVG or at the OTE zone
6. **Price targets old highs** (buy-side liquidity) above
7. **Delivery to BSL** — trade closes at old highs or next PD Array above

### 1.7 Market Maker Sell Model (7 Steps)

1. **Old Highs swept** — Buy-side liquidity taken (stop hunt above swing high)
2. **MSS** — Candle BODY closes below the last higher low
3. **FVG created** on the displacement candle below
4. **Price retraces up into the FVG**
5. **Entry zone** — enter short inside the FVG or at OTE
6. **Price targets old lows** (sell-side liquidity) below
7. **Delivery to SSL** — trade closes at old lows or next PD Array below

**Critical MSS rule:** The candle BODY must close past the swing extreme — not just a wick. A wick break without body close is a liquidity sweep only; the MSS has not confirmed.

### 1.8 IPDA (Interbank Price Delivery Algorithm) Lookback Rules

| Lookback Period | Rule | Application |
|---|---|---|
| 20-day lookback | Near-term range boundary | Price regularly returns to fill imbalances from last 20 days |
| 40-day lookback | Medium-term range | Identifies the current "dealing range" for institutional positioning |
| 60-day lookback | Extended institutional range | Defines HTF premium/discount levels |

**IPDA key rule:** Mark the high and low of each lookback period. Price tends to be drawn from one boundary to the other within the lookback timeframe. If price is at the bottom of the 20-day range, the algorithmic target is the top of the 20-day range (and vice versa).

### 1.9 SMT Divergence Rules

SMT (Smart Money Technique) divergence identifies when correlated instruments fail to confirm each other's extremes:

- **Minimum correlation requirement:** 60% (0.60 correlation coefficient)
- **Best timeframe:** 15-minute or lower
- **Application:** When BTC makes a new high but ETH fails to make a new high simultaneously = bearish SMT divergence (one is being used to sweep liquidity while the other is already distributing)
- **Entry:** Enter the instrument that made the FALSE new high (the one that swept and failed)
- **Stop:** Above the swept high (for shorts)

**High-correlation pairs for SMT:**
- BTC / ETH (0.80–0.90 correlation)
- ETH / SOL (0.70–0.85)
- SPX futures / NDX futures (traditional markets)

### 1.10 Order Block Identification Rules

**Bullish Order Block:** The last bearish candle (or series of bearish candles forming a "base") immediately before a significant bullish displacement. Price often returns to this zone to fill institutional buy orders.

**Bearish Order Block:** The last bullish candle immediately before a significant bearish displacement.

**Validity rules:**
- An order block is valid until it is completely mitigated (price trades through the entire candle body)
- A partial mitigated OB (price enters but doesn't close through) = still valid
- OBs on higher timeframes (daily, 4H) carry more weight than lower TF OBs
- When multiple TF OBs stack (daily OB + 4H OB in same zone), confluence is high

**Breaker block rule:** When price fully breaks through an OB, the OB flips to a breaker — a zone that now acts in the opposite function (old demand becomes supply, old supply becomes demand).

---

## SECTION 2: STEVE MAURO BTMM — COMPLETE METHODOLOGY

### 2.1 The 5 EMA System (CORRECTED)

**Confirmed from multiple primary-source PDFs — EMA 13 NOT EMA 12:**

| EMA | Color | Nickname | Function |
|---|---|---|---|
| EMA 5 | Yellow | "Mustard" | Short-term momentum direction |
| **EMA 13** | Red | "Ketchup" | **Primary trend signal EMA (CORRECTED)** |
| EMA 50 | Light Blue | "Water" | Medium-term trend |
| EMA 200 | White | "Mayonnaise" | Long-term trend / market regime |
| EMA 800 | Dark Blue | "Blueberry" | Macro institutional level |

**Key signals:**
- EMA 5 crosses above EMA 13 = bullish momentum signal
- EMA 13 above EMA 50 = medium-term bullish trend
- Price above EMA 50 = long bias only
- Price below EMA 50 = short bias only (non-negotiable filter)
- All 5 EMAs stacked bullishly with price above all = maximum long conviction

### 2.2 Session Times (GMT)

| Session | Window (GMT) | Notes |
|---|---|---|
| Asia | 00:30 – 07:00 GMT | Sets the Asian range; ≤50 pips for valid BTMM setup |
| London | 07:30 – 13:00 GMT | Primary manipulation and entry window |
| New York | 13:30 – 20:30 GMT | Continuation and reversal window |

**Asian Range Rule:** If the Asian range exceeds 50 pips, the setup is considered too volatile for standard BTMM entries in that session. Skip until the next session.

### 2.3 The Three-Phase Market Maker Cycle

Market makers operate on a repeating cycle that completes roughly over 3–5 trading days:

1. **Accumulation (Consolidation):** Low volatility, range-bound; market makers absorbing retail orders
2. **Manipulation (Stop Hunt):** Fake move in the wrong direction to clear stop orders; creates the liquidity for Phase 3
3. **Distribution (Trend move):** The real directional move; market makers delivering price to target

**BTMM weekly cycle:**
- Monday–Tuesday: Often manipulation phase (stop hunts, false breakouts)
- **Midweek Reversal Window: Tuesday–Thursday** (not just Wednesday — the window spans all three days)
- Thursday–Friday: Distribution or end-of-week close; sometimes reversal back

### 2.4 Stop Hunt Distance Rules

| Type | Distance | Conditions |
|---|---|---|
| Standard stop hunt | 25–50 pips | Normal market conditions |
| Extended stop hunt | 51–100 pips | High-impact news, thin liquidity |
| Mega spike | 100–200 pips | Major fundamental event |

**Rule:** If price spikes beyond 100 pips from range boundary without news, it's likely a cascade liquidation, not a planned manipulation — avoid immediate fade entries.

### 2.5 Two-Hour Scratch Rule

After entering a trade based on BTMM structure:
- If the second leg of the move does NOT materialize within **2 hours** after the entry candle closes
- Exit the trade at breakeven or small loss (scratch the trade)
- The setup has stalled — institutional money is not following through as expected

### 2.6 Position Scaling: 5:4:3:2:1 Ratio

BTMM uses a specific decreasing scale-out system:

| Exit | Lot Ratio | When |
|---|---|---|
| Exit 1 | 5 parts | At first TP (initial target zone) |
| Exit 2 | 4 parts | At second target |
| Exit 3 | 3 parts | At third target |
| Exit 4 | 2 parts | At fourth target |
| Exit 5 | 1 part | Runner to final target |

**Trailing stop on runner:** 32-pip trailing stop applied to the final 1-part runner position.

### 2.7 Risk Parameters

| Level | Risk per Trade | Context |
|---|---|---|
| Learner | 1–3% | New to BTMM; strict stop adherence |
| Proficient | Up to 5% | Proven edge; experienced trader |
| Absolute maximum | 5% | Never exceed regardless of conviction |

**Daily target:** 50 pips (forex equivalent). In crypto, scale this proportionally to the instrument's ATR:
- BTC 1H ATR ~$800: daily target ≈ $400–$600 per BTC
- Scale to account size accordingly

### 2.8 TDI (Traders Dynamic Index) Settings

The TDI is BTMM's primary momentum and trend indicator:

| Parameter | Setting | Notes |
|---|---|---|
| RSI Period | 13 | Not 14 — BTMM-specific |
| Fast Signal MA | 2 | Short-term momentum |
| Slow Signal MA | 7 | Trend direction |
| Bollinger Bands Period | 34 | Volatility bands |
| BB Deviation | 1.619 | Fibonacci-based deviation |
| Middle Band Line (MBL) | 34 | Baseline |

**TDI Reading Rules:**
- RSI line above MBL (50) = bullish bias
- RSI above Slow MA = bullish momentum
- RSI crossing above Fast MA from below = entry signal
- RSI at upper BB (above 68) = overbought, look for shorts
- RSI at lower BB (below 32) = oversold, look for longs
- Fast MA crossing Slow MA = trend change signal

### 2.9 BTMM Candlestick Patterns

| Pattern | Description | Signal |
|---|---|---|
| Railroad Tracks | Two opposite-colored candles of equal size | Reversal signal |
| M Pattern | Double top formation with specific candle sequence | Bearish reversal |
| W Pattern | Double bottom formation | Bullish reversal |
| Half Batman | Single shoulder reversal before major move | Early entry signal |
| COW | "Change of Way" — momentum shift candle | Direction change |
| Snowflake | Doji-like indecision at key level | Reversal precursor |
| Shark Fin | Sharp spike and immediate reversal | Stop hunt confirmation |

### 2.10 BTMM 5-Check Decision Sequence

Before any trade entry, verify all 5:
1. **Session timing** — Are we in a valid BTMM session window?
2. **Asian range size** — Is it ≤50 pips (or crypto equivalent)?
3. **EMA alignment** — Does the 5 EMA and 13 EMA support the trade direction?
4. **Stop hunt confirmed** — Has the manipulation phase already occurred?
5. **TDI confirmation** — Does TDI support the entry direction?

All 5 must be green before entry. If any fails = no trade.

---

## SECTION 3: WYCKOFF ACCUMULATION/DISTRIBUTION — COMPLETE SCHEMATICS

### 3.1 Accumulation Schematic — Volume Requirements

Wyckoff uses specific volume signatures at each phase:

| Phase Event | Volume vs. 20-Period Average | Interpretation |
|---|---|---|
| SC (Selling Climax) | **200–400% of average** | Panic selling; institutions absorbing |
| AR (Automatic Rally) | **70–90% of SC volume** | Demand emerging; not full reversal yet |
| ST (Secondary Test) | **40–60% of SC volume** | Supply drying up; key confirmation |
| Spring | **Must be lower than SC** | Institutions absorbing final sellers |
| SOS (Sign of Strength) | High volume; > average | Institutional buying confirmed |
| LPS (Last Point of Support) | Low volume | Supply exhausted; ready to mark up |

### 3.2 Spring — Non-Negotiable Rules

The Spring is the most critical event in the accumulation schematic:

- **Price must penetrate below the Trading Range low** (the SC and ST lows)
- **Price must CLOSE BACK INSIDE the Trading Range within 1–3 bars** — this is non-negotiable. If price closes outside the range for more than 3 bars, it is not a Spring — it is a breakdown.
- A wick through the low that closes back inside the same candle = Type 1 Spring (ideal)
- A wick through the low that closes back inside within 2–3 candles = Type 2 or 3 Spring (still valid)

**Spring Type Classification:**

| Type | Volume | Characteristic | Entry Rule |
|---|---|---|---|
| Type 1 | High (climax volume) | Deep shakeout; strong reversal wick | Immediate entry at close of Spring candle |
| Type 2 | Moderate | Normal penetration; close back inside | Wait for test candle; enter on test hold |
| Type 3 | Low ("dry spring") | Barely penetrates; no climax | Immediate entry; institutions are loaded |

**Why low-volume Spring (Type 3) is highest conviction:** When price barely dips below the range on low volume, it means there are almost no sellers left — institutions have absorbed all supply.

### 3.3 Distribution Schematic — Key Events

| Event | Definition | Trading Implication |
|---|---|---|
| PSY (Preliminary Supply) | First selling into a rally | Warning; not yet a distribution signal |
| BC (Buying Climax) | Final high on very high volume | Peak demand; institutions distributing |
| AR (Automatic Reaction) | First significant decline from BC | Establishes the distribution range |
| ST (Secondary Test) | Retest of BC high on lower volume | Lower volume = supply confirmed; mark resistance |
| SOW (Sign of Weakness) | Price breaks below range mid-point | Distribution confirmed; add short |
| LPSY (Last Point of Supply) | Weak rally before final markdown | Short entry; last opportunity |
| UTAD (Upthrust After Distribution) | False breakout above BC high | Must reverse BACK INSIDE range within sessions |

**UTAD Rules:**
- Price breaks above BC high (Buying Climax high)
- Volume is high but price action fails to sustain above the level
- Price reverses back inside the distribution range within the SAME or next 1–3 candles
- If price stays above BC for more than 3–5 candles, the distribution is failing (accumulation re-starting)

### 3.4 Phase Identification — Complete Framework

**Accumulation Phases:**

| Phase | Description | Key Event |
|---|---|---|
| Phase A | Stopping downtrend | SC, AR occur; establishes the range |
| Phase B | Building cause | ST, minor rallies; range established |
| Phase C | Testing supply | Spring or Shakeout occurs |
| Phase D | Dominance of demand | SOS, LPS; upward movement begins |
| Phase E | Markup | Price exits range; full trend begins |

**Best entry point:** Phase D, specifically at the **BUYLPS** (Buy at the Last Point of Support). This is statistically the highest-probability entry in the entire accumulation schematic — Phase D has passed the Spring test, institutional buying is confirmed, and the stop placement is tight (below the LPS low or below the Spring low).

### 3.5 Nine Buying Tests (Accumulation Checklist)

Before entering a Wyckoff long, verify:

1. **Price objective**: Has the cause (horizontal P&F count) been established?
2. **Low-area activity**: Is price in the lower portion of the range?
3. **Preliminary support**: Did we see a PS + SC sequence?
4. **Selling climax**: Clear SC with volume spike?
5. **Secondary test**: ST on lower volume confirming?
6. **Volume**: Decreasing volume on downswings in Phase B/C?
7. **Price spread**: Narrowing price spreads on downswings?
8. **Relative performance**: Is this instrument stronger than its peers/sector?
9. **Turning point**: Has the Spring/shakeout occurred?

**Minimum R:R requirement from Test #9:** At least **3:1** measured from the entry price to the P&F count target.

### 3.6 Point & Figure Count Formula

For calculating the upside target from an accumulation base:

```
Target = (Count × Box Size × Reversal Factor) + Spring Low
```

Where:
- **Count** = Number of columns across the base (horizontal extent of accumulation)
- **Box Size** = The P&F box value (typically 1% of price for crypto)
- **Reversal Factor** = Usually 3 (3-box reversal is standard)
- **Spring Low** = The price level of the Spring event

**Application for crypto:** Use 1% box size on BTC. A 20-column accumulation base at $60,000 Spring low:
- Target = 20 × 600 × 3 + 60,000 = $96,000

### 3.7 Re-Accumulation vs. Primary Accumulation

**Critical distinction for identification:**

| Feature | Primary Accumulation | Re-Accumulation |
|---|---|---|
| Precedes | Initial large uptrend | Continuation of existing uptrend |
| Phase A appearance | SC + AR (classic) | **Looks like Distribution** (PSY + BC pattern) |
| Volume at top | Panic selling at SC | Looks like selling at a high (confusing) |
| Context | After sustained downtrend | During uptrend pullback |
| Spring | Deep; tests major lows | Shallower; tests local structure |

**The critical trap:** Phase A of re-accumulation pattern looks exactly like distribution to inexperienced Wyckoff traders. The solution is context — if the primary uptrend is still intact (higher highs/highs above previous range), suspect re-accumulation when you see a "distribution-looking" pattern.

---

## SECTION 4: HARMONIC PATTERNS — COMPLETE FIBONACCI TRADING RULES

### 4.1 Complete Pattern Ratio Reference Table

| Pattern | AB/XA Retracement | BC/AB Retracement | D Definition | D Extends Beyond X? |
|---|---|---|---|---|
| ABCD Classic | — | 0.618 of AB | AB=CD | No |
| ABCD Alternate | — | 0.786–0.886 of AB | 1.618–2.000 × BC | No |
| **Gartley** | **0.618** | 0.382 or 0.886 | **0.786 XA** | No |
| **Bat** | **0.382–0.500** | 0.382 or 0.886 | **0.886 XA** | No (barely) |
| Alternate Bat | ≤0.382 | 0.382–0.886 | **1.130 XA** | Yes (slightly) |
| **Butterfly** | **0.786** | 0.382 or 0.886 | **1.272 or 1.618 XA** | Yes |
| **Crab** | 0.382–0.618 | 0.382 or 0.886 | **1.618 XA** | Yes |
| Deep Crab | 0.886 | 0.382 or 0.886 | 1.618 XA | Yes |
| **Cypher** | 0.382–0.618 | **1.272–1.414 of XA** | **0.786 of XC** | Sometimes |
| Shark (OXABC) | — | 1.130–1.618 of OX | **0.886–1.130** | Yes |
| Three Drives | — | 0.618 (retrace) | **1.272 extension** | Special |

**Bold = highest-reliability patterns for crypto 1H trading**

### 4.2 Pattern-by-Pattern Critical Rules

**Gartley (most conservative):**
- B point MUST be exactly 0.618 XA — this is the non-negotiable differentiator
- D completes inside the XA range (never beyond X)
- PRZ: 0.786 XA + BC projection + AB=CD all cluster
- Stop: Just beyond X (or 1.13 XA for buffer against wicks)
- T1: 38.2–61.8% retracement of A-D leg; T2: Point A

**Bat (most reliable for crypto):**
- B point: 0.382–0.500 XA. If B reaches 0.618 → it's a Gartley, not Bat
- D completes at 0.886 XA — extremely tight stop possible
- Best R:R of all patterns due to 0.886 closeness to X
- Stop: Just beyond X
- T1: 0.382 of AD; T2: 0.618 of AD (near B); T3: Point A

**Butterfly (extension pattern):**
- B point MUST be 0.786 XA — the signature defining ratio
- D extends BEYOND X (breakout from the XA range)
- Higher confirmation requirement due to extension nature
- Stop: Beyond 1.618 XA

**Crab (tightest PRZ):**
- CD is extreme: 2.240× or 3.618× the BC leg
- Creates the tightest PRZ of any standard harmonic (high accuracy when valid)
- D at 1.618 XA — extreme extension
- Stop: Just beyond 1.618 XA

**Cypher (unique rule):**
- D is defined as 0.786 retracement of **X-to-C leg** (NOT XA — unique)
- BC must extend beyond A (minimum 1.272 XA, maximum 1.414 XA)
- BC outside the 1.272–1.414 range = pattern invalid
- Best for consolidating/range-bound markets
- Stop: Below X

**Shark (OXABC notation):**
- Uses O, X, A, B, C labels (not XABCD) — the "D" point is called "C" in Shark
- Two defining PRZ levels must converge: 0.886 retracement AND 1.13 extension
- Produces short-lived counter-trend moves — requires active management
- Short-term targets only; not suitable for multi-day holds

### 4.3 PRZ (Potential Reversal Zone) Construction

The PRZ is defined by three independent Fibonacci measurements converging:

1. **Primary:** XA ratio (the pattern-defining level)
2. **Secondary:** BC projection (CD extension level)
3. **Tertiary:** AB=CD completion point

**PRZ validity requirements:**
- Minimum: 2 of 3 Fibonacci components must converge
- AB=CD must be present in the PRZ (penalty for absence in scoring)
- PRZ width: <1% price convergence for crypto (tight); >2% = reduced confidence
- All three components within 0.5% = high-conviction PRZ

**PRZ tolerance for crypto:**
- Standard markets: ±2% tolerance per ratio
- **Crypto-adjusted: ±3–5% tolerance** (higher volatility requires wider acceptance)
- At ±2%: win rates 55–65%
- At ±5%: win rates up to 77.4% (Zamirroshan study, EURUSD 1H, 12 years, 133 patterns)

### 4.4 Entry, Stop, and Target Rules

**Entry Method 1 — Limit (Aggressive):**
- Place limit at primary Fibonacci level (e.g., 0.886 XA for Bat)
- No confirmation required
- Best for: high-scoring patterns (7+/10), tight PRZs
- Risk: no confirmation means higher failure rate

**Entry Method 2 — Confirmed (Recommended for crypto):**
1. Price reaches the PRZ
2. Wait for reversal candlestick: pin bar, engulfing, doji, inside bar
3. RSI divergence present at D point
4. MACD histogram divergence forming
5. Enter on next candle close OR on FVG retest from confirmation impulse

**Entry Method 3 — PRZ Midpoint:**
- Enter at the middle of the PRZ zone
- Stop just beyond the full PRZ width
- Better R:R than entering at the extreme

**Profit Target System (Carney standard):**
- T1: 0.382 retracement of AD leg (close 33–50% of position)
- T2: 0.618 retracement of AD leg (close another 25–33%)
- T3: Return to point A
- Extended T4: 1.272 XA extension from D (for high-momentum reversals)

**Move stop to breakeven:** After T1 hit, move stop to entry price.

### 4.5 Win Rate Data by Pattern Type

| Pattern | Win Rate (Strict ±2%) | Win Rate (±5%) | Notes |
|---|---|---|---|
| Bat | 65–75% | Up to 77% | Highest reliability; tight stop |
| Gartley | 60–70% | 65–77% | Requires strict 0.618 B point |
| Crab | 60–70% | ~75% | Tightest PRZ when valid |
| Butterfly | 48–65% | Varies | Extension; needs more confirmation |
| Cypher | 40–60% | 55–65% | Lower in actual backtests |
| Shark | 50–60% | N/A | Short-lived; active management only |
| Three Drives | 55–65% | Higher on D/W | Best on daily/weekly; drops on 1H |

**Realistic crypto 1H win rate:** ~58% (vs. 68% in forex — lower due to higher volatility and manipulation in smaller caps). BTC and ETH generate the most reliable patterns.

### 4.6 Harmonic Pattern Failure Rules

**Pattern is invalidated when:**
- For Gartley/Bat/Cypher: candle BODY closes beyond X point
- For Butterfly: candle body closes beyond 1.618 XA
- For Crab: candle body closes beyond 1.618 XA
- For Shark: price closes through the 0.886/1.13 PRZ zone with no rejection

**Trading the failure (Anti-Pattern):**
- When a pattern fails, enter in the continuation direction
- Entry: after price closes beyond X (or 1.618 for extension patterns)
- Stop: re-entry back into the PRZ zone
- Target: measured move = size of XA leg projected from breakout point
- These can become high-probability momentum trades

**Signs of imminent failure (avoid entry):**
- Large Marubozu candles approaching PRZ with no hesitation
- Volume expanding (not contracting) as price approaches PRZ
- No RSI divergence forming at D
- Fundamental catalyst (news) in the same session as PRZ completion
- Pattern trading against dominant HTF trend

### 4.7 Crypto-Specific Adjustments

**For 1H crypto harmonic bot:**
- Fibonacci tolerance: ±3–5% (vs. ±2% standard)
- Stop buffer: Add 0.5× ATR(14) beyond the pattern-defined stop level
- Confirmation: RSI divergence OR reversal candle (prefer both)
- 4H timeframe alignment check REQUIRED before any 1H entry
- Only trade BTC, ETH, or top-5 market cap assets for highest reliability
- Avoid entries during 2–6 AM UTC (low liquidity = high false signal rate)
- Minimum GBB Auto-Validator score: 6/10 (target 7+/10)

**Timeframe reliability for crypto:**
1. Daily/Weekly: highest
2. 4H: high, good frequency
3. **1H: moderate, good frequency** ← appropriate for bot
4. 15M and below: lower reliability, noise increases

---

## SECTION 5: ADVANCED TRADE MANAGEMENT

### 5.1 Entry Execution Rules

**Use LIMIT orders when:**
- Entering at a defined structural level (OB, FVG, OTE zone, S/R)
- Price is in a range or trending slowly
- Want maker fees (0.01–0.02% vs. 0.05% taker on Binance/Bybit)
- Scaling into an existing position

**Use MARKET orders when:**
- Breaking out aggressively — need immediate execution
- Exiting a losing trade that hit stop criteria
- **NEVER use stop-limit for protective stops in crypto** — gaps through limit cause no fill during cascades
- Use **Stop-Market** for all protective stops

**OTE Entry Rules (ICT Sniper):**
- Draw Fibonacci from swing low to swing high (for pullback longs)
- OTE zone: 0.62 (entry start) → 0.705 (sweet spot) → 0.79 (outer limit)
- Limit order at 0.705 for best R:R
- Invalidation: candle body close beyond 1.0 level
- Targets: -0.27 and -0.62 extensions

### 5.2 ATR-Based Stop Loss Formulas

```
Long Stop = Entry Price − (ATR_14 × Multiplier)
Short Stop = Entry Price + (ATR_14 × Multiplier)
```

**Multipliers by setup type:**

| Setup Type | ATR Period | Multiplier | Notes |
|---|---|---|---|
| Scalp (<15M) | 7 | 1.0–1.5× | Tight; high premature stop rate |
| **Day trade (1H)** | **14** | **1.5–2.0×** | **Standard; use for 1H bot** |
| Swing (4H) | 14 | 2.0–2.5× | Balanced |
| High-vol altcoins | 14 | 2.5–3.0× | Wider to absorb noise |
| Chandelier trailing | 22 | 3.5–4.0× | Crypto-optimized trailing |

**Chandelier Exit formula:**
```
Trailing Stop (long) = Highest High (22 periods) − ATR(22) × 3.5
```
Updates every candle close. Best in trending conditions; underperforms in chop.

### 5.3 Stop Placement — Structural Rules

**The "Cold Side" Rule:** Stop must be placed where the market would only reach if your thesis is definitively wrong — not where normal volatility might briefly touch.
- Long entry after SSL sweep: stop goes below the swept low
- Short entry at OB rejection: stop goes above the top of the OB

**Liquidity Heatmap Stop Placement:**
- NEVER place stop directly at a large liquidation cluster — institutions target these
- Push stop 0.5–1% beyond any major liquidation cluster within your normal stop zone
- Use clusters as TP targets, not as stops

**Maximum Pain Placement:**
1. Find the most obvious retail stop level
2. Add 0.5–1× ATR beyond that level
3. Use irregular numbers (avoid round numbers like $65,000 — use $64,623)

**Crypto-specific stop buffer:** Add 1.0–1.5% beyond the obvious structural level to absorb stop-hunt wicks.

### 5.4 Profit Taking — Exact Percentages and Timing

**Standard professional framework:**
- TP1 (first target): **Close 50% of position**; move stop to breakeven
- TP2 (second target): **Close 25% of position**; trail stop behind structure
- TP3 / Runner: **Final 25%** with trailing stop

**Alternative aggressive framework:**
- TP1: 33% at 1R (guarantees trade is breakeven even if 67% stops at entry)
- TP2: 33% at 2R
- TP3: 34% runner with trailing

**Conservative (prop firm):**
- TP1: 75% at 1.5R
- Runner: 25% with tight trailing

**Move to Breakeven Timing:**

| Account Type | Trigger | Notes |
|---|---|---|
| Day trades (sub-4H) | **1R profit** | 20–30% will stop at B/E — acceptable |
| Swing trades (4H+) | **1.5–2R profit** | Better buffer against pullbacks |
| Prop firm | 1R (tight rules) | Account for fees in B/E price |

**True breakeven formula:** Entry + (Entry × fee rate). Set stop at entry + fee % to actually break even net of commissions.

### 5.5 Trailing Stop Methods

**Method 1 — Ratchet Stop:**
- Move to B/E at 1R
- Move to +0.5R at 1.5R profit
- Move to +1R at 2R profit
- Move to +1.5R at 2.5R profit

**Method 2 — Structure Trail:**
- Trail stop below each successive swing low (for longs)
- Best for trending moves; ineffective in chop

**Method 3 — ATR Chandelier Trail:**
```
Stop = Rolling Highest High (14 periods) − ATR(14) × 3.0 (for longs)
```
Updates every candle close; crypto-optimized shorter lookback.

**When to "Let It Run":**
- Funding rate negative and you are long (you are being paid to hold)
- Volume expanding in your direction on each successive candle
- Price accelerating through Low Volume Nodes (LVN) on volume profile
- Open Interest rising with price (new money entering)
- Major liquidation cluster ahead in your direction (price will be drawn to it)

### 5.6 Scaling In (Pyramiding) Rules

**Decreasing size pyramid:**
| Add | Size % of Total Intended | Trigger |
|---|---|---|
| Initial entry | **50%** | Original setup signal |
| Second add | **30%** | Price confirms beyond first target |
| Third add | **20%** | Second confirmation / extension |

**Hard rule:** Total combined risk across ALL pyramid adds must never exceed your single-trade risk limit (e.g., 1% of account). Each add's individual risk is smaller because price has moved favorably.

**Maximum add levels:** 3–4 maximum. Beyond 4, trend exhaustion probability exceeds reward justification.

### 5.7 Time-Based Management

**1H setup time stops:**
- If no meaningful progress (>0.5× ATR in intended direction) within **5 completed 1H candles** after entry → tighten stop dramatically or exit
- **10-hour time stop:** Absolute maximum hold time for a 1H breakout/reversal setup showing no progress
- **3-candle rule:** If next 3 candles after entry all close within the entry candle's range → exit or tighten

**Breakout-specific:** Follow-through should appear within **2–4 candles** after a valid 1H breakout. More than 4–5 candles stalling at the breakout = likely failed breakout.

### 5.8 Session-Based Management for Crypto 24/7

**Reduce/exit before low-liquidity windows:**
- If holding a 1H setup heading into the Asia session (00:00 UTC) with no clear trend → consider 50% partial exit
- Funding checkpoint times (00:00, 08:00, 16:00 UTC): evaluate positions before each; unfavorable funding >0.04% = tighten stop

**FOMC/NFP Management:**
- Close or reduce leveraged positions **15–30 minutes before** announcement
- Reduce size 50–75% if unable to fully exit
- Crypto moves average 2% on FOMC days vs. 1.25% non-FOMC
- Wait 24–48 hours for full crypto reaction before entering new positions

### 5.9 Minimum R:R by Setup Type

| Setup Type | Minimum R:R | Notes |
|---|---|---|
| Scalp (1M–5M) | 0.8:1 – 1.2:1 | Requires 65%+ win rate |
| VWAP bounce | 1.5:1 | |
| **Pullback entry (trend)** | **2:1** | **Standard for 1H strategies** |
| Breakout | 2:1 – 3:1 | Lower win rate (~38–45%); needs reward |
| Reversal (counter-trend) | 3:1 – 5:1 | High failure rate; must have large reward |
| OTE/FVG entries | **2:1 minimum** (often achieves 4:1–8:1 naturally) | ICT setups by design |

**Breakeven win rates:**
- At 2:1 R:R: only need **33% win rate** to be profitable
- At 3:1 R:R: only need **25% win rate**
- At 1:1 R:R: need **50% win rate** (minimum viable)

### 5.10 Funding Rate Thresholds

| Funding Rate (per 8H) | Signal | Action |
|---|---|---|
| ±0.01% | Normal | No adjustment |
| +0.02–0.04% | Mild long bias | Monitor; acceptable for short-term longs |
| **+0.04–0.075%** | **Elevated; overheated** | **Avoid new long entries** |
| **+0.075%+** | **Extreme** | **Strong contrarian short signal** |
| −0.02% to −0.04% | Mild short bias | Potential long opportunity |
| −0.04%+ | Extreme negative | Strong contrarian long signal |

**Funding cost calculation:**
```
Funding Cost = Position Notional × Funding Rate × Number of 8H Periods
```
If total expected funding cost exceeds 0.5% of position, add to minimum TP requirement.

---

## SECTION 6: POSITION SIZING — KELLY, VOLATILITY-ADJUSTED, ADVANCED METHODS

### 6.1 Fixed Fractional (Core Formula)

```
Position Size (units) = Dollar Risk / Stop Distance in $
Dollar Risk = Account Balance × Risk %
Position Size (Notional) = Dollar Risk / Stop Distance %
```

**Example:** $10,000 account, 1% risk = $100 risk. BTC stop distance = $1,300. Position = $100/$1,300 = 0.0769 BTC ($4,998 notional).

**Industry standard risk percentages:**

| Experience Level | Risk % | Rationale |
|---|---|---|
| Beginners | 0.5 – 1.0% | 10 losses = 9.5% max drawdown |
| Intermediate | 1.0 – 2.0% | CFA-backed "2% Rule" |
| Advanced | 2.0 – 3.0% | Proven edge required |
| Hard ceiling | **3%** | **Never exceed regardless of conviction** |

**Statistical survival at 10 consecutive losses:**
- At 1% risk: 90.44% of capital remaining
- At 2% risk: 81.71% remaining
- At 5% risk: only 59.87% remaining

### 6.2 Kelly Criterion — Complete Formula and Rules

**Kelly formula:**
```
f* = (b × p − q) / b

Where:
  f* = fraction of capital to risk
  b = reward-to-risk ratio (avg win ÷ avg loss)
  p = win probability
  q = loss probability (1 − p)
```

**Simplified trading form:**
```
Kelly % = W − [(1 − W) / R]
Where: W = win rate, R = reward/risk ratio
```

**Kelly fraction examples:**

| Win Rate | R:R | Full Kelly | Half Kelly | Quarter Kelly |
|---|---|---|---|---|
| 50% | 2.0 | 25.0% | 12.5% | 6.25% |
| 55% | 1.5 | 21.7% | 10.85% | 5.4% |
| 60% | 1.2 | 26.7% | 13.3% | 6.7% |
| 40% | 3.0 | 20.0% | 10.0% | 5.0% |

**Why Full Kelly is dangerous:**
- 20% drawdown: **80% probability** at full Kelly
- 50% drawdown: **50% probability** at full Kelly
- 80% drawdown: **20% probability** at full Kelly
- Betting >2× Kelly produces **negative** geometric growth rate

**Professional recommendation:**
- **Half Kelly:** 75% of growth rate at 50% variance reduction
- **Quarter Kelly:** Recommended specifically for crypto
- **Maximum for live crypto:** 10–25% of calculated Kelly fraction
- **Minimum trade history required:** 50 closed trades for any reliability; 100+ preferred

**Conservative input adjustment for crypto:**
- Reduce backtested win rate by 10% before calculation
- Reduce R:R estimate by 10%
- Use bootstrap 5th-percentile worst case (results in ~50% of naive Kelly)

### 6.3 ATR-Based Volatility-Adjusted Position Sizing

```
Position Size = Risk Amount / (ATR_14 × Multiplier)

Full form:
Position Size = (Account Balance × Risk %) / (N × ATR_14)
```

**ATR multiplier selection:**

| Context | Multiplier | Application |
|---|---|---|
| Aggressive / calm markets | 1.5× | Tighter stop; larger size |
| **Standard balanced** | **2.0×** | **Default for 1H crypto** |
| Volatile assets / trend-following | 3.0× | Wider stop; smaller size |

**BTC volatility regime adjustments:**

| Market Regime | Daily ATR | 1H ATR (approx) | Adjustment |
|---|---|---|---|
| Compressed (low vol) | 1.0% | $400–600 | Larger position; same $ risk |
| **Normal trending** | **2.0%** | **$800–1,200** | **Standard** |
| Elevated volatility | 3.0% | $1,500–2,000 | Smaller position |
| Extreme (news/crash) | 5%+ | $2,500+ | **Reduce risk % to 0.5–0.25%** |

**Extreme volatility rule:**
```
If ATR_14 > 2 × ATR_50_average: reduce base risk % to 0.5%
If ATR_14 > 3 × ATR_50_average: reduce to 0.25% or exit all positions
```

### 6.4 Optimal f (Ralph Vince)

**HPR formula:**
```
HPR_i(f) = 1 + f × (−Return_i / Worst_Loss)
TWR(f) = HPR_1 × HPR_2 × ... × HPR_n
```
Find the `f` value (0–1) that maximizes TWR = Optimal f.

**Why Optimal f is more dangerous than Kelly:** Optimal f models actual trade distribution (not binary bets), typically recommending larger fractions. Every new trade could produce a loss exceeding historical worst case.

**Live trading application:** Use 10–25% of Optimal f only. Calculate from the **5th percentile worst loss** (bootstrap) rather than single worst historical loss.

### 6.5 Risk of Ruin Formula

```
RoR = ((1 − A) / (1 + A))^N

Where:
  A = trader's edge (EV per trade as R-multiple)
  N = number of risk units (Account Size / Dollar Risk Per Trade)
```

**Scenario analysis (to maintain RoR < 1%):**
- 1% risk, 50% win rate, 2:1 R:R → RoR ≈ **~0%** (excellent)
- Require either: Risk ≤ 1% with edge A ≥ 0.1, OR risk ≤ 0.5% for near-zero RoR

**Consecutive loss probability:**
```
P(n losses in a row) = (1 − Win Rate)^n
```
At 50% WR: 5 consecutive losses has 3.1% probability (1 in 32 sequences).

**Expected maximum losing streak over N trades:**
```
Expected Streak = log(N) / log(1 / loss_rate)
```
At 60% WR over 1,000 trades: ~7.5 consecutive losses expected.

### 6.6 Correlation-Adjusted Portfolio Sizing

**Scale factor for multiple correlated positions:**
```
Scale Factor = 1 / √(1 + (n − 1) × ρ̄)
```

**Crypto correlation thresholds:**

| Correlation Range | Action |
|---|---|
| 0.90–1.00 | Do not open second position |
| **0.70–0.90** | **Reduce second position to 50% of normal** |
| 0.40–0.70 | Meaningful diversification; minor scaling OK |
| Below 0.40 | Full independent sizing allowed |

**Real crypto correlations:**
- BTC/ETH: 0.80–0.90 (treat as nearly same trade)
- ETH/SOL: 0.70–0.85
- Top-30 altcoins/BTC: 0.60–0.95

**5-coin portfolio at 0.85 average correlation:**
```
Scale = 1 / √(1 + 4 × 0.85) = 1 / √4.4 = 0.48
```
→ Size each position at only 48% of normal — 52% reduction for correlated assets.

### 6.7 Setup Quality-Based Sizing

| Setup Grade | Risk % | Criteria |
|---|---|---|
| A+ Setup | 1.5% | Multi-TF confluence, R:R ≥ 3:1, structural level, HTF trend aligned |
| B Setup | 1.0% | Standard criteria, R:R 2:1–3:1, single TF, one confluence |
| C Setup | 0.5% | Speculative, R:R 1.5:1–2:1, limited history |
| D / Disqualified | 0% | R:R < 1.5:1, no clear stop anchor, counter-trend without strong signal |

**Scoring system (0–10 points):**
- R:R ≥ 3:1 = 3pts; 2:1–3:1 = 2pts; 1.5:1–2:1 = 1pt; <1.5:1 = 0 + flag
- 3 TF aligned = 3pts; 2 TF = 2pts; 1 TF = 1pt
- Structural stop = 2pts; ATR-only = 1pt; arbitrary = 0pts
- Volume/momentum confirmation = 2pts; absent = 0pts
- Thresholds: 8–10 = A+ (1.5% risk); 5–7 = B (1.0%); 3–4 = C (0.5%); <3 = no trade

### 6.8 Drawdown-Based Sizing Protocol (3-Tier)

| Tier | Drawdown Level | Position Size | Action |
|---|---|---|---|
| Normal | 0 – 3% | **100%** | Continue at full size |
| Elevated Risk | 3 – 5% | **50% of normal** | A-setups only |
| Capital Protection | 5%+ | **Stop → re-enter at 25%** | Full diagnostic review |

**Recovery staging:**
```
0.5R → (5 consecutive winning days) → 0.75R → (stable 1 week) → 1.0R
```

**Drawdown recovery math (why size reduction matters):**

| Drawdown | Gain Needed to Recover |
|---|---|
| 5% | 5.3% |
| 10% | 11.1% |
| 20% | 25.0% |
| 50% | 100.0% |
| 75% | 300.0% → functionally dead |

### 6.9 Leverage Rules for Crypto Perpetuals

**Effective leverage formula:**
```
Effective Leverage = Position Notional / Account Equity
```

**Critical concept:** Leverage does NOT change planned dollar risk. It changes margin requirements and liquidation proximity. A $100 planned risk is $100 regardless of whether leverage is 5× or 20×.

**Liquidation distance:**
```
Liquidation Distance ≈ 100% / Chosen Leverage
```
- 10× leverage: ~10% adverse move before liquidation
- 20× leverage: ~5% adverse move

**Stop must be 20–50% less distance than liquidation.** If stop is at $58,800 but liquidation triggers at $58,500, a wick liquidates before the stop fires.

**Recommended leverage for 1H crypto (1–3% stop distances):**

| Account/Experience | Max Leverage | Notes |
|---|---|---|
| Beginner | 2–3× | Liquidation buffer critical |
| Intermediate | 3–5× | Standard risk management |
| Advanced | 5–10× | Only with hard stops + alerts |
| 1H trading | 5–15× | Intraday; close before funding |

### 6.10 Parameter Matrix Summary

| Parameter | Conservative | Standard | Aggressive |
|---|---|---|---|
| Risk per trade (base) | 0.5% | 1.0% | 1.5–2.0% |
| A+ setup multiplier | 1.0× | 1.5× | 2.0× |
| Max portfolio heat | 5% | 6–8% | 10% |
| Max leverage (1H) | 5× | 10× | 15× |
| Stop distance (ATR mult.) | 2.5× | 2.0× | 1.5× |
| Drawdown Tier 2 trigger | 3% | 5% | 8% |
| Kelly fraction (if used) | 10% | 15–25% | 25–50% |
| Correlation threshold | 0.60 | 0.70 | 0.80 |

---

## SECTION 7: MULTI-TIMEFRAME ANALYSIS — COMPLETE DECISION FRAMEWORK

### 7.1 Win Rate Data by Alignment Level

The most critical quantitative finding in MTFA research:

| Alignment Level | Win Rate | Source |
|---|---|---|
| 0 TF (random entries) | 38–39% | BB/LB 8,734-trade study (Jan 2023–Jun 2024) |
| 1 TF (single timeframe) | 45–49% | Multiple backtest sources |
| **2 TFs aligned** | **58–64.7%** | **BB/LB study; consistent across asset classes** |
| **3 TFs aligned** | **65–72%** | **TradealGo +3 score study; 2023 research** |
| 3 TFs + HTF at key level | 70–74% | SMC backtest: OB + FVG + MTF alignment |
| Counter-trend vs. HTF | 38–42% | "Loses money 58% of time" — TradealGo data |

**QuantPedia BTC Study (Dec 2018–Nov 2025) — Adding D1 filter to 1H MACD:**
- Sharpe ratio: 0.33 → **0.80 (+142%)**
- Max drawdown: -23.9% → **-12.4% (-48%)**
- Annual return: 4.6% → **6.6% (+43%)**

**Position sizing by alignment:**
- 3+ TFs aligned: **Full (1.0×) size**
- 2 TFs aligned: **0.75× size**
- 1 TF / counter-trend: **0.25× or avoid**

### 7.2 The Three Functional Layers

| Layer | Function | Timeframe |
|---|---|---|
| Layer 1 — Bias | Directional intent; determines which side to trade | Highest TF in use |
| Layer 2 — Setup | Where trade premises develop; identifies the specific zone | Middle TF |
| Layer 3 — Execution | Times the precise entry at the identified zone | Lowest TF |

**HTF always has authority.** A bearish daily bias means NO long trades regardless of how clean a 1H long looks. This rule is absolute.

### 7.3 Timeframe-by-Timeframe Rules

**Monthly Chart:**
- Extract: multi-year highs/lows (highest-priority liquidity pools), macro regime
- Use: define targets and hard reversal zones only — not entry points
- Mark and leave; approaching monthly levels warrants increased caution

**Weekly Chart:**
- Extract: PWH (Previous Week High), PWL (Previous Week Low), weekly open (00:00 UTC Sunday for crypto), weekly FVGs, equal highs/lows
- **Crypto weekly note:** Weekly lows occur on Monday ~40% of the time (3× statistical expectation) = Monday liquidity sweep tendency before real weekly directional move
- Trend rule: 2 consecutive HH + HL on weekly = bullish declared

**Daily Chart:**
- Extract: PDH, PDL, daily FVGs, daily OBs, daily EMAs, midnight open
- **ICT Midnight Open Rule:** NY midnight (00:00 AM NY = 05:00 UTC) is the daily directional reference
  - Price above Midnight Open at London/NY session start = bullish daily bias
  - Price below Midnight Open = bearish daily bias
- **PDH/PDL Rules:**
  - Fakeout ABOVE PDH + rejection back below = bullish liquidity sweep signal
  - Fakeout BELOW PDL + rejection back above = bearish liquidity sweep signal
- 7-step daily bias workflow:
  1. Read daily order flow (HH/HL vs LL/LH)
  2. Identify unfilled daily FVGs and imbalances
  3. Mark closest BSL and SSL above and below
  4. Check prior day's close vs. midpoint
  5. Validate against 4H structure
  6. Set bias when 3+ signals agree
  7. Skip day if signals conflict

**4H Chart:**
- Extract: 4H OBs, 4H FVGs, 4H demand/supply zones, 4H EMA alignment
- **When price is AT a 4H level:** switch to 1H/15M for entry timing — do not enter on 4H
- **When price is BETWEEN 4H levels:** do not enter. Wait.
- Trading between levels = most false signals in lower timeframes
- 4H bullish confirmation: 13 EMA > 21 EMA > 50 EMA, price above all three

**1H Chart (Primary execution context for bot):**
- Extract: 1H OBs, 1H FVGs, 1H swing highs/lows, 1H EMA alignment
- Draw: 4H level transferred down, PDH/PDL, session VWAP or opening range
- Entry setup: Daily bullish → 4H bullish or pulling back → 1H shows CHOCH/BOS → enter on 15M confirmation at 1H demand zone

**15M Chart:**
- Purpose: First execution confirmation timeframe
- Trigger: bullish market structure break with FVG in confirmation candle = valid entry signal
- Enter at 15M candle body close or FVG retest

**5M Chart:**
- Purpose: Precision entry for minimum stop distance
- Use only after 15M has confirmed — 5M BOS at the 15M structure break area

### 7.4 EMA Stack by Timeframe

| Timeframe | Fast EMA | Medium EMA | Slow EMA | Primary Trend Reference |
|---|---|---|---|---|
| Monthly | 5 | 10 | 20 | 20-month EMA |
| Weekly | 10 | 20 | 50 | 50-week EMA |
| Daily | 20 | 50 | 200 | **200-day EMA (golden/death cross)** |
| 4H | 13 | 21 | 50 | 50-period 4H EMA |
| **1H** | **13** | **21** | **50** | **21-period 1H EMA** |
| 15M | 8 | 13 | 21 | 13-period 15M EMA |
| 5M | 8 | 13 | — | 8-period 5M EMA |

**Full bullish EMA stack (maximum conviction):**
- Daily: Price > 20 > 50 > 200, all rising
- 4H: Price > 13 > 21 > 50, all rising
- 1H: Price > 13 > 21 > 50, all rising
- Action: Buy pullbacks to nearest EMA only. No shorts at all.

**21 EMA universality principle:** If you can only plot one EMA per timeframe, use the 21. It is the most consistent single EMA reference across ICT, BTMM, and professional price action communities.

### 7.5 Trend Declaration Rules

**Structure-based (non-negotiable minimum):**
- **Bullish:** Minimum 2 consecutive HH + 2 consecutive HL, with most recent swing low intact
- **Bearish:** Minimum 2 consecutive LL + 2 consecutive LH, with most recent swing high intact
- **Neutral/Range:** Alternating sequences, no sustained direction; ADX < 20
- **Range rule:** Do not apply trend-following MTFA during neutral/range conditions

**Bias vs. Direction distinction:**
- **Bias** = directional tendency from highest TF; static for session/multi-day period
- **Direction** = immediate price movement on execution TF; can temporarily oppose bias
- If daily bias is bullish and 1H direction is bearish (pullback) → the 1H bearish direction is NOT tradeable as a short

### 7.6 Conflict Resolution Rules

| Conflict Scenario | Rule | Action |
|---|---|---|
| Weekly bullish, Daily bearish | Daily = weekly pullback | No shorts; wait for daily bounce at weekly support for long |
| Daily bullish, 4H bearish | 4H = daily pullback | No shorts on 4H; wait for 4H to reach daily demand; enter long on 1H confirmation |
| Daily bullish, 1H bearish | 1H = intraday pullback | No shorts; wait for 1H to reach 4H level; enter long on 15M BOS |
| 4H bullish, 1H BOS against trend | Only 1H structure broke | Do NOT flip short; interpret as noise; wait for 1H to re-establish bullish structure |
| Daily and 4H conflict | No clear bias | Reduce size to 0.5×; scalp only; no trend entries |
| Weekly bearish, Daily bullish bounce | Counter-trend bounce | Small long OK with target at next weekly resistance; no adds; no multi-day holds |
| All TFs conflict | No tradeable condition | **Do not trade; "When in doubt, stay out"** |

**Position sizing by conflict level:**
- 3+ TFs agree: Full size
- 2 TFs agree, 1 TF against: 0.75× size
- 1 TF only: 0.25× maximum, or skip

### 7.7 Confluence Zone Rules

**Minimum confluence for valid trade zone:**
- At least **1 Tier 1 factor** + **1 Tier 2 factor** clustering within 0.5–1% of price

**Tier 1 factors (highest weight):**
- Monthly/weekly swing high or low
- PDH/PDL when aligning with HTF level
- Weekly open or midpoint
- Daily FVG

**Tier 2 factors:**
- 4H OB or FVG
- Fibonacci 38.2%, 50%, or 61.8% of major swing
- 4H or daily EMA (21, 50, or 200)
- Previous day close

**Tier 3 (confirmation):**
- 1H swing high/low
- 1H FVG
- Session VWAP
- Round number psychological level

**Maximum confluence (monthly/weekly + 4H OB/FVG + Fibonacci + round number):** Occurs 1–3 times per month on any given asset; highest probability of strong reaction.

### 7.8 Session Windows for Crypto Top-Down Timing

| Session Window | UTC | Signal Quality |
|---|---|---|
| Asian (low vol) | 00:00–08:00 UTC | High false signal rate; mark levels, avoid entries |
| **London kill zone** | **08:00–12:00 UTC** | **Highest probability for 1H setups on crypto** |
| **London-NY overlap** | **12:00–16:00 UTC** | **Maximum liquidity; cleanest signals** |
| NY session | 13:00–17:00 UTC | Second confirmation window |
| Late session | 17:00–00:00 UTC | Lower conviction; end-of-day positioning |

**Monday note:** Don't set weekly bias from Sunday open. Set weekly bias from Tuesday/Wednesday action. Monday is statistically a liquidity sweep day 40% of the time.

**CME gap fill (historical note):** Prior to May 29, 2026, 77% of CME Bitcoin futures weekend gaps filled. CME now trades 24/7 — this pattern is obsolete for CME futures but Monday sweep tendency continues in spot markets.

### 7.9 ICT 7-Step Top-Down Protocol

1. **Monthly:** Multi-year trend + liquidity pool mapping
2. **Weekly:** Validate monthly trend; mark PWH/PWL; identify weekly reversal zones
3. **Daily:** Spot trend direction; mark daily OBs and FVGs; apply ICT Daily Bias Workflow
4. **4H:** Confirm bias; identify precise 4H entry zone; establish stop/TP framework
5. **1H/15M:** Pinpoint entry trigger; validate structure shift; set stop below LTF level
6. **Liquidity Mapping:** PDH/PDL, PWH/PWL, monthly opens, round numbers — all timeframes
7. **Fundamental Integration:** Check calendar; suspend MTFA logic during news releases; resume after initial spike + retracement

### 7.10 Key Numbers Reference

| Parameter | Value |
|---|---|
| Minimum TF alignment for trade | 2 TFs (64.7% WR) |
| Recommended minimum | 3 TFs (65–72% WR) |
| Win rate benefit: 4th TF vs. 3rd | +2% only (40% more complexity) |
| Structure confirmation minimum | 2 HH + 2 HL per timeframe |
| Trend EMA reference (universal) | 21-period EMA per timeframe |
| ADX trend threshold | >20 = trending; <20 = range |
| Monday weekly low probability | ~40% (BTC, Binance 2023 data) |
| Midnight Open (NY) in UTC | 05:00 UTC (04:00 UTC summer/EDT) |
| Crypto daily candle close | 00:00 UTC |
| Weekly candle close (crypto) | 23:59 UTC Sunday |

---

## SECTION 8: SUPPLY & DEMAND ZONE TRADING

*⏳ Research pending — agent a0e6a2ba6dd7f0084 completing*

---

## SECTION 9: ORDER BOOK / DOM / FOOTPRINT READING

### 9.1 Order Book Imbalance (OBI) — Core Formulas

**Standard Normalized OBI:**
```
OBI = (Total Bid Volume − Total Ask Volume) / (Total Bid Volume + Total Ask Volume)
```
Range: −1 to +1. Zero = balanced. +1 = all bids. −1 = all asks.

**Volume-Adjusted Mid Price (VAMP):**
```
VAMP = (Best Bid Price × Best Ask Qty + Best Ask Price × Best Bid Qty) / (Best Bid Qty + Best Ask Qty)
```
Superior to simple mid-price when queue sizes are asymmetric.

**Exponentially Weighted OBI (practical):**
Apply decay weights [1.00, 0.50, 0.25, 0.125, 0.0625] to top 5 price levels per side. Down-weights distant orders less likely to execute.

### 9.2 OBI Threshold Values

| OBI Value (Normalized) | Interpretation | Action Bias |
|---|---|---|
| +0.60 to +1.00 | Strong buy-side dominance | Bullish bias confirmed |
| +0.33 to +0.60 | Moderate buy-side lean | Watch for upside |
| −0.10 to +0.33 | Balanced / noise zone | No signal |
| −0.25 to −0.10 | Slight sell-side lean | Caution on longs |
| −1.00 to −0.25 | Strong sell-side dominance | Bearish bias confirmed |

**Actionable example:** ETH/USDT with 4,200 ETH bids vs. 1,100 ETH asks within 1% of price = 4:1 skew = OBI ~+0.60 = short-term bullish signal.

**Key calibrations:**
- High-volatility instruments: use 80–90% threshold to filter noise
- Minimum absolute size rule: a 70% skew on near-zero absolute volume does NOT fire as a signal
- Imbalance "lock" criterion: OBI remains above 65% for 30–60 consecutive seconds = confirmed directional signal
- Signal half-life: 5–30 seconds for raw OBI — use as entry timing tool, not standalone signal

### 9.3 Large Limit Order (Wall) Behavior

**Definition of significant wall:** Single order or cluster >=5x the median order size at that price level.

**Genuine support wall criteria (all should be present):**
1. **Persistence:** Wall holds as price approaches (does not disappear before contact)
2. **Partial fills:** Actual trade prints executing against it (visible in Bookmap as volume bubbles)
3. **Iceberg refilling:** Level replenishes to same or larger size after partial execution
4. **Absorption:** Price reaches the wall, volume spikes, price does NOT continue through
5. **Age:** Present for 10+ minutes; not freshly placed seconds ago
6. **Context:** Wall sits at a technically meaningful level (POC, round number, prior swing)

**Three documented price reactions to walls:**
1. **Hesitation/stall** — Order flow decelerates 2–5 ticks before contact; spread may widen slightly
2. **Reversal before contact** — Sophisticated traders front-run the wall before price physically reaches it
3. **Break-and-trap** — Price breaches the wall, attracts follow-through, then snaps back sharply (spoof scenario)

**Spoofing identification:**

| Indicator | Genuine Order | Spoofed Order |
|---|---|---|
| Persistence | Holds firm as price approaches | Disappears before price arrives |
| Volume execution | Generates trade prints | Zero trade prints despite price contact |
| Cancellation speed | Seconds/minutes | Sub-second (milliseconds) |
| Pattern | Organic sizing, varied price | Round numbers, VWAP, prior highs/lows |

**Documented spoof rate:** 31% of large orders on Coinbase BTC/ETH were potentially spoofed in December 2024 (arxiv.org, 2025).

**Iceberg detection:** Price repeatedly trades at same level; tape shows 15–23+ BTC executing without price clearing; identical lot sizes reappear after each partial fill; level refreshes within milliseconds.

### 9.4 Footprint Chart Analysis — Key Rules

**Format:** Each candle row shows `Bid Volume × Ask Volume` at each price level.

**Delta per candle** = Sum(Ask Volume − Bid Volume) across all rows.
- Positive delta = net aggressive buying dominated
- Negative delta = net aggressive selling dominated

**CVD (Cumulative Volume Delta)** = rolling sum of per-candle delta. Rising CVD = sustained buying pressure; falling = sustained selling.

**Footprint Imbalance — The 3:1 Rule:**
A price row is "imbalanced" when one side is **3x or more** the other:
- `200 × 800` → 4:1 ask-side = bullish imbalance (aggressive buyers lifting offers)
- `1,500 × 300` → 5:1 bid-side = bearish imbalance (aggressive sellers hitting bids)
- The 3:1 ratio is the industry-standard minimum threshold

**Stacked Imbalances:**
3 or more consecutive price rows within a single candle all showing imbalance in the same direction (each >=3:1):
- **Buying stacks** (3+ bullish rows) → zone acts as strong support on return; high-probability bounce
- **Selling stacks** (3+ bearish rows) → zone acts as strong resistance on return
- Entry: wait for price to retest the stacked imbalance zone; enter on first/second candle showing acceptance
- Stop: below the bottom of the stacked imbalance zone (for longs)

### 9.5 Absorption vs. Exhaustion Pattern

**Absorption** (institutional counterparty fighting aggressive flow):
- HIGH volume; both sides battling
- Net Taker Imbalance (NTI) near zero despite high volume
- Price refuses to advance despite sustained directional prints
- NTI < ±25% for 2+ consecutive minutes on 5M chart = absorption confirmed

**Exhaustion** (dominant side simply runs out of participants):
- LOW volume; dominant side disappears
- Print size shrinks dramatically at the extreme
- Near-empty footprint rows at candle high/low (1–2 contracts max at extreme)
- Single `1 × 0` or `0 × 1` cell at candle extreme = exhaustion confirmed

| Feature | Absorption | Exhaustion |
|---|---|---|
| Volume level | HIGH (both fighting) | LOW (dominant disappears) |
| NTI | Near zero | Collapses toward zero |
| Price behavior | Stalls despite aggression | Stalls as thin volume "taps" |
| Tape appearance | Sustained large prints | Print size shrinks dramatically |

### 9.6 Absorption Reversal Setup — Complete Steps

**Bearish absorption reversal at resistance:**
1. Price advances into structural resistance (VAH, POC, prior high, OB zone)
2. Tape shows sustained aggressive buy prints (green, large, fast)
3. Delta/CVD rising but price not advancing → absorption confirmed
4. Volume Z-Score elevated; NTI near zero for 2+ minutes
5. Footprint shows large ask-side numbers at high rows (passive sellers absorbing buyers)
6. Entry: short on close of absorption candle
7. Stop: above swing high where absorption occurred
8. Target: POC → VAL → next structural support

**Bullish absorption reversal at support:** Mirror logic.

### 9.7 Sweep and Reverse — Order Book Signature

**Before sweep:** Large limit order cluster at key level (retail stops visible).

**During sweep:** Burst of large directional prints on tape; price accelerates through level; spread blows out as market makers pull quotes; OI drops sharply (liquidations).

**Reversal signal:** Large bid wall appears BELOW sweep low (institutional absorbing stop liquidation flow); footprint shows immediate delta reversal at extreme; CVD bottom confirmed.

**Critical identifier:** Genuine breakdowns show disappearing bids + continued selling. Stop hunts show strong bids actively absorbing panicked orders even while price is at the low.

### 9.8 Volume Profile Confluence Rules

**Naked POC strategy:**
1. Identify Naked POC (not revisited since formation; ~80% revisited within 10 sessions)
2. Wait for price within 2–3% of Naked POC
3. OBI: heavy bid stacking at Naked POC confirms "magnet effect"
4. CVD: negative CVD bringing price to POC then CVD bottoms and reverses = bullish absorption
5. Enter long on first footprint candle showing buying imbalance AT the POC

**LVN breakout confirmation:**
Price accelerates through LVN + stacked imbalances in breakout direction + expanding volume = institutional participation confirmed.

**80% Rule OBI confirmation:**
Price enters Value Area from outside + OBI shows heavy imbalance in direction of traversal = high-conviction trade.

### 9.9 Order Flow Tools for Crypto

| Tool | Primary Feature | Crypto Exchanges |
|---|---|---|
| **Bookmap** | Time-based heatmap; iceberg detection; Multibook | Binance, Coinbase, Bitstamp |
| **Exocharts** | Crypto-native; real-time liquidation cascade visualization | Binance, Bybit, OKX, Bitget, Coinbase |
| **ATAS** | 400+ footprint variations; Smart Tape; 30-day heatmap | Binance, Bybit, OKX |
| **TradingLite** | Browser-based heatmap; crypto-native | Binance, Bybit |
| **Coinalyze** | OI, funding, liquidation aggregator; alerts | Multi-exchange |

**ATAS pricing:** Plus $24.95/month (2-day heatmap history); Pro $69.95/month (7-day heatmap).

### 9.10 Documented Edge Data (Order Flow)

**VPIN on BTC Perpetual Futures (26-month study 2024–2026):**
- Win rate: **63.6%**
- Net return: **+31.4 bps per trade** (after 28 bps transaction costs)
- Sharpe ratio: **0.88** (6-fold walk-forward)
- Max drawdown: **-12.2%**
- Critical decay: 2024: +82.3 bps gross → 2025: +38.5 bps → 2026 YTD: +12.4 bps (negative after costs)
- Bull months: +88.3 bps; Bear months: -5.9 bps

**Key caveats:**
1. All documented OFI edges are decaying year-over-year from HFT competition
2. Regime-dependent: bull markets significantly better than bear/sideways
3. For 1H setups: use OFI as confirmation tool only — latency requirements for standalone alpha require sub-100ms execution
4. 31% of large crypto orders potentially spoofed — raw book less reliable than CME futures

### 9.11 Signal Hierarchy for 1H Entry Timing

| Signal | Reliability | Timeframe | Threshold |
|---|---|---|---|
| Stacked imbalances (3+ rows at 3:1+) | HIGH | 5M–15M candle | 3 consecutive rows, >=3:1 |
| Absorption reversal | HIGH | 5M–15M | High Vol Z-Score + NTI <±25% |
| Delta divergence | HIGH | 1M–15M | Price extreme + CVD non-confirmation |
| OBI at structural level | MEDIUM-HIGH | Real-time | OBI >=0.60 or <=-0.60 at level |
| Wall holding with absorption | MEDIUM | 1M–5M | Persists, generates fills, iceberg refill |
| Naked POC OBI confluence | HIGH | 1H–4H structure | OBI bid-heavy at Naked POC |
| Liquidation cluster sweep | HIGH | 1M sweep | Yellow cluster cleared, CVD reversing |

---

## SECTION 10: LIQUIDITY ENGINEERING / STOP HUNT PATTERNS

### 10.1 The Classic "Run Stops, Reverse" — Three-Phase Framework

All institutional stop hunts follow this sequence:

**Phase 1 — Accumulation/Range Formation:** Price coils between two defined boundaries. Market makers accumulate while appearing directionally neutral. Equal highs form above, equal lows form below.

**Phase 2 — The Hunt:** Price is driven aggressively beyond a visible swing high or low where retail stops cluster. The triggered stop orders (forced market orders) provide the institutional counterparty to fill large positions in the opposite direction.

**Phase 3 — The Reversal:** Price reverses sharply. Characterized by: (a) wick-only extension with body closing back inside prior range, (b) rapid Market Structure Shift on lower timeframes, (c) displacement in the reversal direction.

**Critical candle-close rule:** Wick through a level + body closes back inside = stop hunt. Candle closes beyond the level = genuine structural break.

### 10.2 Where Retail Stops Cluster (Prime Hunt Zones)

1. **Above swing highs / below swing lows** — primary structure-based stops
2. **Round numbers** — prices ending in .00, .50, psychological levels (e.g., BTC $100,000); over 70% of traders cluster orders at round numbers
3. **Just beyond obvious S/R lines** — trendlines, Fibonacci levels, VWAP, pivot points
4. **Below double-bottoms / above double-tops** — creates densest clusters (both original swing traders AND double-top/bottom traders park stops at same level)

**Osler (2005) academic confirmation:** 9,655 stop-loss orders totaling $55 billion across USD/JPY, USD/GBP, EUR/USD. Finding: "Exchange rate trends are unusually rapid when rates reach levels where stop-loss orders cluster." Stop-loss cascade response is **larger and longer-lasting** than take-profit order response. Clusters at round numbers (big figures) confirmed empirically.

### 10.3 Equal Highs / Equal Lows — Prime Sweep Targets

**The rule:** Equal highs and equal lows are NOT support/resistance — they are **TARGET ZONES** for institutional sweeps. Never trade the double top short without waiting for the sweep first.

**Why:** Price tests a level twice, fails both times. All traders who shorted the double top + all traders long between the double bottom placed stops at the same level. One sweep triggers all of them simultaneously.

**ICT definition:** A "relative equal high" = a high with a lower swing high on its right side (failed breakout + liquidity cluster above).

**Equal high/low sweep mechanics:**
1. Price approaches with momentum
2. Breaks through briefly — taking all resting stops
3. Immediately reverses — stop-triggered orders exhausted, no more unidirectional fuel
4. Reversal is sharp precisely because all forced pressure is now spent

### 10.4 Stop Hunt Distance Rules

| Instrument | Sweep Extension | Rule |
|---|---|---|
| Forex major pairs | 5–20 pips beyond level | ICT: "10–20 pips beyond sweep wick" |
| Crypto (BTC/ETH) | 0.5–2% beyond level | ATR-proportional |
| Futures/Indices | 1–5 ticks / 0.1–0.3 ATR | Documented range |
| Asian Range (FXNX) | 8 pips below on ~30 pip range | Specific documented example |

**ATR-based rule:** Sweep extending more than **0.5 ATR (daily)** beyond a level that holds for 3+ entry-TF candles = increasingly likely genuine breakout, not stop hunt.

**Turtle Soup (Raschke/Connors) specifics:**
- Entry: **5–10 ticks above** prior 20-day low (for longs)
- Stop: **1–2 ticks below** today's low
- Prior 20-day low must be **at least 4 days old** (not yesterday's low)

### 10.5 Session-Based Stop Hunt Timing

| Window | ET Time | Type |
|---|---|---|
| Judas Swing primary | 00:00–05:00 AM (peak 03:00–05:00 AM) | Pre-London/London Open sweep |
| London Kill Zone | 02:00–05:00 AM | Highest institutional activity |
| NY manipulation window | **08:30–09:30 AM** | False breakout before real move |
| NY Open initial spike | 09:30–10:00 AM | Often false — first reaction |
| Silver Bullet AM | 10:00–11:00 AM | **Real move begins AFTER 08:30–09:30 manipulation** |
| Silver Bullet PM | 02:00–03:00 PM | Afternoon continuation/reversal |

**Universal rule:** "Do not trade the first breakout — let the first 15–30 minutes of any session develop. This is the manipulation phase, not the direction."

### 10.6 The London Judas Swing — Complete Protocol

1. Determine daily bias (bullish/bearish) before session opens
2. Mark: Asian High, Asian Low, NY Midnight Open (00:00 AM NY = 05:00 UTC)
3. During 00:00–05:00 AM NY: wait for sharp move **AGAINST** daily bias
   - Bullish bias day: Judas = fake bearish spike below Asian Low
   - Bearish bias day: Judas = fake bullish spike above Asian High
4. Price returns back through 00:00 NY open price
5. 5M Market Structure Shift confirms reversal in direction of daily bias
6. Enter on retest of 5M FVG or OB created by MSS displacement
7. **Stop:** 10–20 pips beyond the Judas Swing wick
8. **Target:** Prior day high (bullish) or prior day low (bearish)

**Optimal Asian Range size:** Under 40 pips; ranges above 80 pips show lower probability sweeps.

### 10.7 False Breakout — Exact Rules

**True breakout vs. false breakout:**

| Condition | True Breakout | False Breakout |
|---|---|---|
| Breakout candle volume | >150% of 20-period average | <50% of average |
| Wick behavior | Small wick, large body | Large wick, small body |
| Follow-through | Second candle confirms | Reversal within 1–3 candles |
| CVD alignment | CVD expands with break | CVD diverges; buying exhausted |
| First pullback volume | Falls to <50% of breakout | May spike on reversal |

**CVD divergence signals:**
- Bearish fake: Price higher high + CVD lower high or stalls = buyer exhaustion
- Bullish fake: Price lower low + CVD higher low = seller exhaustion

**Breakout statistics (CrackingMarkets.com, 40 futures markets, 40,000+ trades):**
- 1-hour hold: Sharpe **1.59** (profitable edge)
- 10-hour hold: Sharpe **1.55** (edge holds short-term)
- **2-day hold: Sharpe 0.21** (near-random — momentum dissipates within hours)
- Implication: ~60–80% of breakouts fail to reach meaningful targets; breakout strategies win only 20–40% but use asymmetric payoffs

### 10.8 AMD Cycle — Accumulation-Manipulation-Distribution

**Phase 1 — Consolidation:** Price ranges; volatility compresses; ATR shrinks; volume decreasing.

**Phase 2 — False Breakout (Manipulation):**
- Aggressively breaks range boundary on one side
- Volume on false break is BELOW 20-period average
- Breakout candle has large wick in break direction
- Fails to close second candle beyond boundary

**Phase 3 — Real Move:**
- Price reverses through OPPOSITE boundary
- Fueled by: (a) trapped traders exiting at loss, (b) smart money positioned for real direction
- MSS back through range within 1–5 candles

### 10.9 ICT/SMC Pattern Exact Rules

**CHoCH (Change of Character):**
- Bullish CHoCH: In downtrend (LL/LH), price candle BODY closes above most recent lower high = first higher high
- Bearish CHoCH: In uptrend (HH/HL), price candle BODY closes below most recent higher low = first lower low
- **MUST be candle body close** — wick-only = stop hunt, NOT CHoCH

**BOS (Break of Structure):** Break in SAME direction as prior trend = continuation. Genuine BOS is preceded by inducement sweep + displacement candle.

**Inducement (IDM) — Critical filter:**
- First valid pullback inside the impulse leg reaching >=0.5 Fibonacci (with wick confirmation)
- Mark the high/low of this first pullback as the IDM level
- **Do NOT enter until IDM is swept first** — entering before IDM is swept = trading into a trap
- In uptrends: wait for dip below IDM low before entering long
- In downtrends: wait for spike above IDM high before entering short

**Breaker Block:**
- Order block that was swept with liquidity then reversed = higher probability
- Price returns as confirmation zone for the new direction

**Mitigation Block:**
- Broken order block (failed without sweeping liquidity) = smart money returns to close unfilled orders
- Continuation pattern; lower probability than Breaker Block

### 10.10 PVSRA Volume Signatures of Manipulation

**Climax candles (Institutional Activity):**
- Volume >=2x the 10-bar average, OR Volume x spread >= highest effort value in last 10 bars

**Absorption candles (Stop Hunt Confirmation):**
- Climax-level volume (>=2x average)
- **Spread <50% of average spread**
- Massive volume transacted but price barely moved
- This is the **definitive volume signature of a stop hunt completing**

**PVSRA color coding:**
- Climax UP (high vol, wide spread, bullish): Blue/green = institutional buying
- Climax DOWN (high vol, wide spread, bearish): Red = institutional selling
- **Absorption UP (high vol, narrow spread, closes up): Aqua = absorbing sell stops** ← highest-quality bullish reversal signal
- **Absorption DOWN (high vol, narrow spread, closes down): Fuchsia = absorbing buy stops** ← highest-quality bearish reversal signal

### 10.11 Post-Sweep Entry Protocol

**Required pre-conditions:**
1. Higher-TF structural bias confirmed (daily/4H)
2. Visible liquidity pool swept (equal high/low, swing extreme, round number)
3. Sweep was wick-only (body closed back inside) OR reversed sharply within 1–3 candles
4. Inducement level has been swept

**Minimum one confirmation:**
1. MSS on lower TF (5M/1M): protected swing point broken with candle close in reversal direction
2. FVG created by MSS displacement (becomes entry zone)
3. SMT Divergence: correlated pair does NOT sweep the same level

**Entry execution:**
- Enter on RETEST of FVG or OB created by MSS displacement (NOT at the swept level itself)
- NOT during the displacement spike (slippage too high)

**Stop-loss:**
- Below swept low (longs) / above swept high (shorts)
- Buffer: 10–20 pips Forex; 0.1–0.2 ATR crypto
- Stops go BEYOND the entire sweep wick, not at the swept level

**Targets:** TP1 = internal liquidity (equal highs/lows); TP2 = prior day high/low; TP3 = weekly extreme. Minimum R:R: 2:1 (3:1 preferred).

### 10.12 Key Numeric Thresholds Reference

| Metric | Value | Source |
|---|---|---|
| Judas Swing stop buffer | 10–20 pips beyond sweep wick | ICT |
| Market Maker Model stop | 10–20 pips beyond last swing before MSS | ICT MMBM/MMSM |
| Silver Bullet min target (Forex) | 15 pips | ICT |
| Silver Bullet min R:R | 1:3 | ICT 2022 Model |
| Asian Range optimal width | <40 pips; >80 pips = reduced probability | ICT/FXNX |
| Documented sweep depth (Asian Low) | 8 pips on ~30 pip range | FXNX |
| Turtle Soup entry | 5–10 ticks above prior 20-day low | Raschke/Connors |
| Turtle Soup lookback rule | Prior low >=4 days old | Raschke/Connors |
| True breakout volume | >150% of 20-period average | LuxAlgo |
| False breakout warning | <50% of average at break | LuxAlgo |
| PVSRA climax volume | >=2x 10-bar average | PVSRA |
| PVSRA absorption (stop hunt) | Climax vol + spread <50% average | PVSRA |
| IDM Fibonacci requirement | Pullback >=0.5 Fib of impulse | ICT |
| Breakout momentum decay | Sharpe 0.21 at 2-day hold (near random) | CrackingMarkets.com |
| Retail stop cluster density | >70% at round numbers | Osler 2005 + practitioners |
| Spoofed large orders (crypto) | ~31% of large orders | arxiv.org 2025 study |
| Session manipulation window | First 15–30 min of any session open | Universal SMC rule |

---

## VOLUME 10 MASTER PRE-TRADE CHECKLIST

### 12-Point ICT/BTMM/Wyckoff/Harmonic Unified Checklist

Before any 1H entry, verify:

**Bias Layer (from highest TF):**
- [ ] 1. Daily trend direction confirmed (HH/HL series; price above/below MO and 50 EMA)
- [ ] 2. 4H structure agrees with daily bias (or 4H is at a valid pullback level within the daily trend)
- [ ] 3. 1H market structure shift (CHOCH or BOS in bias direction) has occurred

**Zone Layer:**
- [ ] 4. Price is AT a valid HTF key level (daily FVG, 4H OB, 4H demand zone, weekly pivot) — NOT between levels
- [ ] 5. Minimum 2-tier confluence at the zone (Tier 1 + Tier 2 factors within 0.5–1% of price)
- [ ] 6. Liquidity sweep confirmed (BSL or SSL already swept before entry — stop hunt complete)

**Execution Layer:**
- [ ] 7. 15M/5M confirmation signal present (BOS, pin bar, engulfing, or FVG rejection)
- [ ] 8. RSI divergence or MACD divergence at the zone (ideally both)
- [ ] 9. Session timing is valid (London or NY window — avoid pure Asian session entries)

**Risk Layer:**
- [ ] 10. R:R calculated ≥ 2:1 (minimum); if reversal setup, ≥ 3:1
- [ ] 11. Funding rate checked (below 0.04% per 8H for longs; below −0.04% for shorts or exit)
- [ ] 12. Position sized correctly (ATR-adjusted, drawdown tier considered, correlation-adjusted if multiple positions)

**Score:** 10–12 = full size (1% risk); 8–9 = reduced size (0.75%); 7 = marginal (0.5%); <7 = skip

---

## VOLUME 10 SCORING TABLE — COMBINED CONFLUENCE SYSTEM

| Category | Signal | Weight | Notes |
|---|---|---|---|
| Wyckoff Phase | Phase D / BUYLPS or Phase D / LPSY | +3 | Highest probability Wyckoff entries |
| Harmonic PRZ | Valid PRZ (2+ Fibonacci cluster, ±3% tolerance) | +2 | Reduce to +1 if PRZ is wide |
| Harmonic PRZ | GBB Auto-Validator score ≥ 7/10 | +1 additional | Bonus for tight PRZ |
| ICT Structure | Market Maker Model step completion (step 4-5 of 7) | +2 | Buy/Sell model at OTE zone |
| BTMM Confirmation | All 5 BTMM checks green | +2 | TDI confirms + session valid |
| MTFA Alignment | 3+ TFs aligned | +3 | Maximum; reduce to +2 for 2 TF, +1 for 1 TF |
| OTE Zone | Entry within 0.62–0.79 Fibonacci zone | +1 | Sweet spot 0.705 |
| Killzone | Entry during London or NY killzone | +1 | Highest-probability execution windows |
| RSI Divergence | Confirmed at entry zone | +1 | Bullish or bearish divergence at D/Spring/OTE |
| Volume Signal | Spring on climax volume (Wyckoff) or PVSRA vector candle | +1 | Wyckoff SC/Spring or PVSRA climax |
| Funding Rate | Neutral or favorable | +1 | <0.02% = favorable; >0.04% = unfavorable (subtract) |
| Liquidity Sweep | Prior stop hunt confirmed | +1 | BSL/SSL already cleared before entry |

**Scoring thresholds:**
- **12–15 points:** Maximum conviction — A+ setup (1.5% risk, full pyramid scaling authorized)
- **9–11 points:** High conviction — A setup (1.0% risk, standard management)
- **6–8 points:** Moderate conviction — B setup (0.75% risk, TP1 closer)
- **3–5 points:** Low conviction — C setup (0.5% risk, mechanical only)
- **<3 points:** Skip trade

---

*Volume 10 Sections 8–10 will be added upon completion of remaining research agents.*  
*TR Masterclass psychology section (agent a0edcee280116cf83) will be incorporated as a supplementary section upon completion.*
