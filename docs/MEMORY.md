# Kudbee Quant — Memory Layer

> **Persistent, git-versioned memory.** The remote container is ephemeral; this
> file (and the journal) is what survives across sessions. It records what we
> have *learned and tested* so we never re-derive it or re-test dead ends.
> The thesis of this whole project, in one line: **the rules are commodity —
> the edge is in the reasoning and the execution.**

_Last updated: 2026-06-09._

---

## 0. THE OPERATING MODEL (the click — read this first)

**Direction = the human read. Scalping = the bot's execution.** These are
SEPARATE jobs. A skilled discretionary read (Tino-style, or KudbeeX) sets the
HIGH-PROBABILITY DIRECTION for a symbol ("SOL going down to ~62"). The bot then
takes only confluence-R scalps THAT AGREE with that direction — trading WITH the
identified market-maker momentum, never against it.

Why this is right (and why it took a while to click): when the ENGINE picks
direction from confluence, the edge is modest and regime-dependent. But the
data already shows the with-direction side is far stronger (downtrend: short-only
scalps +0.267R vs +0.159R both-sides). When the human supplies the correct
direction, the bot's *execution* edge (limit-retrace, 3R, maker) compounds on
the right side. Human judgment (direction) + machine discipline (execution +
measurement) = the real product. Neither alone is the edge.

Implementation: `kudbee_quant/bias.py` (BiasBook, data/biases.json) + the paper
loop's direction gate. CLI: `bias-set SOLUSDT short --target 62 --note "..."`,
`bias-list`, `bias-clear`. The hourly Action scalps WITH active biases.

---

## 1. The validated strategy (current best — tested, not believed)

> **1h timeframe · confluence ≥ 50% (of ~10 factors) · 3R target · LIMIT entry
> on a 0.25-ATR retrace (maker fill) · both directions · sized small.**

- Walk-forward, 6 folds × 6 assets incl. **gold & S&P** (correlation 0.00):
  **83% of cells positive, median ~+0.19–0.24R/trade** at realistic maker cost.
- It came from **execution** (limit-retrace) + **R:R** (3R), NOT from adding
  signals. Market-order/taker execution turns it **negative** — execution is the
  edge.
- **Regime-dependent & with-trend:** short-led in downtrends, long-led in
  uptrends; thinner in chop. Real drawdowns (−15 to −31R) → size small.
- **Status:** validated *backward*. Forward/paper proof is accumulating via the
  hourly GitHub Action (`paper-scan` → `journal-check` → `journal-score`). No
  real capital until forward R holds.

The engine: `kudbee_quant/confluence/stack.py` (factors → score),
`backtest/bracket.py` (R, limit-retrace, confirmation), `paper/` (forward loop).

---

## 2. Honest scoreboard — what we tested (DON'T re-test these)

**Beats the null (keep):**
- The 10-factor confluence direction (trend/level votes) — modest directional edge.
- **Limit-retrace entry** — ~doubled expectancy + maker fills. THE lever.
- **3R > 2R** with the limit entry (asymmetric R:R).
- **Range exhaustion** (forward range shrinks as % ADR used rises) — real, but a
  known volatility effect, non-directional.

**Does NOT beat the null (proven dead — stop adding these):**
- Adding factors: **Order Blocks, macro (DXY/ES/VIX), BOS/CHoCH structure,
  funding rate, RSI divergence** — ALL diluted the edge. The 10-factor set is
  **saturated**; more price-derived factors hurt.
- **Multi-timeframe (1h+4h) agreement** — reduced edge (1h already encodes the
  HTF trend; filters out reversal trades). Vol 10's MTF win-rate claim did not
  replicate.
- **PVSRA-MM strategy** — crypto beta, not alpha.
- **Vector "always recovered"** — recovers at the same rate as a random zone (no
  magnet edge).
- **Daily-open 2nd-test / Tuesday / NY** slices — noise (too few events).
- **Confluence-as-reversal** (does confluence raise reaction?) — flat ~50%.
- Hand-flipping "contrarian" factors — overfits (factor signs non-stationary).

**Mixed / open:**
- **Candlestick confirmation** at the entry ("stopping candle") — helped the
  aggregate walk-forward (+0.243→+0.324R) but hurt SOL held-out. Configurable
  option, NOT default; A/B it once forward data exists.

**Killed by reality:**
- **1-minute scalping** — costs (0.7–2.6 R/trade) dwarf any edge. Dead.

---

## 3. Why the edge is reasoning + execution (the project's core lesson)

We extracted and mechanized the ENTIRE Traders Reality / ICT / BTMM corpus
(research Vols 1–10) and tested it. **The mechanical rules do not beat the
null.** What *did* matter:
1. **Execution** — entering on a limit retrace at the level (maker), not chasing.
2. **R:R discipline** — small fixed losses, bigger asymmetric wins (3R).
3. **Direction selection** — the confluence picks the right side by regime.
4. **Discretionary reading** — KudbeeX's own live calls (DOT $1.84→$0.60, SOL
   shorts) have played out; the *reading* may carry edge the mechanics can't.

