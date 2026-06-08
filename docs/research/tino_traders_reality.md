# Tino / Traders Reality — Methodology Research (cited)

Deep-research synthesis for building a backtestable model. The discipline of
this document: **separate (a) what Tino / the community teaches from (b) what
is empirically supported**, and flag every claim that is unfalsifiable,
hindsight-prone, or unverified. Stay humble — most of this is hypothesis, not
proven edge.

Sources were gathered by five parallel research agents (origins; indicator
rules; recovery theory; market-maker cycle; sessions/timing). Confidence and
fact-vs-assertion are marked per claim. Several primary pages (Scribd,
innercircletrader.net, forex-station, volumespreadanalysis.com) were
gated/403/blank on direct fetch; claims resting only on search-engine
excerpts are flagged LOWER confidence.

---

## 1. Who Tino is, and where the method comes from

- **Tino** (likely **Constantino Pistou**, UK-based) is the founder/host of
  **Traders Reality** (tradersreality.com), a trading-education community
  reportedly established **2017**, covering forex/crypto/stocks.
  *(Medium confidence — name/date/location from a single aggregator,
  finnotes.org; not confirmed on the official site.)*
- The **"Hybrid System" is not original to Tino.** It fuses two pre-existing
  methods: **PVSRA** (popularized ~2013 on ForexFactory's *Sonic R* community
  by the user **"Trader At Home"**) and **Steve Mauro's "Market Maker Method" /
  "Beat the Market Maker" (BTMM)**. *(Medium-high confidence; repeated across
  multiple sources, exact attributions medium.)*
- **Lineage:** Richard **Wyckoff** (supply/demand, accumulation/distribution)
  → Tom **Williams** **Volume Spread Analysis (VSA)** in the 1970s → Richard
  **Ney** ("specialist"/market-maker manipulation theory, *The Wall Street
  Jungle*, 1970). PVSRA and BTMM are descendants of this "read the market
  maker" school. *(High confidence on the VSA/Wyckoff lineage; Ney's specific
  influence is asserted by the VSA camp.)*
- **PVSRA acronym:** most-attested expansion is **"Price, Volume, Support &
  Resistance Analysis"** — *not* "Price Volume Spread Read Analysis" (that
  wording was not found in any source; "spread" echoes VSA but is a loose
  gloss). *(High confidence.)*
- **Relation to ICT:** ICT (Michael J. Huddleston) is a **separate, later**
  framework — price-structure/liquidity driven and largely volume-agnostic
  (FX has no centralized volume). PVSRA is volume/candle-coloring + S&R driven.
  They **share only the broad "market makers manipulate retail" premise** and
  much vocabulary (liquidity, sweeps, accumulation/manipulation/distribution).
  Much of the session/killzone/daily-open material below is ICT, which the
  Traders Reality community has absorbed. *(High confidence on ICT being
  distinct; the PVSRA-vs-ICT contrast is structural, not from one authority.)*

**Honesty flag:** The entire school's core premise — that an identifiable
"market maker" deliberately and coordinatedly manipulates price to hunt retail
stops — is an **assertion inferred from the same price/volume it explains**.
No source identifies actors, cites order-flow data, or shows coordination. We
treat it as a *lens*, not a fact.

---

## 2. PVSRA Vector Candles — the exact, mechanical rules (HIGH confidence)

This is the most solid part: the canonical logic is recovered verbatim from
the open-source `tr-full.pine` port and the official `Traders_Reality_Lib`
`calcPvsra()` description, which agree.

```
av        = sma(volume, 10)            // 10-bar simple average of volume
value2    = volume * (high - low)      // "effort" = volume x spread
hivalue2  = highest(value2, 10)        // highest effort over last 10 bars

// tier: 1 = climax/vector, 2 = above-average, 0 = normal
va = (volume >= av*2 OR value2 >= hivalue2) ? 1
   : (volume >= av*1.5)                ? 2
   : 0

isBull = close > open
```

Color scheme:

| tier | bull (close>open) | bear (close<open) |
|---|---|---|
| climax / vector (va=1) | **lime** `#00FF00` | **red** `#FF0000` |
| above-average (va=2)   | **blue** `#0000FF` | **fuchsia/violet** `#FF00FF` |
| normal (va=0)          | gray `#999999`     | dark gray `#4d4d4d` |

