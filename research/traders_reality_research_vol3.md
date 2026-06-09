# Traders Reality / Hybrid System — Research Volume 3
# Advanced Confluences, Market Mechanics & Execution Framework
# Branch: claude/crypto-confluences-research-cxrtp3
# Date: 2026-06-08
# Covers: 9 deep-research topics compiled from parallel research agents

---

## TABLE OF CONTENTS

1. SMT Divergence, Dealing Range, OTE & CISD
2. Crypto-Specific Market Mechanics (Funding, OI, Liquidations, BTC.D)
3. Advanced ICT Price Delivery Structures (Breaker, Mitigation, Displacement, Propulsion, Void)
4. Complete Fibonacci Framework (OTE, Golden Pocket, SD Projections)
5. Market Seasonality & Cyclicality (Halving, Quarterly, Monthly, Day-of-Week)
6. Advanced ICT Models (Silver Bullet, IPDA, Daily Bias, DOL, Turtle Soup)
7. VWAP, Volume Profile & Market Profile
8. Order Book Analysis, CVD & On-Chain Data
9. Prop Firm Rules — Session-Based Trading (FTMO, TopStep, Apex)

---

## SECTION 1: SMT DIVERGENCE, DEALING RANGE, OTE & CISD

### 1.1 SMT Divergence (Smart Money Technique / Synthetic Divergence)

SMT Divergence occurs when two correlated instruments (BTC vs ETH, or ES vs NQ) form **opposing price structures** at the same PD Array (Point of Divergence). This signals that one leg is a manipulation sweep while the other confirms genuine direction.

**Core Rule:** BTC makes a new high but ETH makes a lower high at the same timeframe = bearish SMT. BTC fails to make a lower low but ETH makes a lower low = bullish SMT. The asset that FAILS to make the correlated extreme is revealing the true institutional intent.