So the next real gains are in **better execution and capturing the reasoning**,
not more indicators.

---

## 4. Traders Reality / Tino methodology (distilled, for reference)

- **Hybrid System** = PVSRA (vector candles) + Steve Mauro BTMM (session
  timing / market-maker cycle). Lineage: Wyckoff → Tom Williams (VSA) → Ney.
- **PVSRA vector candles:** climax (green/red) = volume ≥ 2× the 10-bar avg
  OR vol×spread = highest of 10; above-avg (blue/violet) = ≥ 1.5×. Faithfully
  in `signals/pvsra.py` (+ Pine).
- **Sessions (NY local / UTC):** Asian (accumulation) → London (manipulation /
  stop hunt) → New York (distribution / real move). London–NY overlap
  (08:00–11:00 ET) = peak liquidity. Frankfurt 07:00 GMT, London 08:00 GMT.
- **Brinks box** = the ~1h pre-session window where stops are hunted ("set-up
  for the session"). EU Brinks 08:00–09:00 UTC (DST-off). Trade the reversal
  AGAINST the initial breakout (Judas swing).
- **Key levels:** daily/weekly/monthly open, PDH/PDL/PWH/PWL, session highs/lows,
  ADR projections, pivots (PP/R/S), EMA stack (5/13/50/200/800), volume nodes,
  psychological round numbers, vector zones. (All computed in `levels/`.)
- **Market-open game plan (his videos):** mark the levels, expect a session-open
  stop hunt / Frankfurt trap, then the real move; trade with MM momentum, not
  against it; "the fast move is the false move."
- **His reasoning principles (the part that matters):** work WITH the market
  maker's intent; few high-probability trades in premium windows; clues/“traps”
  before moves; percentage-of-R goals over dollar amounts; stay humble.

---

## 5. Video library (Traders Reality — transcript status)

| ID | Title | Transcript |
|---|---|---|
| aYnclx5ZI6U | Market Open Game Plan: Key Levels & What to Expect | ❌ blocked |
| 8h3Q6ZS3zZ8 | HOW TO TRADE BITCOIN (NEW YORK SESSION) July 06 | ❌ blocked (live session video) |
| msOFp7XP1EY | Clues For Moves In BITCOIN | ❌ blocked — topic: "clues" = **vector candles** |
| wNJ1oGVUoSI | How To Project Bitcoin Price? (30Min Lesson) | ❌ blocked — topic: **unrecovered-vector projection** |

> **Limitation confirmed twice:** I cannot watch video/audio, and YouTube +
> every transcript service are blocked from this environment (captcha /
> JS-rendered captions). Reliable path: open the video → "…more" → **Show
> transcript** → paste it here, and I'll distill the *reasoning* into this file.

**Key cross-reference (what the two lessons teach vs. what we measured):**
- "Clues For Moves" teaches **vector candles** as the clue to MM intent. We tested
  vectors as a confluence factor and as a recovery magnet → no edge over null.
- "How To Project Price" teaches **unrecovered-vector targets** ("recovers the red
  vector like clockwork"). **We measured this directly:** vectors recover at the
  SAME rate as a random equidistant zone (≈92% vs 93% over 60d) — no projection
  edge. So the *mechanical* claim of this lesson is already a NULL in our tests.
  The value Tino adds is the *discretionary* choice of WHICH zone, in WHAT
  context — the reasoning, not the rule.

---

## 6. KudbeeX's own reads & calls (the discretionary track record)

- **DOT/USDT (2025-12-31):** weekly imbalance-fill, $1.84 → target $0.60.
  Playing out (reached ~$0.95). *Directionally correct, in progress.*
- **SOL/USDT (2026-06-09):** short scalp off daily-open rejection + 50-EMA wick,
  target the psych high ~64.5 then ~62. Logged (`reach_below 64.5`). Open.
- Reasoning style: session-open stopping candles, vector recovery %, NY range
  high / Brinks confluence, bull-trap detection.

> These get logged in `data/journal.json` and scored forward — the honest test
> of whether the discretionary *reading* has edge (the open question).

---

## 7. Open hypotheses (next, ranked by honesty-of-upside)

1. **Forward-validate the live strategy** (paper loop running) — the only proof
   left that matters. Then A/B candlestick confirmation on live data.
2. **Log Tino's daily calls** (if subscribed) and score his real forward R — the
   rigorous way to value his reasoning / a paid channel.
3. **Capture reasoning from transcripts** (when pasted) — mine his market-open
   DECISION logic, not level names.
4. Better entry execution variants (partial profits 50/25/25, ATR-trailing) —
   Vol 10 trade-management ideas, tested honestly.

---

## 8. How this memory grows

Append here whenever we (a) validate or kill a hypothesis, (b) distill a video/
lesson, (c) log a real call + outcome. Keep the honesty layer: record what
*failed* as loudly as what worked, so we never burn time re-testing dead ends.