Key mechanical facts:
- **N = 10** for both the volume SMA and the effort high.
- The climax trigger is **OR**, not AND. (The official *prose* says "200% …
  and candles where …" but the **code uses `or`**; code is authoritative. Our
  implementation already uses OR — correct.)
- The spread×volume branch lets a **wide-range** candle qualify as a vector
  even if raw volume is below 2× average.
- Lookbacks **include the current bar** in the canonical code. Descriptions
  say "10 previous candles" (implying prior-only). Minor discrepancy — default
  to matching the code; expose as a parameter.
- Bull/bear is `close > open` only.

Sources: `tr-full.pine` (github.com/mikejuliano2/pine), TriexDev
SuperBuySellTrend Pine, TradingView `Traders-Reality-Lib` /
`Traders-Reality-Main` / `PVSRA-Volume-Suite` / `Vector-Candle-Zones`.

> Status: our `kudbee_quant/signals/pvsra.py` already implements exactly this.
> The research confirms it is faithful.

---

## 3. The "vector candle always gets recovered" theory

How it is taught (community assertion):
- Vector candles are the market maker's "footprint"; the liquidity in them is
  "unrecovered," and price will **return ("recover"/"revisit")** the zone to
  release it. Unrecovered vectors act as **magnets/targets**.
- Stated with an **open-ended horizon**: "eventually," "could be 10 minutes or
  a year," **"no set rule for when."**
- "Smaller timeframe → faster recovery"; "normal vectors recovered same day or
  next hour."
- Operational definition (from the *Vector Candle Zones* indicators):
  **recovery = price moves back through the vector candle's price box** (its
  high–low range), not specifically the high, low, or 50%.
- **Partial recovery of 50%–100% of the zone** is claimed to mark
  high-probability reversal points.
- Prescribed action: "trade towards and away from" unrecovered zones;
  philosophy **"it's ok to be counter-trend, never counter-MM."**

**Honesty flags (critical):**
- The **headline claim is unfalsifiable as stated.** "Always eventually
  recovered, no time limit, no invalidation" → no observation can disprove it;
  any not-yet-recovered vector is simply "not recovered *yet*." Hedge words
  ("normal," "often," "eventually," "high probability," "do not necessarily")
  systematically convert checkable claims into unfalsifiable ones.
- The X/field "proof" ("see — ALL vectors in this range got filled") is
  **hindsight/survivorship selection**: picking a completed range and noting
  the vectors inside were filled does not test a forward prediction.
- The intent layer ("a green vector is the MM selling into retail") is
  **unobservable** and circular.

**What IS testable (this is how we honor the theory honestly):**
1. **Recovery rate by timeframe & horizon** — of all vector candles, what
   fraction have price re-enter the box within N bars? Build the survival
   curve. The bounded claims ("small-TF same day/next hour") become measurable.
2. **50–100% partial-recovery reversal** — do reversals actually cluster when
   price penetrates 50–100% of a vector zone? Measurable.
3. **Magnet effect** — is an unrecovered vector zone reached more often than a
   random equidistant level? Measurable against a null model.

See `docs/research/testable_ruleset.md` §A.

---

## 4. Market-maker cycle / manipulation philosophy

Taught structure (community assertion; mostly from BTMM/ICT):
- **AMD cycle:** Accumulation → Manipulation → Distribution, claimed to repeat
  on every session/day/week.
- **Session mapping:** Asia = accumulation, London = manipulation, New York =
  distribution. *(Heuristic, medium confidence.)*
- **"MM moves in 3s"** / **three-day cycle:** three "level" pushes; Level I
  (MM-driven fast move) → Level II (retail-emotion) → Level III (MM return for
  profit-taking).
- **Liquidity engineering:** stop orders genuinely cluster above prior highs
  (buy-side liquidity) and below prior lows (sell-side liquidity) — **this part
  is structurally true**. A **"sweep"** spikes through such a level then
  reverses. "Price moves to where the money is."