**SMT Entry Rules:**
- Only valid at a known PD Array level (Order Block, Fair Value Gap, previous session high/low, liquidity pool)
- Requires same-timeframe structure — do not compare HTF on one asset to LTF on another
- Entry triggers on the asset that SHOWED the divergence (the one that didn't sweep)
- Best timeframes: 1H/4H for identification; 15M/5M for entry
- Invalidation: if BOTH assets ultimately break the extreme, the divergence failed — exit immediately

**BTC vs ETH Session Rules:**
- At NY open (07:00–10:00 AM EST), run SMT check FIRST before any entry
- BTC.D rising at NY open → BTC outperforming → trade BTC longs / ETH shorts
- BTC.D falling at NY open → alts outperforming → trade ETH/alt longs
- SMT divergence at Asian session high/low = highest-probability setup for London kill zone

**Confirmation Checklist:**
1. Price at PD Array (OB, FVG, liquidity pool)
2. One asset sweeps the extreme; the other does not
3. CISD or MSS fires on the diverging asset
4. Volume expansion on the diverging candle
5. Session kill zone active (London 02:00–05:00 AM EST or NY 07:00–10:00 AM EST)

---

### 1.2 ICT Dealing Range (Premium vs Discount)

The Dealing Range is defined between any two significant swing points (typically a weekly or daily high and low). The 50% midpoint (equilibrium) divides the range into:

- **Premium (above 50%):** Only take SHORT trades. Longs taken in premium are fighting institutional order flow.
- **Discount (below 50%):** Only take LONG trades. Shorts taken in discount are fighting institutional order flow.
- **Equilibrium (50%):** Neutral zone — avoid unless a strong PD Array coincides here.

**Application Rules:**
- Identify the Dealing Range on the WEEKLY chart first for macro bias
- Confirm on the DAILY chart for session bias
- Use the H4/H1 Dealing Range for intraday entry precision
- A trade at the 62%, 70.5%, or 79% retracement (in discount for longs, in premium for shorts) = OTE (Optimal Trade Entry)
- Premium/Discount changes when a higher high or lower low is formed — recalculate after every BOS

**CISD — Change in State of Delivery:**
CISD is the FIRST signal that delivery has shifted direction — it fires BEFORE MSS (Market Structure Shift).

- **Definition:** A candle BODY closes PAST the opening price of the delivery candle (the candle that initiated the prior leg)
- Does NOT require a swing high/low to be broken
- Fires earlier = allows earlier entry with tighter stop

**MSS — Market Structure Shift:**
- Definition: Price closes PAST a prior structural swing high (bullish MSS) or swing low (bearish MSS)
- Fires AFTER CISD — later entry, wider stop, but more confirmation
- MSS + FVG left behind = highest-probability reversal entry

**CISD vs MSS Priority:**
```
CISD fires → aggressive entry, tight stop below/above delivery candle low/high
↓ (if CISD fails)
MSS fires → conservative entry, stop below/above the structural swing that was broken
```

---

### 1.3 OTE — Optimal Trade Entry (Fibonacci)

OTE is the ICT-defined high-probability retracement zone for entry after a BOS or MSS.

**Levels:**
- 62% retracement: Conservative entry zone
- **70.5% retracement: Primary OTE (the "sweet spot")**
- 79% retracement: Final entry zone before invalidation

**How to Draw OTE:**
- For LONG setups: Draw Fibonacci from the most recent swing LOW to the most recent swing HIGH (post-BOS)
  - 62–79% retracement = OTE zone for long entries
  - Stop: below the swing LOW
  - Target: the swing HIGH (100%), then 127.2% and 161.8% extensions

- For SHORT setups: Draw Fibonacci from most recent swing HIGH to swing LOW
  - 62–79% retracement (measured from the HIGH) = OTE zone for short entries
  - Stop: above the swing HIGH
  - Target: swing LOW (100%), then 127.2% and 161.8% extensions

**OTE + Session Rules:**
- OTE during London kill zone = most reliable (price routinely retraces to OTE after the Judas Swing)
- OTE + Order Block alignment = highest-confluence entry
- OTE during dead zones (12:00–2:00 PM EST, Asian session for non-Asian pairs) = skip
- Never enter OTE without confirming the BROADER dealing range supports the direction (discount for longs, premium for shorts)

---

## SECTION 2: CRYPTO MARKET MECHANICS (FUNDING, OI, LIQUIDATIONS, BTC.D)

### 2.1 Funding Rates

Perpetual futures contracts use a funding rate mechanism to keep the perpetual price anchored to spot. Funding is paid/received every 8 hours.

**Exchange Reset Times (UTC):**
- Binance, Bybit, OKX: 00:00 UTC / 08:00 UTC / 16:00 UTC
- The 00:00 UTC (midnight UTC) reset overlaps with the Asian session open
- The 08:00 UTC reset overlaps with the London open
- The 16:00 UTC reset overlaps with the NY close

**Actionable Thresholds:**

| Funding Rate / 8h | Annualized | Signal | Action |
|---|---|---|---|
| > +0.10% | > +109% APR | Extreme overheating (longs) | Strong bearish signal — avoid new longs; watch for manipulation sweep down |
| +0.05% to +0.10% | +55–109% APR | Overheated longs | Caution; sustained 3+ days = 5–15% pullback likely within 24–72h |
| +0.01% to +0.05% | +11–55% APR | Moderate bullish | Normal bull market carry |
| -0.01% to +0.01% | ~0% | Neutral | No funding signal — read CVD and OI instead |
| -0.01% to -0.05% | -11 to -55% APR | Moderate bearish | Short squeeze risk builds |
| < -0.03% | < -33% APR | Excessive shorts | Historically preceded every major Bitcoin relief rally |
| < -0.10% | < -109% APR | Extreme negative | Strong bullish contrarian signal — forced short covering imminent |

**Session Direction Rules:**
- Positive funding entering London/NY open + rising price = longs crowded → manipulation LIKELY to sweep DOWN first (Judas Swing down) before real move up
- Negative funding + price at strong support + NY open = short squeeze environment → violent upside
- Neutral funding = no funding edge; rely on CVD + OI

---

### 2.2 Open Interest (OI)

**OI + Price Matrix:**

| OI | Price | Signal |
|---|---|---|
| Rising | Rising | Fresh longs entering — trend continuation (SAFEST to hold) |
| Rising | Falling | Fresh shorts entering — bearish continuation; long squeeze risk |
| Falling | Rising | Short covering — weak rally; fade near resistance |
| Falling | Falling | Long liquidations exhausting — trend nearing end; watch for reversal |

**Session-Specific OI Rules:**
- **Pre-NY (06:00–08:00 AM EST):** CME futures open at 08:00 AM EST. OI change in this window = institutional pre-positioning
- **8:00 AM EST CME open:** OI spike + price stability = institutional hedging (neutral signal)
- **9:30 AM EST NYSE open:** Rising OI + positive funding = expect manipulation sweep DOWN first, then real move up
- **3–7 day sustained rising OI + bearish positioning near resistance** = historically precedes major short squeezes
- CME data is delayed — use Binance/Bybit/Coinglass for real-time OI
- Rising OI + CVD flat or negative = defensive/bearish positioning, not bullish conviction

---

### 2.3 Liquidation Heatmap (Coinglass)

**Color System:**

| Color | Density | Implication |
|---|---|---|
| Bright Yellow / White | Maximum | Critical magnet zones — primary price targets for stop hunts |
| Orange | High | Significant volatility expected |
| Green | Moderate | Minor reactions |
| Purple / Dark Blue | Very low | "Liquidity gap" — price moves through rapidly |

**Key Rules:**
- Yellow zones within **2–3% of current price** = ~70% probability price tests that level within 24 hours
- Yellow zone swept = magnet effect disappears → price often reverses sharply (sweep-and-reverse entry pattern)
- **Stop placement rule:** Place stops on the "dark side" of a cluster (beyond it), NEVER inside a yellow zone
- Use **Model 1** (10x–100x leverage only) for session-based Brinks Box setups
- Cross-reference Binance + Bybit + OKX — zones visible on multiple exchanges are more reliable

**Pre-Session Heatmap Procedure (30 min before London or NY open):**
1. Open Coinglass Liquidation Heatmap — 12-hour or 24-hour view, Model 1
2. Mark nearest yellow zone ABOVE current price = short liquidation cluster = upside stop hunt target
3. Mark nearest yellow zone BELOW current price = long liquidation cluster = downside stop hunt target
4. The Brinks Box stop hunt will target the nearest yellow zone in the direction of the manipulation
5. Determine bias with funding + OI: crowded longs (positive funding + rising OI) = stop hunt goes DOWN first

**$2.56 billion real example (early 2026):** Dense long-liquidation clusters between $60,000–$70,000 were visible on the heatmap for weeks before price cascaded through them in the early-2026 crash.

---

### 2.4 BTC Dominance (BTC.D) Rules

BTC.D measures Bitcoin's share of total crypto market cap.

**19 BTC.D Intraday Rules at NY Open:**

1. BTC.D > 55% and rising = Bitcoin-heavy market; avoid altcoin longs
2. BTC.D < 45% and falling = altseason conditions; altcoin longs preferred over BTC
3. BTC.D rising at NY open with BTC falling = capital rotating OUT of alts INTO BTC (risk-off)
4. BTC.D falling at NY open with BTC rising = broad altcoin participation; healthy bull
5. BTC.D rising + BTC falling = aggressive capital flight to stables; AVOID all longs
6. BTC.D spike +1% in 1 hour at NY open = institutional BTC buying; ETH/alts lagging is expected
7. BTC.D falling + BTC stagnant = altcoin pump rotation; trade alts not BTC
8. SMT divergence between BTC and ETH confirmed by BTC.D direction = highest-conviction signal
9. BTC.D at 50% = equilibrium; no directional bias from dominance alone
10. BTC.D breaking above prior weekly high = Bitcoin dominance trend confirmed; rotate to BTC
11. BTC.D breaking below prior weekly low = alt season confirmed; rotate to ETH/alts
12. BTC.D consolidating (flat for 24h+) = wait for breakout before using dominance as filter
13. During NY kill zone: check BTC.D 15-min chart for acceleration
14. Rising BTC.D + falling BTC price = extreme fear, potential capitulation bottom
15. Rising BTC.D + rising BTC price = Bitcoin bull run; alts underperform
16. Falling BTC.D + falling BTC price = broad market crash; avoid all longs
17. Falling BTC.D + rising BTC price = altcoin rotation cycle; rotate to ETH first, then mid-caps
18. BTC.D gap up at open = whales accumulating BTC; near-term bearish for alts
19. BTC.D gap down at open = early alt season signal; ETH leads first 24–48 hours

---

### 2.5 Exchange Flow Data (On-Chain)

**Core Logic:**
- Exchange Inflow spike = coins moving TO exchanges = preparation to sell = BEARISH
- Exchange Outflow spike = coins moving FROM exchanges = self-custody = BULLISH (supply squeeze)
- Netflow = Inflow − Outflow: Positive = bearish pressure; Negative = supply leaving (bullish)

**Actionable Thresholds:**

| Metric | Threshold | Signal |
|---|---|---|
| Single-day BTC exchange inflow | > 30,000 BTC | Historically preceded avg 5.2% drawdown within one week |
| Whale deposits (48h window) | Any large spike | Preceded 3%+ price drops in 65% of cases within 48h |
| Exchange Whale Ratio | > 0.6 | 60%+ of BTC inflows from top-10 wallets; elevated selling risk |
| Exchange Whale Ratio | > 0.85 | Extreme whale concentration; highest near-term selling risk |
| BTC on exchanges | < 12% of supply | Long-term bullish supply squeeze (early 2026 level vs 17% in 2023) |
| Stablecoin inflows | < $50M/day net | Reduced buying power; limits upside |

**Session Reading:**
- Use 7-day MA of inflows — single-day spikes are noise
- Low mean transaction size + high total inflows = retail panic selling (less sustained)
- High mean transaction size = institutional/whale selling (more sustained, multi-session impact)
- Falling stablecoin inflows + rising BTC inflows = dual bearish pressure for the session

---

## SECTION 3: ADVANCED ICT PRICE DELIVERY STRUCTURES

### 3.1 Breaker Block

A Breaker Block is a **failed Order Block** — an OB that was invalidated by price breaking through it with a liquidity sweep, then REVERSING. It now flips polarity: an old bullish OB becomes bearish, and vice versa.

**Formation Rules:**
- A bullish OB at a prior low was swept (price broke below the OB low)
- Price then reverses back UP through the OB
- The OB now acts as **resistance** on the first retest from below
- Valid for **ONE retest only** — after the first retest, the Breaker Block is consumed

**Entry Rules:**
- Short: Enter on the FIRST retest of the former bullish OB from below
- Stop: Above the body high of the Breaker Block candle
- Target: Next SSL (sell-side liquidity) or HVN below
- Long: Enter on FIRST retest of the former bearish OB from above (now bullish Breaker)
- Invalid if: price closes ABOVE the Breaker Block on the retest (not just a wick — body close)

---

### 3.2 Mitigation Block

A Mitigation Block is an **old Order Block that price returns to in the SAME direction** — no liquidity sweep required. It represents unfinished institutional order flow.

**Formation Rules:**
- Bullish OB established at a swing low
- Price rallied away, leaving the OB untested
- Price returns to retest the OB FROM ABOVE (same direction as original move)
- Entry: Long on the retest of the OB body (between the open and close of the OB candle)
- Stop: Below the OB candle low
- No liquidity sweep required (distinguishes it from Breaker Block)

**Mitigation vs Breaker:**
| | Mitigation Block | Breaker Block |
|---|---|---|
| Price swept the OB? | No | Yes |
| Direction of setup | Continuation (same direction) | Reversal (opposite direction) |
| How many times valid? | Multiple retests possible | ONE retest only |
| Entry style | At OB body on pullback | At OB body on first return after sweep |

---

### 3.3 Displacement

Displacement is the confirmation that institutional order flow is driving a move — not retail.

**Definition:**
- Minimum **3 consecutive same-direction large-body candles** with minimal wicks
- Must leave a **Fair Value Gap (FVG)** — a gap between the prior candle's high/low and the next candle's low/high
- All 3 candles must close above their midpoints (bullish displacement) or below (bearish)

**Displacement Rules:**
- Displacement after a liquidity sweep = highest probability setup (confirms manipulation is done)
- FVG left by displacement = pending price return target (50% fill = Consequent Encroachment minimum)
- Displacement on H1 or H4 = swing trade significance
- Displacement on 15M or 5M = intraday significance
- Without displacement, there is NO institutional confirmation of direction

**Displacement + Session Rules:**
- London kill zone displacement (after Asian range stop hunt) = primary Hybrid System entry trigger
- NY open displacement (after London high/low is swept in London-NY overlap) = institutional NY entry

---

### 3.4 Propulsion Block

A Propulsion Block is a single **ignition candle** found INSIDE an Order Block — the specific candle that launched price away from the OB.

**Entry Rules:**
- Mark the single candle that initiated the move from an OB
- Entry at **50% (Mean Threshold)** of that propulsion candle's body
- Stop: Below the full propulsion candle low (for longs) or above for shorts
- This is a more precise entry than the full OB range

**Why 50%:**
- Institutions execute at the equilibrium of their entry candle
- Price often returns to exactly 50% of the propulsion candle before continuing
- The 50% level = Consequent Encroachment of the propulsion candle body

---

### 3.5 Liquidity Void

A Liquidity Void is formed by **2 or more stacked Fair Value Gaps** — price moved so fast that multiple consecutive gaps were left unfilled.

**Rules:**
- Minimum: 2 consecutive FVGs with no overlap
- Price will fill to at least **50% of the total void** (Consequent Encroachment of the full void)
- Often fills completely before resuming
- Acts as a high-probability return target when price is trading far from the void
- Do NOT enter inside a Liquidity Void — wait for price to exit the void and show reversal

**Void vs FVG:**
| | Single FVG | Liquidity Void |
|---|---|---|
| Number of gaps | 1 | 2+ stacked |
| Fill expectation | 50% (CE) minimum | 50% of total void minimum |
| Price behavior inside | Slows, may reverse | Moves rapidly through |
| Entry location | At FVG boundary | After price exits the void |

---

## SECTION 4: COMPLETE FIBONACCI FRAMEWORK

### 4.1 TradingView Fibonacci Configuration

**Standard Levels to Enable:**
```
0       = Swing origin
0.236   = Minor pullback
0.382   = Shallow retracement  
0.5     = Equilibrium / 50% mean
0.618   = Golden Pocket start
0.65    = (optional midpoint)
0.705   = OTE primary level (the sweet spot)
0.786   = OTE deep level
0.886   = Very deep retracement (still valid if OB present)
1.0     = Full retracement / origin
-0.27   = Extension target 1 (127.2%) = T2
-0.618  = Extension target 2 (161.8%) = T3
-1.0    = Extension target 3 (200%)
```

**Colors:**
- OTE zone (0.62–0.79): Yellow or orange highlight
- Golden Pocket (0.618–0.65): Blue
- Extension targets: Red levels

---

### 4.2 OTE (Optimal Trade Entry) Rules

**Anchoring Rules:**
- After a BULLISH BOS (price breaks above a swing high): Draw Fib from the LAST SWING LOW to the SWING HIGH (the broken high)
  - Long entry zone: 62–79% retracement
  - 70.5% = primary target price in zone
  - Stop: Below the swing low (origin point)

- After a BEARISH BOS (price breaks below a swing low): Draw Fib from LAST SWING HIGH to the SWING LOW (the broken low)
  - Short entry zone: 62–79% retracement (measured FROM the high)
  - 70.5% = primary entry
  - Stop: Above the swing high

**OTE + Kill Zone Rule:**
- OTE entered during London Kill Zone (02:00–05:00 AM EST) = A+ setup
- OTE entered during NY Kill Zone (07:00–10:00 AM EST) = A+ setup
- OTE entered during Dead Zone (12:00–2:00 PM EST) = SKIP
- OTE entered against the Weekly Dealing Range direction = SKIP (e.g., don't take OTE long in premium zone)

**OTE Targets:**
- T1: 100% (return to the swing high/low that was broken — the BOS origin)
- T2: 127.2% extension (labeled -0.27 in TradingView)
- T3: 161.8% extension (labeled -0.618 in TradingView) — primary swing target

---

### 4.3 Golden Pocket (0.618–0.65)

The Golden Pocket is the strongest retracement confluence zone:
- **0.618 (61.8%):** The classic Fibonacci retracement
- **0.65:** The midpoint between 0.618 and 0.705
- Both levels together form the "pocket" — price often consolidates here before continuing

**Golden Pocket Rules:**
- If price enters the Golden Pocket AND an Order Block or FVG exists at the same level = very high-probability long (in discount) or short (in premium)
- If price blows through the Golden Pocket without pausing = the entire swing is likely being retraced fully (watch for support at 0.786 or 0.886 instead)
- Golden Pocket + CISD candle = OTE entry trigger

---

### 4.4 Standard Deviation Projections

ICT and Traders Reality use standard deviation Fibonacci projections for targets beyond the prior swing extreme.

**Standard Deviation Levels:**
- **-1 SD (127.2%):** First projection target after BOS — labeled -0.27 in TradingView
- **-2 SD (161.8%):** Primary swing target — labeled -0.618
- **-2.5 SD (200%):** Extended target — labeled -1.0
- **-3 SD (261.8%):** Maximum extension — labeled -1.618

**Fibonacci Extension Target Rules:**
- T1 = 0% (return to swing origin — used for partial exits)
- T2 = -0.27 (127.2%) — first scaling-out target
- T3 = -0.62 (161.8%) — primary target / full exit
- Scale out: 50% at T2, 50% at T3 (or 33% at each of 3 targets)
- Only move stop to breakeven AFTER T1 is hit

---

## SECTION 5: MARKET SEASONALITY & CYCLICALITY

### 5.1 BTC Halving Cycle

Bitcoin undergoes a halving event approximately every 4 years (every ~210,000 blocks), reducing the block reward by 50%.

**Cycle Phases:**
- **Year 1 post-halving:** Accumulation phase — price consolidates or slowly grinds higher
- **Year 2 post-halving:** Bull run phase — historically the largest price appreciation
- **Year 3 post-halving:** Distribution/topping phase — diminishing returns vs prior cycle
- **Year 4 pre-halving:** Bear market / accumulation reset

**Historical ATH Pattern:** New ATH typically reached 12–18 months after the halving date.

---

### 5.2 ICT Quarterly Theory (XAMD)

Annual macro framework mapped to calendar quarters:

- **Q1 (Jan–Mar):** X-period — Initial move; sets the year's directional bias
- **Q2 (Apr–Jun):** A-period — Accumulation / manipulation; can be choppy or reversing
- **Q3 (Jul–Sep):** M-period — The "bear quarter" historically; highest risk for long positions
- **Q4 (Oct–Dec):** D-period — Distribution / the best bullish quarter statistically

**Quarterly SMT Confirmation:**
- A new quarterly high in Q1 that is NOT confirmed by ETH (BTC makes new Q1 high, ETH doesn't) = likely manipulation → Q2 bearish
- Q3 XAMD reversal signal: BTC forms a lower low in Q3 that ETH does not confirm = potential bottom setup entering Q4

---

### 5.3 Monthly Seasonality

**Best Month:** October — historically ~80%+ win rate, highest average monthly returns for BTC
**Worst Month:** September — average return approximately -4.16%; the "September effect" is statistically the most negative month for BTC

**Monthly Bias Table (average historical BTC returns):**

| Month | Avg Return | Notes |
|---|---|---|
| January | +10% to +25% | Strong bull open most years |
| February | Variable | Often consolidation after January run |
| March | Moderate positive | Quarterly XAMD transition |
| April | Moderate | Q2 start — watch for Q1 ATH fake-out |
| May | Variable | "Sell in May" narrative; mixed results |
| June | Slightly negative | Q2 end caution |
| July | Variable | Often choppy |
| August | Slightly positive | Pre-Q3 consolidation |
| September | **-4.16% avg** | **Worst month — reduce position size** |
| October | **+20–40% avg** | **Best month — increase position size** |
| November | Strong positive | Q4 bull momentum |
| December | Variable | Profit-taking into year-end |

---

### 5.4 Day-of-Week Patterns

**Monday:** ~40% of all weekly LOWS are set on Monday — the highest single-day probability for weekly lows. The week often starts with a liquidity sweep downward (clearing prior week's lows) before the real weekly directional move begins.

**Thursday:** The only day of the week with a statistically negative average return for BTC. Often completes a midweek reversal after Tuesday/Wednesday highs are established.

**Friday:** Weekend position-squaring — often choppy. Reduced institutional participation as CME closes.

**Day-of-Week Trading Rules:**
- Monday morning: Watch for sweep of prior week's low → potential long setup for the week
- Monday evening (NYC) to Tuesday AM: Often the real weekly direction starts
- Wednesday: Trend continuation days — highest statistical probability of a strong directional candle
- Thursday: Be cautious with longs; the Thursday negative average = watch for Thursday reversal
- Friday: Scale back to 50% position size; avoid new full-size entries
- Saturday/Sunday: Weekend gap risk; keep positions small or flat

---

## SECTION 6: ADVANCED ICT MODELS (SILVER BULLET, IPDA, DOL, TURTLE SOUP)

### 6.1 ICT Silver Bullet Setup

The Silver Bullet is a precision entry model based on three specific 1-hour windows:

**Windows (EST):**
1. **03:00–04:00 AM EST** (London kill zone precision window)
2. **10:00–11:00 AM EST** (NY AM precision window)
3. **14:00–15:00 PM EST** (NY PM precision window — London close)

**Silver Bullet Entry Sequence:**
1. Within the window, price sweeps a prior session high or low (liquidity grab)
2. A Market Structure Shift (MSS) fires on the 1-minute or 5-minute chart
3. A FVG forms during the displacement after the MSS
4. Entry: On the FIRST retest of the FVG created by the displacement
5. Stop: Below (long) or above (short) the FVG + 2 ticks
6. Target: The original swing high or low that was swept (the liquidity pool)

**Silver Bullet Rules:**
- Only valid INSIDE one of the three 1-hour windows
- The FVG MUST form during the same window — no carry-forward from prior windows
- Best applied on 1-minute to 5-minute charts
- On crypto: use the same windows in EST; the 10:00–11:00 AM EST window is most reliable for BTC

---

### 6.2 ICT Turtle Soup

Turtle Soup is the ICT counter-trend fade of 20-period highs and lows (based on the Turtle Trading breakout rule).

**Rule:**
- When price breaks a **20-period high** (on any timeframe), expect a false breakout
- Entry: 5–10 ticks BELOW the prior 20-period high on the same candle or next candle
- Stop: Above the 20-period high by 5–10 ticks
- Target: 20-period low (opposite extreme)

**For 20-period Lows (bullish Turtle Soup):**
- Price breaks the 20-period low
- Entry: 5–10 ticks ABOVE the prior 20-period low
- Stop: Below the 20-period low
- Target: 20-period high

**Turtle Soup Filters:**
- Only trade Turtle Soup when the 20-period high/low aligns with a known PD Array (OB, FVG, liquidity zone)
- Higher probability during kill zones
- Avoid on strong trend days with institutional displacement confirmation — don't fade displacement

---

### 6.3 IPDA (Inter-Price Delivery Algorithm)

IPDA is ICT's concept for HOW the market delivers price over time using specific lookback periods.

**Three IPDA Lookback Periods:**
- **20 trading days** (1 calendar month): Short-term liquidity reference
- **40 trading days** (2 calendar months): Medium-term reference
- **60 trading days** (3 calendar months / 1 quarter): Long-term reference

**IPDA Rule:** The algorithm can only deliver price to ONE of two destinations:
1. **Liquidity pools** (old highs or lows — BSL or SSL)
2. **Fair Value Gaps** (imbalances from prior price action)

**Application:**
- Look back 20, 40, and 60 days for the HIGHEST high and LOWEST low
- Mark these as active liquidity targets
- The IPDA will draw price toward these levels before the reference window "ages off"
- As a 60-day FVG or liquidity level approaches, watch for acceleration toward it

---

### 6.4 Daily Bias — 7-Step Checklist

Before every trading session, run this checklist to establish the day's directional bias:

1. **Step 1 — Weekly Range:** Is price in the upper half (premium) or lower half (discount) of the prior week's range?
2. **Step 2 — Dealing Range:** Is price in weekly premium (above 50%) or weekly discount (below 50%)?
3. **Step 3 — Higher-Timeframe PD Array:** What is the nearest daily/weekly OB, FVG, or liquidity pool above and below current price?
4. **Step 4 — IPDA:** What are the 20/40/60-day liquidity pools and FVGs? Which is closer?
5. **Step 5 — Session Context:** What did the Asian session set up? Which side has more stop-loss orders (Asian box high or low)?
6. **Step 6 — Funding + OI:** What is the funding rate direction? Is OI building in one direction?
7. **Step 7 — Heatmap:** Where are the nearest yellow liquidation clusters?

**Output:** A clear directional bias (BULLISH, BEARISH, or NEUTRAL) and specific price levels to watch for the session.

---

### 6.5 Draw on Liquidity (DOL) — IRL to ERL Cycle

Price moves in a repeating cycle between two types of liquidity:

- **IRL (Internal Range Liquidity):** FVGs, Order Blocks, and imbalances WITHIN the current dealing range
- **ERL (External Range Liquidity):** Old highs, old lows, and equal highs/lows OUTSIDE the current dealing range

**The Cycle:**
```
Price at ERL (external liquidity pool) 
→ Swept / cleared
→ Draw to IRL (nearest FVG or OB inside the range)
→ IRL filled / mitigated
→ Draw back to opposite ERL
→ Repeat
```

**Rules:**
- After an ERL is swept, the next target is an IRL (FVG or OB)
- After an IRL is filled, the next target is the opposite ERL
- FVGs are INTERNAL magnets — price will reach at least 50% of any FVG (CE = Consequent Encroachment)
- BSL (Buy-Side Liquidity) and SSL (Sell-Side Liquidity) are EXTERNAL magnets — above prior swing highs and below prior swing lows
- Never chase a move that just cleared an ERL — wait for the IRL draw before entering

---

## SECTION 7: VWAP, VOLUME PROFILE & MARKET PROFILE

### 7.1 Session VWAP Rules

VWAP (Volume Weighted Average Price) resets at session opens for intraday context.

**Session Reset Points for 24/7 Crypto:**
- **Daily VWAP:** Resets at 00:00 UTC (neutral daily benchmark)
- **Asian Session VWAP:** Anchored to Asian open (~20:00 EST)
- **London Session VWAP:** Anchored to London open (~02:00 EST)
- **NY Session VWAP:** Anchored to NY open (~07:00 EST)

**Run all three simultaneously** to see volume-weighted fair value across sessions.

**Core VWAP Rules:**
- Price above Session VWAP = buyers controlled that session → ONLY take longs on pullbacks to VWAP
- Price below Session VWAP = sellers controlled → ONLY take shorts on rallies to VWAP
- Never fade VWAP as a stand-alone signal — wait for a candle rejection at VWAP
- VWAP failure (price tries to reclaim VWAP but fails to hold) = continuation in the existing direction

**Session Handoff Rules:**
- Asian session closes ABOVE Asian VWAP → London has bullish baseline
- London closes ABOVE London VWAP → NY session has bullish baseline
- BOTH session VWAPs below current price = strongest bullish session filter
- Both above current price = strongest bearish session filter

---

### 7.2 Anchored VWAP (AVWAP)

**Anchor Point Hierarchy (highest to lowest significance):**
1. Weekly open (Monday first 30-min candle) — weekly premium/discount reference
2. Monthly open — macro positioning reference
3. Post-BOS swing low/high — directional trend anchor
4. Major liquidity event / news candle — event-driven fair value
5. Daily session open — intraday benchmark

**Key AVWAP Rules:**
- Price above weekly AVWAP = weekly premium → seek longs on dips TO weekly AVWAP
- Price below weekly AVWAP = weekly discount → seek shorts on rallies TO weekly AVWAP
- Post-BOS: Anchor AVWAP to the LAST SWING LOW (for bullish BOS) — price often retests this AVWAP before continuing up
- A decisive break BELOW a macro AVWAP anchored to a significant prior low = major trend reversal signal

**AVWAP Standard Deviation Bands:**
- ±1 SD: Contains ~68% of price action — the "fair range"
- ±2 SD: Contains ~95% — the outer extreme
- +2 SD touch in a sideways session → bearish reversal setup targeting the VWAP mean
- -2 SD touch → bullish reversal setup targeting the VWAP mean
- In a STRONG TREND, price can ride the +1 SD band continuously — DO NOT fade it during trending sessions

**Multiple AVWAP Confluence Rule:**
When 2+ Anchored VWAPs converge at the SAME price level, the confluence carries significantly more weight. Stack with Volume Profile POC + historical S/R for maximum confidence.

---

### 7.3 Volume Profile — POC, VAH, VAL

**Definitions:**
- **POC (Point of Control):** Price level with HIGHEST traded volume in a period = "fair price" / equilibrium
- **Value Area (VA):** Price range containing **70%** of total traded volume
- **VAH (Value Area High):** Upper boundary of the 70% zone
- **VAL (Value Area Low):** Lower boundary of the 70% zone
- **HVN (High-Volume Node):** Thick histogram area — strong consensus, acts as S/R
- **LVN (Low-Volume Node):** Thin histogram area — price moves through rapidly ("fast lane")

**POC Rules:**
- POC = gravitational pull — price returns to it repeatedly during ranging conditions
- "Naked POC" (prior session POC never revisited) = pending magnet until price returns and fills it
- POC migrating higher during a rally = institutional accumulation at elevated prices (bullish)
- POC migrating lower during a drop = distribution (bearish)
- Do not use YESTERDAY'S POC as a mechanical entry in isolation — use it as context

**VAH/VAL Mean Reversion Rules:**
- Price at VAL, low volume → wait for bullish candle closing INSIDE the Value Area → long targeting POC → VAH
- Price at VAH, low volume → wait for bearish candle closing INSIDE the Value Area → short targeting POC → VAL
- Stop: 10 ticks (or ~0.3–0.5% for BTC) beyond the VAL/VAH level
- "Rule of 3": If price tests the same VAH or VAL THREE times without breaking, reversal probability increases significantly

**VAH/VAL Breakout Rules:**
- Price opens above VAH and holds for 30+ minutes = TREND day → trade extensions, not fades
- Sustained close above VAH = bullish acceptance → target next HVN above
- Close below VAL = bearish acceptance → target next HVN below

**Session Context:**
- New session opens INSIDE prior VA → expect range-bound rotation between VAH and VAL
- New session opens OUTSIDE prior VA → expect directional trending behavior
- Mark prior session POC, VAH, VAL BEFORE each new session opens — these are first reference levels

---

### 7.4 VPVR (Volume Profile Visible Range) — HVN & LVN

**HVN Trading Rules:**
- HVN = "shelf" — thick volume cluster; price slows here, often reverses
- After a breakout from consolidation into an LVN gap → next HVN = PRIMARY TARGET
- LVN between two HVNs = "open road" — minimal resistance, fast move
- HVN breakout sustained for multiple candles = HVN flips from resistance to support (or vice versa)
- Use VPVR on 1H, 4H, and Daily timeframes for BTC (sub-15M is too noisy)

**LVN Rules:**
- LVN = "fast lane" — price moves rapidly through it
- Do NOT enter or take profit INSIDE an LVN — wait for the next HVN
- LVN on the approach side of a prior HVN = potential reversal zone warning

**Naked POC Chain:** Mark all prior session/day/week POCs that were never revisited. Chain them together as a sequence of pending targets. When price gaps away from a naked POC, probability of eventual return remains elevated until tested.

---

### 7.5 Market Profile — Initial Balance (IB)

**Definition:** The price range established during the FIRST TWO 30-minute periods (A + B) = first hour of the session. For NY open: **07:00–08:00 AM EST** (or 07:00–10:00 AM EST for the full 3-hour crypto IB).

**Day Type Classification:**

| Day Type | IB Size | Shape | Approach |
|---|---|---|---|
| Trend Day | Narrow | Elongated | Buy breakout, don't fade |
| Normal Variation | Moderate | One-sided extension | Trade extension direction |
| Neutral Day | Wide | D-shape / balanced | Range trade VAH/VAL |
| Spike Day | Wide with tail | Sharp spike | Tail defines reversal limit |

**Initial Balance Breakout Rules:**

1. **Entry:** Price must break IB High (longs) or IB Low (shorts) with a FULL 30-minute period CLOSE outside the range (not just a wick)
2. **Sustained Acceptance:** Wait for TWO consecutive 30-min periods outside IB — strongest confirmation
3. **Volume:** Higher-than-average volume during the opening hour = institutional participation = more reliable breakout
4. **Targets:**
   - Conservative: **1.5× IB range** measured from breakout point
   - Aggressive: **2–3× IB range** (narrow IBs on trend days)
   - Primary target: next session POC or prior HVN
5. **Stops:** Long = below IB Low. Short = above IB High. For BTC: widen 1.5–2% for volatility
6. **Optimal timing:** C, D, E periods (60–90 min after IB closes) = highest-probability breakout windows
7. **70–75% Probability Rule:** Once price closes outside the IB for one full period, 70–75% chance it reaches at least the 1× IB extension
8. **IB Rejection:** Price breaks IB High but returns inside within next period → 70–75% chance it tests IB Low

---

### 7.6 Full Session Workflow Using VWAP + Volume Profile

**Pre-Session Setup (mark before session opens):**
1. Mark Asian session box HIGH and LOW (the liquidity pools / Brinks Box)
2. Mark prior session POC, VAH, VAL
3. Draw Anchored VWAP from: (a) Monday open for weekly context, (b) last confirmed swing low/high
4. Plot VPVR on 1H/4H to identify HVNs and LVNs
5. Mark all naked POCs from prior sessions
6. Check Coinglass heatmap for yellow liquidation clusters near current price

**London Kill Zone (02:00–05:00 AM EST):**
- Watch for sweep of Asian box high/low (BTMM stop hunt)
- If price sweeps Asian HIGH then falls below Asian VWAP → short targeting Asian VAL or prior session POC
- If price sweeps Asian LOW then reclaims Asian VWAP → long targeting Asian VAH or prior session POC
- Entry: First retest of London VWAP after sweep-and-reversal
- Target: Nearest HVN above (long) or below (short) on VPVR

**NY Kill Zone (07:00–10:00 AM EST):**
- Note whether NY opens inside or outside prior session VA
- Inside VA → range behavior between VAH and VAL (mean reversion)
- Outside VA → trend day; trade in breakout direction
- IB assessment: If IB (07:00–08:00 EST) is narrow (< 0.5% range for BTC) → expect trend day; C-period breakout is the entry
- Target: 1.5–2× IB range from breakout close

**Confluence Hierarchy:**
1. Weekly AVWAP + Session POC + HVN at same level = highest confidence
2. Session VWAP + prior session VAH/VAL = strong
3. IB boundary + VPVR HVN = strong
4. Naked POC alone = moderate
5. LVN gap with no other confluence = acceleration zone only, not S/R

---

## SECTION 8: ORDER BOOK, CVD & ON-CHAIN ANALYSIS

### 8.1 Order Book Walls — Reading Rules

**Pre-Session Procedure (30–60 min before session open):**
- Use a combined order book tool (Tapesurf.com aggregates 10 exchanges simultaneously — a wall on Binance alone = only 30–40% of market depth)
- Mark walls 30–60 min before session opens — these become S/R anchors for the opening manipulation sweep
- BTC/USDT significance threshold on Binance/Bybit: clusters of **50+ BTC at a single level** = whale-tier wall

**Spread Thresholds:**
- BTC/USDT normal spread: $1–$10 (0.001–0.01%)
- Spread widening BEYOND this before session open = reduced liquidity = higher manipulation risk

**Real Walls vs Spoof/Fake Walls:**

| Signal | Real Wall | Spoof |
|---|---|---|
| Behavior as price approaches | Holds, absorbs volume, color darkens | Disappears entirely before touch |
| Refill behavior | Replenished after partial fill | Never refills |
| Age/persistence | Sits for hours at same level | Appears and vanishes within 30 seconds |
| Relationship to round numbers | Can be at any level | Disproportionately clusters at round numbers |
| Pattern | 5 BTC keeps trading at same price; 200+ BTC has transacted there | No such refill pattern |

**Key Rule:** "A wall that has been partially filled and replenished = genuine." A wall that vanishes on contact = stop-hunt lure, not real support.

**Stop Hunt Alignment:**
- Before London open (07:00 GMT): large ask walls sit just above Asian high; large bid walls just below Asian low
- This creates the Brinks Box boundary — the session open sweep moves INTO these walls to trigger stops
- A genuine wall that holds = session S/R anchor
- A spoofed wall that disappears = institutional lure for retail breakout traders

---

### 8.2 CVD (Cumulative Volume Delta)

CVD = running total of (aggressive buy volume − aggressive sell volume). Rising CVD = buyers more aggressive; falling CVD = sellers more aggressive.

**Session-Scoped CVD Rule:**
- Standard CVD blends all sessions = noise
- Use SESSION-SCOPED CVD that resets to zero at each session open
- Divergences only valid WITHIN the same session — comparing London CVD to Asian CVD = meaningless

**Four Divergence Signals:**

| Price | CVD | Signal |
|---|---|---|
| Higher high | Lower high or flat | Bearish divergence — buyer exhaustion; watch for reversal |
| Lower low | Higher low or flat | Bullish divergence — seller exhaustion; watch for bounce |
| Higher low (uptrend) | Lower low | Hidden bearish — downtrend continuation |
| Lower high (downtrend) | Higher high | Hidden bullish — uptrend continuation |

**CVD Rules:**
- Minimum timeframe for actionable divergence: **15-minute or 1-hour chart** (1M = noise)
- Do NOT enter on divergence alone — wait for a break of the most recent swing low (bearish) or high (bullish)
- "CVD surges sharply late in a directional push but price stops advancing" = exhaustion signal at session extremes (London 09:30–10:30 GMT, NY 10:00–10:30 AM EST) — tighten stops, take profits
- Absorption signal: CVD falling (selling pressure active) but price holds the level = passive buyers absorbing → bullish only if selling follow-through fails

**Confluence Checklist for CVD trade (need 3 of 4):**
1. Price at known reference level (prior high/low, VWAP, liquidation cluster, OB)
2. CVD diverges from price action
3. Volume expands above session average on confirming candle
4. VPIN > 0.5 (if available) — indicates informed traders positioning

---

### 8.3 Full Confluence Scoring Matrix — Brinks Box Session Trade

Before taking a Brinks Box session trade, score each factor:

| Factor | Bullish Score +1 | Bearish Score +1 |
|---|---|---|
| Funding rate | < -0.01% (shorts paying) | > +0.05% (longs paying heavily) |
| OI + Price direction | Falling OI + rising price (short covering) | Rising OI + falling price (new shorts) |
| CVD at session open | Bullish divergence at Asian low | Bearish divergence at Asian high |
| Heatmap yellow zone | Yellow zone below price swept | Yellow zone above price swept |
| Order book walls | Genuine bid wall absorbing at Asian low | Genuine ask wall absorbing at Asian high |
| Exchange flows | Outflows > Inflows (7DMA); Whale Ratio < 0.6 | Inflows spiking; Whale Ratio > 0.6 |
| Spot-perp basis | Perp at discount to spot | Perp at premium to spot |

**Rule:** Score **4 or more** in one direction before entering. Avoid 3-3 tied signals (conflicting — skip the trade).

---

## SECTION 9: PROP FIRM RULES — SESSION-BASED TRADING

### 9.1 Drawdown Rule Types (Critical for System Design)

**Static Drawdown (FTMO, FundedNext — Forex):**
- Floor fixed at initial balance minus 10% — FOREVER
- As you profit ($100K → $125K), floor stays at $90K
- Buffer EXPANDS as you profit → most favorable for session traders who let winners run
- Daily loss: 5% of account balance (equity-based, including floating PnL), resets midnight CE(S)T

**EOD Trailing Drawdown (TopStep, Apex EOD — Futures):**
- Floor rises to (peak END-OF-DAY balance − trail amount)
- Intraday wicks DO NOT move the floor — only closing equity matters
- After a profitable day, your room shrinks; after a bad day, floor stays
- Best for consistent incremental traders; protects runners that almost get stopped during NY volatility

**Intraday Trailing Drawdown (Apex Intraday):**
- Floor moves TICK-BY-TICK with unrealized equity peak during the session
- A trade that's up $2,000 but closes at breakeven has STILL raised your floor by up to $2,000
- HARDEST model for session traders using 1:2 or 1:3 RR targets — avoid for BTMM/ICT strategies

**Recommendation for BTMM/ICT/Hybrid System:** Static or EOD trailing drawdown accounts ONLY. Intraday trailing drawdown is incompatible with strategies that let trades breathe to TP2/TP3.

---

### 9.2 FTMO Specific Rules

**2-Step Challenge (Standard):**
- Max Daily Loss: **5% of account balance** — EQUITY-based (includes floating PnL + commissions)
- Max Total Loss: **10% of initial balance** — STATIC, does not trail highs
- Reset: **Midnight CE(S)T** (approximately 6 PM ET / 7 PM ET depending on DST)

**IMPORTANT — Daily Reset Gotcha:**
FTMO resets the daily limit at midnight CE(S)T. If you hold a position overnight, the new day's limit resets against a potentially different balance. A position within limits before midnight can trigger a violation after the reset if floating losses are large enough. Session traders holding through the CE(S)T midnight should ensure floating loss is less than 2% of account.

**News Trading:**
- Challenge phases: Unrestricted
- Funded Standard accounts: No trades within **2 minutes before AND 2 minutes after** high-impact events on directly affected instruments
- Funded Swing accounts: No news restrictions at all

**NY Kill Zone + FTMO News Rule:**
- NFP is 8:30 AM ET → FTMO Standard funded accounts: cannot open/close GBPUSD, EURUSD from 8:28–8:32 AM ET
- Solution: Be fully out before 8:28 AM or accept the 4-minute freeze
- London kill zone is SUPERIOR for FTMO Standard funded accounts — avoids US news windows entirely

---

### 9.3 Prop Firm Comparison for Session Traders

| Firm | Daily DD | Max DD | Type | Reset | Best For |
|---|---|---|---|---|---|
| FTMO 2-Step | 5% equity | 10% static | Static | Midnight CE(S)T | Forex London/NY session |
| FTMO Swing | 5% equity | 10% static | Static | Midnight CE(S)T | Hold-through sessions |
| TopStep $50K | $1,000/day | $2,000 EOD trail | EOD Trailing | 3:10 PM CT settlement | Futures ES/NQ NY session |
| Apex EOD | DLL pauses (not fails) | EOD trail | EOD Trailing | 4:59 PM ET | Futures NY; DLL recovers |
| Apex Intraday | No DLL | Intraday trail | Intraday Trailing | N/A | AVOID for runners |
| The5%ers | 3–5% balance | 6–10% balance | Balance-based | Server midnight | Most forgiving daily DD |

**The5%ers advantage:** Uses BALANCE-based daily drawdown — open trades do NOT count until closed. Most forgiving for session traders who may hold through intraday retracements.

---

### 9.4 Kill Zone Recommendations by Firm

| Kill Zone | EST Window | Best Firm Match | Notes |
|---|---|---|---|
| London | 02:00–05:00 | FTMO Standard Funded | No US news conflict; clean setup; BTMM manipulation sweep window |
| NY Open | 07:00–10:00 | TopStep / Apex EOD | EOD trailing protects intraday runners; ES/NQ most liquid |
| London-NY Overlap | 08:00–11:00 | Any firm | Highest liquidity; ADR adjustment required |
| Lunch hour | 12:00–14:00 | AVOID ALL FIRMS | Low volume, choppy, prop firm accounts give back morning profits here |
| Asian | 20:00–00:00 | Markup/analysis only | AUD/NZD/JPY pairs only; not for Western session traders |

**Win Rate by Kill Zone (backtested across multiple independent sources):**
- Inside kill zones: **68% win rate, 2.8 profit factor**
- Outside kill zones: **41% win rate, 0.9 profit factor**
- London: 65–70% win rate
- NY Open: 70–75% win rate (highest)

---

### 9.5 Position Sizing for Prop Firms

**Core Formula:**
```
Dollar Risk = Account Balance × Risk%
Lot Size = Dollar Risk ÷ (Stop Loss in Pips × Pip Value per Lot)
```

**Pip Values:**
- EUR/USD, GBP/USD: $10/pip per standard lot
- XAU/USD (Gold): $100/point per standard lot
- USD/JPY: ~$9.09/pip per standard lot

**ADR-Based Stop Rules:**
- Conservative (challenge phase): Stop = 25–35% of daily ADR from entry
- Standard: Stop = 50% of ADR
- Wide (funded static DD): Stop = 75–100% of ADR

**Key ADR Rule:** On news days (NFP, CPI) where ADR expands to 1.5–2.5× normal, either skip the trade or cut position size by **40–50%** to maintain equivalent dollar risk per ADR unit.

**Lot Size Examples at 0.5% Risk:**

| Account | 0.5% Risk | 20-pip Stop EUR/USD | 40-pip Stop | 80-pip Stop |
|---|---|---|---|---|
| $10,000 | $50 | 0.25 lots | 0.12 lots | 0.06 lots |
| $25,000 | $125 | 0.62 lots | 0.31 lots | 0.16 lots |
| $50,000 | $250 | 1.25 lots | 0.62 lots | 0.31 lots |
| $100,000 | $500 | 2.5 lots | 1.25 lots | 0.62 lots |

**Risk Tier Progression:**

| Phase | Risk/Trade | Rationale |
|---|---|---|
| Challenge early | 0.25% | Preserves runway for learning curve |
| Challenge established | 0.5% | 5 consecutive losses = 2.5% (inside 5% DLL) |
| Funded months 1–3 | 0.5% | Protect the account; floor not yet built |
| Funded months 4–6 | 0.75% | After 3 profitable months |
| Funded month 7+ | 1.0% | After 6+ consistent months only |

---

### 9.6 Prop Firm Challenge Rules Summary

**Challenge Phase Hard Rules:**
1. Risk 0.5% per trade maximum — never exceed 1% during challenge
2. Daily cap: STOP trading when daily drawdown reaches **2.5%** (50% of the 5% DLL) — leaves buffer
3. Trade ONLY London (02:00–05:00 EST) and NY (07:00–10:00 EST) kill zones
4. Max 2 trades per kill zone; hard stop after 2 consecutive losses regardless of remaining headroom
5. Check economic calendar nightly; avoid NY open entries straddling 8:30 AM ET on FTMO Standard funded
6. News days: cut lot size by 50%; ADR is 1.5–2.5× normal
7. NEVER trade 12:00–14:00 EST lunch hour
8. Overnight holds on FTMO: only if floating loss < 2% of account

**BTMM / Hybrid System Prop Firm Adaptation:**
- Day 1 (Accumulation): Reduce to 0.25% risk or skip trading
- Day 2 (Manipulation): Watch for Judas Swing — DO NOT CHASE; wait for reversal confirmation
- Day 3 (Distribution): Execute full-size entries at 0.5–1% risk
- One Masterpiece per day (Steve Mauro's own rule) = perfectly aligned with prop firm requirements
- London = "trapping session" (setup); NY = "execution session" (entry + distribution)

**Quick Position Sizing Formula:**
```
Dollar risk = Account × 0.005
Lot size = Dollar risk ÷ (Stop pips × $10)
ADR-elevated day: multiply lot size × 0.5 before entry
```

---

## MASTER CONFLUENCE CHECKLIST (ALL SECTIONS COMBINED)

Before ANY trade entry, verify:

### Macro Context (HTF — Weekly/Daily)
- [ ] Weekly Dealing Range: Is price in premium (> 50%) or discount (< 50%)?
- [ ] ICT Quarterly XAMD: Which quarter are we in? Is Q3 caution active?
- [ ] Monthly seasonality: Is it September (reduce size) or October (full size)?
- [ ] Day-of-week: Is it Monday (potential sweep of weekly low first)?
- [ ] IPDA: What are the 20/40/60-day liquidity targets?
- [ ] BTC halving cycle: Which phase of the 4-year cycle?

### Session Context (H4/H1)
- [ ] Asian session box established (high/low marked)?
- [ ] Prior session POC, VAH, VAL marked?
- [ ] Weekly AVWAP direction established?
- [ ] Funding rate: Positive/negative/neutral?
- [ ] OI direction: Rising with price (trend) or diverging (reversal setup)?
- [ ] Heatmap: Nearest yellow liquidation cluster identified?
- [ ] BTC.D at NY open: Rising (BTC) or falling (alts)?
- [ ] Exchange flows (7DMA): Inflows rising (bearish) or outflows rising (bullish)?

### Kill Zone Timing (H1/15M)
- [ ] Currently inside a kill zone? (London 02–05 AM EST, NY 07–10 AM EST, Silver Bullet windows)
- [ ] Not during lunch hour (12–14 EST)?
- [ ] Economic calendar checked — no straddling major news on FTMO Standard funded?

### Entry Trigger (15M/5M)
- [ ] Liquidity sweep confirmed (Asian box high or low taken out)?
- [ ] CISD or MSS fired in the reversal direction?
- [ ] Displacement: 3+ consecutive large-body candles + FVG left behind?
- [ ] FVG / Order Block / Breaker Block present at entry zone?
- [ ] SMT Divergence confirmed (BTC vs ETH opposing structure at PD Array)?
- [ ] Dealing Range confirms direction (discount for longs, premium for shorts)?
- [ ] OTE: Entry in 62–79% retracement zone?
- [ ] CVD: Bullish or bearish divergence at the entry level?
- [ ] Order book: Genuine bid/ask wall present (refilling, not spoofed)?
- [ ] Brinks Box confluence score: 4+ factors aligned?

### Risk Management
- [ ] Position size calculated (Account × Risk% ÷ Stop pips × pip value)?
- [ ] ADR normal or elevated? If elevated >1.5×: cut size by 50%
- [ ] Stop beyond the structural swing (not at VWAP — at swing extreme)?
- [ ] Targets set: T1 = prior high/low, T2 = 127.2%, T3 = 161.8%?
- [ ] Prop firm daily loss check: Still within 2.5% drawdown for the day?
- [ ] Maximum 2 entries already used today for this kill zone?

---

## GLOSSARY ADDITIONS (VOLUME 3)

**AVWAP:** Anchored VWAP — VWAP anchored to a specific price event (swing high/low, session open, Monday open)

**Brinks Box Score:** The 7-factor confluence scoring matrix for session trade viability (4+ required)

**CISD:** Change in State of Delivery — first reversal signal; body close past delivery candle opening price

**CVD:** Cumulative Volume Delta — running total of aggressive buy minus aggressive sell volume

**Dealing Range:** The range between two significant swing points; above 50% = premium (shorts), below 50% = discount (longs)

**Displacement:** 3+ consecutive large-body candles in same direction + FVG = institutional order flow confirmation

**DOL:** Draw on Liquidity — the current price target the algorithm is delivering toward

**ERL:** External Range Liquidity — BSL/SSL pools outside the current range (old highs/lows)

**HVN:** High-Volume Node — thick Volume Profile cluster acting as S/R

**IB:** Initial Balance — first 1–2 hours of a session establishing the day's opening range

**IPDA:** Inter-Price Delivery Algorithm — delivers price to liquidity pools or FVGs within 20/40/60-day lookback windows

**IRL:** Internal Range Liquidity — FVGs and OBs inside the current dealing range

**LVN:** Low-Volume Node — thin Volume Profile area; price moves rapidly through it

**MSS:** Market Structure Shift — structural swing broken; later signal than CISD

**OTE:** Optimal Trade Entry — 62%, 70.5%, 79% Fibonacci retracement zone

**POC:** Point of Control — price level with highest traded volume in a period

**Propulsion Block:** Single ignition candle inside an OB; entry at 50% (Mean Threshold)

**Session VWAP:** VWAP reset at each session open (Asian, London, NY) for session-specific fair value

**Silver Bullet:** ICT precision entry model within three 1-hour windows (03–04, 10–11, 14–15 EST)

**SMT Divergence:** BTC vs ETH opposing structure at a PD Array = reversal confirmation

**Turtle Soup:** Fade of 20-period highs/lows; entry 5–10 ticks inside the broken extreme

**VA:** Value Area — price range containing 70% of session's total traded volume

**VAH/VAL:** Value Area High/Low — upper and lower boundaries of the 70% volume zone

---

*Volume 3 compiled from 9 parallel research agents. Volume 4 will cover: Traders Reality full masterclass session list, Tino's psychological/mindset trading rules, and any additional topics pending from the 10th research agent.*