**Honesty flags:** The *only structurally factual* element is that stops
cluster above highs / below lows. The leap from "stops rest there" to "market
makers deliberately hunt them with intent" is assertion. "Ideal cycle"
framing is a textbook unfalsifiability marker (deviations = "non-ideal").
Sweep *price behavior* (spike + reverse) is observable and codeable; the
*causal attribution* is not.

**Testable extraction:** sweep events (we already detect these in
`context/mm_cycle.py`); day-of-week clustering of weekly extremes; forward
returns after a sweep. See ruleset §C.

---

## 5. Sessions, killzones, key-level retests, holidays

**DST caveat (load-bearing for backtests):** Do **not** hardcode one UTC
offset. London = GMT/BST, New York = EST/EDT, Frankfurt = CET/CEST, and US/EU
DST switch dates differ by ~2 weeks. **Anchor sessions to New York local time
(ICT convention)** and derive UTC per-day.

ICT killzones (New York local time):
| Killzone | NY time |
|---|---|
| Asian | 20:00–22:00 (some sources 19:00–23:00) |
| London open | 02:00–05:00 |
| New York (forex) | 07:00–10:00 |
| New York (indices) | 08:30–11:00 |
| London close | 10:00–12:00 |

- **London–New York overlap (~08:00–11:00 ET / 12:00–16:00 GMT) is the
  single most liquid, volatile window** — the "premium" window. *(High
  confidence; >80% of volume involves USD.)* **This is where we focus.**
- **Frankfurt** opens ~1h before London (07:00 GMT winter); the 07:00–08:00
  GMT pre-London hour seeds early EU volatility.
- **Asian session** = low volatility, tight range that London often
  sweeps. *(Medium-high.)*
- **Daily open — ICT "Midnight Open" = the 00:00 ET candle open.** Above =
  bullish daily bias, below = bearish; acts as intraday S/R magnet. *(High
  confidence definition.)*
- **Daily-open RETEST has measured base rates** (edgeful, Jul 2024–Jan 2025):
  ES ~58–69%, NQ ~57–63% (**73% on Tuesdays** when opening below), BTC
  ~64–65%, Gold ~50/50 (unreliable). *(High confidence for that sample —
  single ~6-month window; re-verify.)* **This directly validates building the
  user's "second test of the daily open" event study.**
- **Weekly Open = Sunday 18:00 ET** (CME futures reopen); holding above/below
  defines weekly bias. *(Medium-high.)*
- **"Second test" concept:** ICT "consequent encroachment" teaches a level
  missed on the first leg is often delivered on the **second leg/test** —
  "high-probability, not guaranteed." *(Medium; qualitative.)*
- **Day-of-week:** Monday sets a tentative/"manipulation" range; weekly
  high/low often forms **Tuesday** (Wednesday backup); range expansion
  Tue→Thu. *(Medium; backtest-verifiable, not quantified in sources.)*
- **London** is claimed to frequently set the **daily high or low**.
  *(Low-medium; only headline retrievable.)*
- **Bank/public holidays:** thin liquidity, wider spreads, erratic moves;
  momentum methods break down. **Exclude/flag US, UK, EU, JP holidays + the
  late-December window.** *(High confidence — standard microstructure.)*

---

## 6. Trade-selection philosophy (as the user framed it)

- A **few high-probability, targeted trades** in premium windows beats high
  frequency. Goal = **percentage gain governed by strategy**, not dollar
  amount or trade count.
- **Work *with* market-maker momentum, not against it.**
- **Stay humble** — never assume the edge is solved; keep measuring.

This aligns with the honesty layer: we trade only where the *measured*
conditional base rate justifies it, size by (fractional) Kelly off that
measured edge, and re-measure continuously.

---

## Bottom line

The PVSRA **indicator** is precise and faithfully reproduced. The
**market-maker narrative** is an unprovable lens whose strongest claims are
unfalsifiable. **The honest, valuable move is to convert each teaching into a
measurable conditional probability** — recovery rates, retest base rates,
sweep/day-of-week/session-conditioned forward returns — and let real data say
which "clues" actually carry edge, on which instruments, in which windows.
That is the model we build next: a **conditional event-study engine**, not a
black box that promises riches.
