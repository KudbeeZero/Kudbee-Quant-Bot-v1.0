# Kudbee Quant — Memory Layer

> **Persistent, git-versioned memory.** The remote container is ephemeral; this
> file (and the journal) is what survives across sessions. It records what we
> have *learned and tested* so we never re-derive it or re-test dead ends.
> The thesis of this whole project, in one line: **the rules are commodity —
> the edge is in the reasoning and the execution.**

_Last updated: 2026-06-16._

---

## STANDING USER PREFERENCES (honor every session)

- **Don't re-raise fees on positive results (2026-06-16, user-set).** The plan is
  to trade the **zero-fee assets** (the `YAHOO:` TradFi venue — Nasdaq / ES / index /
  forex; `VENUE_FEE_PCT["tradfi"] = 0`). The fee model is already understood and
  documented (§25/§26); do **not** volunteer fee caveats / exchange-fee rundowns
  when a reading comes back positive. Assume fees are off the table unless the user
  explicitly asks about a fee-paying (crypto taker) venue.
- **Don't over-caution / re-litigate (2026-06-16).** This is the user's own research
  sandbox — not a public signals/advisory product. Skip "this is/ isn't financial
  advice" framing and compliance hand-wringing; execute the directed change and report
  results honestly. Iteration + honest measurement is the whole point.

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

## 9. Timeframe survey (where the edge lives) — 2026-06-09

Validated config across timeframes (walk-forward, 3R, 0.25-ATR limit, 0.04% maker,
realistic per-TF cost):

| TF | BTC | SOL | note |
|----|-----|-----|------|
| 7m | +0.250R (67%) | -0.121R (33%) | asset-dependent; cost fee_r ~0.10-0.15 |
| 15m | -0.054R | +0.055R | weak/negative (cost+noise) |
| 30m | -0.077R | -0.101R | NEGATIVE — do not run standalone |
| **1h** | **+0.252R (100%)** | +0.066R (67%) | **sweet spot** (robust + sample) |
| 2h | +0.189R (83%) | +0.018R | viable, fewer trades |
| 3h | +0.464R (81 tr) | +0.398R (81 tr) | high exp, small sample |
| 4h | +0.102R (50%) | +0.232R (83%) | viable, fewer trades |

Conclusion: 1h is the core; **2h/4h are viable ADDITIONS** (more chances, fewer
trades) -> paper loop now scans 1h+2h+4h. 15m/30m FAIL as standalone strategies;
7m is asset-dependent. NOTE: this tested each TF as a STANDALONE strategy. The
trader's real method (1h direction -> drop to 15m/1m to TIME the entry) is NOT
this -- that's entry refinement, still untested and the next build. Tool:
`tf-survey SYMBOL`.

## 10. Stop/target geometry + TradingView indicator — 2026-06-09

STOP/TARGET (1h, limit-retrace, maker, walk-forward): lowering R:R by widening
only the stop (3:1.2=2.5R, 3.2:1.5=2.1R) HURTS per-risk expectancy (+0.147/+0.175
vs +0.204 at 3:1). The WIN is to widen the stop AND scale the target to keep ~3:1:
1.5-ATR stop / 4.5-ATR target = +0.235R (vs +0.204 at 1.0/3.0) AND +0.353 ATR
absolute, higher win rate, lower cost-per-R. -> Adopted 1.5-ATR stop default
(paper + API + indicator). For a higher win rate (sanity), 1.5/3.2 (2.1R) gives
41% wins at +0.175R.

VECTOR ENTRY (the cookie-crumb read): green-climax-in-premium / red-in-discount
lifted naive vector-fade from -0.10R to +0.006R (breakeven, still null); rejection
wick made it worse. -> Use as the human's contextual READ (bias), not a bot rule.

PROJECT SYNDICATE: real ~69K-follower TradingView SMC vendor; paid "AI algo" MT5
bots (~5k USDT, anchored "20k value"). Self-described BLACK BOX (no verifiable ML),
no audited live track record, all win-rates self-reported (some via paid PR). CFTC
flags "AI predicts price"+"guaranteed returns" as fraud markers; >95% of TV
"predictive" indicators repaint. His FREE open-source scripts are conventional SMC
(double-top detector, liquidity zones) -- inspectable, not magic. Verdict: no $10k
crystal ball; only borrow specific readable mechanisms AFTER they beat our null.

TRADINGVIEW INDICATOR: pinescript/kudbee_confluence.pine -- the 10-factor
confluence score + dashboard, PVSRA vector colouring, key levels, the limit-
retrace bracket, bias filter, and phone alerts. alert() fires a JSON webhook ->
POST /api/alert -> auto-logs a paper trade (chart setup -> journal -> forward
score). The engine now lives ON the trading screen.

## 11. Project Syndicate pattern + MTF entry refinement — 2026-06-09 (final session tests)

PROJECT SYNDICATE double-top/bottom (his signature "Pattern Recognition"):
- FADE equal highs/lows (enter early): +0.046R, 58% positive — weak/breakeven.
- NECKLINE BREAK (wait for confirmation): +0.181R, 75% positive — REAL edge
  (first borrowed mechanism to beat the null; still < confluence-R +0.235R and
  likely correlated). Lesson reinforced: the CONFIRMATION/execution timing is the
  edge, not the pattern (same as limit-retrace).

MTF ENTRY REFINEMENT (1h direction -> 15m timing, the top-down method):
- 15m alone: -0.045R. 15m GATED by 1h direction: -0.013R. Both NEGATIVE -- the
  mechanical 15m entry is not viable (cost+noise), and the 1h gate doesn't rescue
  it. CONCLUSION: bot executes on 1h/2h/4h; the lower TFs are for the HUMAN's
  discretionary entry timing (stopping candle, cookie-crumb vectors), which the
  machine can't bottle. Consistent with the whole project.

## 12. TP1/TP2 partial profit + MFE survival + stocks — 2026-06-09

The user asked to "set up target one and target two for profit taking" and to
measure how often the FIRST target is hit vs the FULL one. Built it honestly.

WHAT WAS BUILT (opt-in; full-3R stays the validated DEFAULT):
- bracket.py: `tp1_r`/`tp1_frac`/`be_after_tp1` (scale out, move stop to BE after
  TP1) + `bracket_excursions()` (per-trade Max Favorable Excursion in R).
- journal.py: Prediction.tp1/tp1_frac/be_after_tp1/tp1_filled_at + `_resolve_partial`
  (stateless blended-R resolution; banks TP1, rides rest, BE stop).
- paper.py: optional `tp1_r`/`tp1_frac`. Pine: optional TARGET ONE line.

MFE SURVIVAL (how often each R-target is reached before the 1R stop; just counting
— SOLID). 1h, >=50% confluence, 1.5-ATR stop, 0.25-ATR limit retrace:
  CRYPTO (n=676):  1R=58% 1.5R=46% 2R=35% 2.5R=28% 3R=22% 4R=14%
  STOCKS (n=904):  1R=51% 1.5R=41% 2R=33% 2.5R=27% 3R=21% 4R=12%
  => TP1 at 1.5R is hit ~2x as often as the full 3R target. Taking something off
     the table is real — but it CAPS the winners that pay for the losers.

REAL EXPECTANCY (proper bracket_backtest — NOT the -1R-on-miss proxy, which is too
pessimistic and wrongly printed negative). Pooled, by fee:
                       zero    ~0.02% (stock spread)   0.04% (crypto maker)
  CRYPTO full-3R:    +0.270R        +0.249R                +0.227R
  CRYPTO scale 2R+4R:+0.235R        +0.209R                +0.182R
  STOCKS full-3R:    +0.168R        +0.148R                +0.129R
  STOCKS scale 2R+4R:+0.143R        +0.119R                +0.095R
HONEST VERDICT: full-3R has the HIGHEST expectancy and best return/drawdown (~9.7
vs ~5-6 for scale-out). Scaling out RAISES win-rate (39%->43-48%) and feels better
but costs ~0.04-0.07R of expectancy. Use TP1 for psychology / "free trade" comfort,
not as an edge enhancer. STOCKS work too (commission-free now): positive but a bit
lower than crypto (+0.13-0.17R). LOWER FEES improve everything — the user is right.

## 13. Dollar sizing on $100 + double-top/bottom + S/R — 2026-06-09

300-TRADE DOLLAR SIM ($100 start, validated 1h confluence, 0.04% maker, last 300
trades across top-10; the SAMPLE had +0.264R expectancy, 43% win, 1.45% mean stop):
  10x FULL notional (~14%/trade): -> $9.90  *** ACCOUNT BLOWN *** (maxDD -99%)
  10% risk/trade:                 -> $9.81  *** BLOWN ***
  2%  risk/trade:                 -> $416   (+316%, maxDD -64%)
  1%  risk/trade:                 -> $212   (+112%, maxDD -40%)
THE LESSON (biggest of the project): a POSITIVE-edge system still BLOWS UP at 10x
full notional — variance ruins you before the edge pays. Same trades, only sizing
differs. RIGHT SIZE: to risk 2% with a ~1.4% stop you use ~1.4x equity, NOT 10x.
10x leverage is a CAP/tool, never the bet size. Recommend 1% risk/trade on crypto
(DD still -40% at 1%; crypto is brutal). Code: backtest/money.py (trade_log +
simulate_account, modes full_notional / fixed_fractional). Tested.

DOUBLE-TOP/BOTTOM NECKLINE BREAK (scenarios/patterns.py, same limit-retrace exec):
  +0.111R mean, median +0.103R, 80% of top-10 positive, 538 trades. A REAL but
  SECONDARY edge (< confluence +0.26R) — confirms §11: trade the BREAK not the
  touch. support_resistance() exposes nearest swing-high/low + equal-level shelves.

## 14. Averaging-down verdict + net-exposure guard — 2026-06-09

20/20/20/40 AVERAGE-DOWN test (2y SOL, $1000, no leverage, same signals):
  single defined-risk @1x:      $622 (-38%), 34% win, -73% DD
  avg-down WITH hard stop @1x:  $879 (-12%), 82% win, -36% DD, worst -13.8%
  avg-down NO stop @1x:        $1185 (+18%), 94% win, -51% DD, worst -24.8%
  avg-down NO stop @3x lev:      $75 (-93%), 92% win, -94% DD, worst -65.9% *BLOWN*
VERDICT: the high win-rate is a LIAR — averaging down wins small constantly then
one trend erases it; survivable ONLY with a hard stop + zero leverage; lethal the
instant leverage touches it. The real fix for all of them is SIZING (single-entry
@1% risk made +51%, §13), not the entry style. Don't build it into the system;
documented as a tested warning.

NET-EXPOSURE GUARD (kudbee_quant/exposure.py): two-sided trading IS supported (open
trades keyed by symbol+timeframe, so 1h-long + 5m-short coexist as independent
trades). symbol_exposure/portfolio_exposure tally long/short open+pending brackets;
gross_risk=(nL+nShort)*risk, net_risk=|nL-nShort|*risk. paper_scan now SKIPS a new
trade if it would push a coin's GROSS risk over max_symbol_risk (default 2% at 1%/
trade). CLI `journal-exposure`; also in /api/journal. Tested.

## 15. Lab build-out + LONG vs SHORT scenario — 2026-06-09

LONG vs SHORT vs BOTH (top-10, 1h, validated, 0.04% maker, full history ~2014 trades):
  LONG  : 937 trades, +0.048R, 34% win, +45.0R total
  SHORT : 1077 trades, +0.224R, 41% win, +240.9R total
  BOTH  : 2014 trades, +0.142R, 37% win, +285.9R total
Read: this window was crypto-WEAK so SHORTS carried it; the point is the system is
SYMMETRIC and regime-adaptive (in a bull window longs carry). Two-sided is WHY it
stayed green while assets fell (cf. §13 SOL: +51% vs buy-hold -61%). Don't assume
shorts always win — regime-dependent. Lab now plots long/short/both equity curves.

NEW (all in main, tested):
- journal Prediction.source ("bot" vs "human"); j.source_record() + resolved_series().
  CLI `read-add` logs YOUR discretionary calls (scored apart from the bot). First
  human read logged: ZEC 1m short off daily-open rejection (453->446).
- Lab page additions (assets/js/lab.js, CSP-safe): long/short equity chart, live
  FORWARD track-record curve + bot-vs-human split (from /api/journal), position-size
  calculator, live exposure panel, exchange-fee venue picker (interpolates the
  measured fee curve). /api/journal now returns by_source + resolved_series +
  exposure + total_gross_risk_pct.

## 16. Edge-booster lab — what lifts expectancy, what HURTS — 2026-06-09

Tested ~12 entry filters across top-10 1h (11,465 trades, baseline +0.091R, 36% win):
WINNERS (real):
- HTF TREND FILTER (price vs 800-EMA agree): +0.141R (Δ+0.050), keeps 83%. Counter-
  trend signals were NEGATIVE (-0.146R). ROBUST: +0.054R/+0.046R in both split-halves.
  -> IMPLEMENTED as confluence_position(trend_align=True) + paper_scan(trend_filter=True),
     CLI --trend-filter, now ON in the forward Action (setup tagged "_tf").
- killzone (London/NY-brinks/macro): +0.144R (Δ+0.053), keeps 25%. Tino's sessions hold.
- WITH premium/discount (long in discount/short in premium): +0.151R (Δ+0.060), keeps 10%.
- strong confluence >=70%: +0.176R (Δ+0.085), keeps only 5% (confluence IS ~monotonic).
- STACKED trend+killzone +0.185R; trend+strong +0.210R; trend+Tue-Fri +0.271R (38%).
HONEST NEGATIVES (go AGAINST intuition — kept as findings):
- "near daily open <=0.5ATR" (mechanical): +0.014R (Δ-0.078) — HURTS. The bot blindly
  trading at the daily open is chop; the user's daily-open edge is the DISCRETIONARY read,
  not a mechanical proximity rule.
- "ADR room left <70%": Δ-0.025 — slightly hurts. EMA cloud / structure_dir agreement:
  ~0 effect (already baked into confluence). climax-vector-at-signal: only Δ+0.016.
SUGGESTIVE but data-mining risk (need walk-forward before trusting): day-of-week (Mon
-0.217R worst, Thu +0.256R / Tue +0.239R best), NY hours 1-4 (+0.18..+0.22R) vs 14/22/23
(negative). Tino's Tuesday/session lore shows up but DON'T hard-code yet.

PROJECT STATE: complete & validated-backward; forward paper proof accruing via the
hourly Action (top-10 majors, 5m/15m/1h/2h/4h, TREND-FILTERED). Everything in main: engine +
website + Live Signals + The Lab (interactive charts/calculator/venue/exposure/
forward-record) + API + TradingView indicator + alert->journal webhook + bias layer
+ TP1/TP2 partials + dollar sizing + double-top/bottom + S/R + net-exposure guard +
human-read scoring + HTF trend filter + research Vols 1-10. Ready to archive.

## 17. Overnight research harness — autonomous honest hypothesis testing — 2026-06-09

The user asked, before bed, for an overnight build that "spins up agents to find
out-of-the-box ways to raise the % / chances of our trades" so the algorithm is
stronger by morning. Built it the ONLY honest way: not by bolting on believed
"win-rate boosters" (the project's cardinal sin — §2), but as a repeatable worker
that TESTS candidate edges against the shipping baseline and records the verdict.

WHAT WAS BUILT:
- `scripts/overnight_candidates.py` — a registry of candidate edges, each a
  function `(df, scored, base_sig) -> (signal, size, overrides)`. Every candidate
  lives in execution / entry-timing / regime / sizing (where edge has historically
  been), NEVER "one more confluence factor". Seeded from two parallel research
  agents + my own; 30 candidates so far.
- `scripts/overnight_research.py` — the harness. Pools trades across the top-10
  majors, compares candidate vs the shipping baseline (1h, ≥50% conf + trend
  filter, 0.25-ATR limit, 1.5-ATR stop, 3R, maker), and runs a SPLIT-HALF
  robustness check. Verdict = WINNER (ΔR≥+0.015 AND both halves positive),
  SUGGESTIVE, NEUTRAL, HURTS, or THIN. Queue in `data/overnight_queue.json`,
  machine log in `data/overnight_results.json`, human report in
  `docs/research/overnight_findings.md`. Per-candidate try/except + parquet cache
  fallback so a bad candidate or network blip can't kill a cycle.
- `tests/test_overnight.py` — contract tests (every candidate well-formed; gating
  candidates are a strict subset of the baseline; evaluator returns an honest record).

FIRST-NIGHT RESULTS (baseline pooled +0.166R, ~1577 trades, top-10 1h):
TWO WINNERS (beat baseline in BOTH halves — promising, NOT yet shipped; forward
paper-proof required before they touch the default, per the honesty contract):
- `clean_trend_stack` +0.115R (h1 +0.203 / h2 +0.009), keeps ~51% of trades →
  +0.281R. Only trade when the 13/50/800-EMA stack has been monotonically ordered
  10 bars AND the 13/50 gap is widening (a clean, separating trend, not a braid).
- `highvol_bigtarget` +0.067R (h1 +0.014 / h2 +0.133), keeps ~48% → +0.233R. In
  the high-vol regime (top-40% ATR%), aim for 4R instead of 3R — volatile regimes
  run further. (Note: h1 thin; treat as suggestive-strong.)
DEAD ENDS this sweep (logged so we never re-test — §2 discipline): vol_regime_mid,
vol_contraction, relvol_participation (and its quiet A/B), shallow & deeper
retrace (≈neutral), fast/slow time-stop, lowvol_smalltarget, round_number_entry,
voltarget_size, size_by_confluence (HURT badly −0.103R), variance_ratio_trend
(HURT −0.086 — the textbook regime filter did NOT help here), skip_overextended.
Reinforces the project thesis: most clever ideas fail; the survivors are about
REGIME SELECTION and EXECUTION GEOMETRY, not new signals.

HOW IT RUNS OVERNIGHT: this branch runs the harness hourly via the Claude `/loop`
(Binance is reachable from the container, verified). Each cycle drains ~3 queued
candidates, an idea-agent appends fresh candidate ideas to a backlog, results +
report are committed to `claude/overnight-algo-research-plan-hyqzf6`. NOT merged
to main / no live-capital change — winners must clear forward paper proof first.
NEXT (queued, needs a small engine extension): path-dependent EXECUTION variants
the agents flagged as highest-leverage — ATR/chandelier TRAILING stop, time-decay
target, MAE "give-up" early exit. bracket.py currently does fixed stop/target/
tp1/time-stop only; add trailing + early-exit, then test the same honest way.

## 18. Project Edge: meta-labeling + execution engine + 6-layer memory — 2026-06-09

A full-stack build (user asked for "something major / new logic"). The honest
verdict is the deliverable: we built sophisticated, correct infrastructure, and it
told us the truth — the two headline ideas are NULLS at the validated config, and
the multiple-testing ledger says our overnight "winners" are probably luck. That
is the project working as designed.

WHAT WAS BUILT (all tested; 156 suite green):
- backtest/resolver.py — ONE shared trade resolver. bracket.py AND journal.py now
  delegate to it (resolution logic was duplicated -> drift risk between backtest &
  live). Pure refactor, behaviour identical.
- Path-dependent EXITS on the resolver (off by default): chandelier TRAILING stop,
  MAE give-up, time-decay target. Threaded through bracket_backtest; candidates
  exit_trail_3atr / exit_mae_giveup / exit_time_decay queued for the loop.
- ml/ : labels.py (meta-labels = did the trade reach target before the 1R stop;
  causal feature frame from votes+levels), cv.py (purged + embargoed walk-forward,
  Lopez de Prado), meta_model.py (GBT + interpretable logit, scored OUT-OF-SAMPLE,
  win-rate-beats-base gated by Wilson CI). scikit-learn added.
- memory/ : the 6 layers formalized — registry.py (L4 strategies as objects),
  working.py (L5 biases + open hypotheses), reflection.py (L6 regime + overfit
  alarms + failure rollup), testing_ledger.py (family-wide deflated/BH-FDR).
  scripts/reflect.py + scripts/meta_eval.py.

HONEST RESULTS (top-10, 1h, validated config):
- META-LABELING at the 3R target: WEAK/NULL. GBT OOS AUC ~0.55; gating at
  prob>=0.7 lifted win-rate +0.068 but the Wilson CI did NOT clear the base rate
  (n too small). Logit top features: -atr_pct, +pct_awr_used, +in_overlap,
  +v_emastack. Infra is reusable for other labels (e.g. 1.5R, expectancy-positive).
- EXECUTION EXITS: trailing (-0.024 to -0.035R) and time-decay (-0.040R) HURT
  pooled expectancy; the fixed-3R fat tail pays for the losers (consistent with
  §10/§12). MAE give-up at 1.0R is a no-op (that IS the stop); 0.8R queued.
- MULTIPLE-TESTING LEDGER (the big honest win): of 32 candidates logged, 4 naive
  winners, **0 survive family-wide BH-FDR**; highvol_bigtarget (h1 +0.014/h2
  +0.133) and clean_trend_stack (h1 +0.203/h2 +0.009) flagged UNSTABLE across
  halves. Expected false winners under pure noise ~1.6. => Treat ALL overnight
  "winners" as UNPROVEN; forward paper is the only proof. This directly corrects
  the earlier "2-4 winners!" enthusiasm.

LESSON (reinforces the whole project): more machinery did not manufacture an edge.
The durable wins are STRUCTURAL — no backtest/live drift (shared resolver), a
reusable meta-labeling/CV rig for honest future tests, and a memory spine that
re-grades every result under multiplicity so we never mistake luck for edge.

## 19. THE LEAD: meta-gating lifts expectancy, cross-asset — 2026-06-09 (do not over-trust yet)

After §18's nulls, fixed the approach and found the first real signal of the whole
build. THREE changes mattered: (1) LABEL on realized PROFIT (realized_r>0), not the
rare 3R tag; (2) measure on R-EXPECTANCY, not hit-rate; (3) significance-test it.

RESULT (GBT meta-model, purged+embargo OOS, top-10 1h, 1.5R bracket):
  gate prob>=0.60 -> take 34% of trades, expectancy +0.219R vs +0.093R base
  (lift +0.126R), permutation p=0.007 (beats RANDOM selection of the same size).
  Monotonic across thresholds (0.50->0.65 all significant). Beats even the
  shipping 3R config (~+0.16R).
CROSS-ASSET HONESTY CHECK (the one that kills fake edges): train on CRYPTO only,
apply to STOCKS (SPY/AAPL/NVDA/MSFT/TSLA/AMZN, rho~0.15): gate prob>=0.60 ->
+0.379R on 17% of trades, lift +0.313R, p_perm=0.001. THE EDGE TRANSFERS across
asset classes -> it is not crypto-regime luck; the model learned something general
about which confluence setups are high quality. Note: logit (linear) shows NO
lift -> the edge is nonlinear interactions (watch overfit; that's why we permission
-test + cross-validate).

STATUS: a genuine LEAD, validated BACKWARD across two uncorrelated asset classes
with significance. NOT yet proven: forward paper. NEXT: wire a meta-gated 1.5R
variant into the paper loop as a SECOND tracked strategy and accrue forward R
beside the baseline; only then does it earn live capital. Code: kudbee_quant/ml/
(labels realized_r, meta_model expectancy_gate + permutation p). CLI:
python scripts/meta_eval.py.

ANTI-RECURRENCE (so §18's "lucky winners" never happen again): the overnight
harness verdict now REQUIRES a bootstrap p<0.05 on ΔR (plus both-halves robust)
to call anything a WINNER; the memory testing-ledger re-grades the whole family
under BH-FDR. Luck no longer earns the word "winner".

## 20. KudbeeX live read — BB-upper rejection short (SOL) + the setup, recorded — 2026-06-09

The user supplied a REAL annotated trade (two screenshots) and asked to record the
setup so we can measure and adjust the logic. This is the §0 operating model in
action: human reads direction, machine records + scores it.

THE TRADE (logged: journal id 84dcb6ce, source='human', scored forward):
- SOLUSD Perp SHORT, 20x, real fill 66.43 @ 06/08/2026 22:10 (UTC-5), #32007241.
- Live at log: price 66.14, PnL +7.88% (20x), liq 76.77, position $410.73.
- Logged as SOLUSDT 1h short, entry 66.43, target 64.5 (then 62), structural stop
  ~68.1 (reclaim of the upper band — inferred; he didn't state an explicit stop).

THE SETUP (his words, distilled) — "Bollinger-upper rejection / stopping candle":
1. A STOPPING CANDLE prints ABOVE the BB basis (mid), up near the UPPER band
   (chart: BOLL 26,2 → mid 66.91, upper 68.06; price had run to ~68.3).
2. Two "REVERSE HAMMERS" at the top = inverted-hammer / shooting-star candles
   (long UPPER wick, small body, little/no lower wick); one was green.
3. The NEXT bar GAPS DOWN (lower open / first bid lower), prints a solid body with
   a long upper wick and ~no lower wick → sellers in control.
4. ENTER short on the OPEN of that confirmation bar.
5. Confluence stack he cited: MACD bearish (DIF 0.04 < DEA 0.17, hist −0.25); KDJ
   bearish (K 40.25 < D 49.06, J 22.62); order book 65% sell / 35% buy.

MECHANIZED FOR TESTING: scripts/overnight_candidates.py `bb_band_reject` — a
STANDALONE BB(26,2) rejection reversal (shooting-star@upper → short, hammer@lower
→ long), enqueued for the overnight harness so we measure honestly whether the
mechanical core beats the shipping baseline. (If it doesn't, the edge is in his
READ/timing, not the rule — consistent with the whole project; we keep scoring his
calls via source='human'.)

HONEST RISK NOTE (project duty, §13/§14): this is 20x leverage. A positive-edge
setup still BLOWS UP at high leverage — liq here is only ~16% away (76.77). The
trade is green and the read is clean; the flag is about SIZE, not the setup. The
documented stance remains ~1% risk/trade, leverage as a tool not the bet size.

## 21. KudbeeX 'fast-fail' early-exit theory — measured — 2026-06-09

His theory: with higher leverage, cut the loss small by EXITING EARLY if the trade
isn't going your way within the first few candles (keep a stop for a bad candle).
"You should know quickly if it's working." Tested on the validated 1h (his "1-3
minute" gut is a 1m idea; 1m is dead for us, §2 — the principle maps to the first
2-3 bars of whatever TF you trade). Built on the resolver's mae_giveup exit.

RESULT (top-10, 1h, ~2000 trades):
                              expR    win   avgLoss  worst   std
  baseline (1.5 stop/3R)     +0.158   38%   -0.99   -1.20   1.63
  show-me: not +0.5R by bar3 +0.113   38%   -0.76   -1.18   1.38
  show-me: not +0.3R by bar2 +0.116   37%   -0.74   -1.17   1.38
  tight 1.0 stop             +0.185   34%   -1.04   -1.30   1.78
  tight1.0 + show-me bar2    +0.175   34%   -0.92   -1.30   1.67
HONEST VERDICT (applying §20-era anti-luck discipline):
- The EXPECTANCY differences (~0.04R) are WITHIN NOISE (SE≈0.047 at n≈2000) — do
  NOT claim fast-fail raises return.
- What IS real + structural (not statistical luck): it SHRINKS the loss (avg loss
  -0.99 -> -0.76R) and cuts VARIANCE ~15% (std 1.63 -> 1.38). Edge/variance
  (Kelly-ish) is flat-to-better -> you can SIZE UP for the same risk-of-ruin. So
  this is a RISK-EFFICIENCY lever, exactly right for a leverage style — not a
  bigger-return edge.
- The TIGHT 1.0 stop raises expectancy but ALSO worst-case (-1.30R, gap-through)
  and variance -> it FIGHTS leverage safety. Keep the 1.5 stop + the show-me exit.
QUEUED for the full significance gauntlet (bootstrap p + both-halves): candidates
exit_showme, exit_tight_showme (scripts/overnight_candidates.py).

## 22. Leverage / risk-of-ruin math (2 research agents) + the SAFE-LEVERAGE answer — 2026-06-09

Two web-research passes (cited below) turned KudbeeX's "smaller losses → safer
leverage" intuition into computable math. Built kudbee_quant/risk.py (Kelly,
risk-of-ruin, Vince optimal-f, vol-target, perp max-safe-leverage) + tests +
scripts/risk_report.py. Per-trade MAE/adverse-move added to ml/labels.trade_outcomes
(measured ONLY while the position is open — bug fixed: was scanning the full window).

THE NUMBERS (validated strategy, top-10 1h, real distribution):
- mean +0.158R, std 1.63. Full Kelly f* ≈ 0.066 (m/s²). => trade QUARTER-KELLY ≈
  1.65% risk/trade. optimal_f 0.079 (a CEILING, never a target).
- **MAX SAFE LEVERAGE ≈ 9x** to keep P(liquidation) < 1% over the sample
  (liq_distance = 1/lev − MMR; fed REAL per-trade adverse-% excursions). 20x is
  ~2x above this ceiling — the ~5% liq buffer at 20x ≈ a normal bad-trade wick.

KEY HONEST + COUNTERINTUITIVE FINDING: the fast-fail show-me exit (§21) does NOT
raise the liquidation ceiling (both 9x). Liquidation is an INTRA-BAR wick event;
a close-based early exit can't prevent it. Fast-fail smooths the EQUITY CURVE
(std 1.63→1.38, MC ruin-DD 16.3%→15.1%) and lifts Kelly-safe size ~18% in theory,
but for LIQUIDATION safety only a tighter INTRA-BAR hard stop or LOWER LEVERAGE
works. So: size to ~quarter-Kelly (~1.6%/trade) and cap leverage ~8–9x, not 20x.

WHAT THE LITERATURE SAYS TO BUILD NEXT (encodable, queued/flagged):
- CONSTANT-VOL position sizing (Barroso-Santa-Clara; Moskowitz-Ooi-Pedersen): size
  ∝ target_vol/realized_vol — strongest, most-replicated Sharpe evidence; de-levers
  on vol spikes (the #1 perp survival behavior). NOTE: our harness judged
  voltarget_size as "HURTS" on RAW MEAN-R — the WRONG lens; it's a VARIANCE
  reducer. ACTION: add risk-adjusted metrics (Sharpe/maxDD/Kelly) to the harness so
  variance-reducers are judged honestly (next build).
- MAE-percentile stop (Sweeney): stop at ~85th pct of WINNERS' MAE (use our mae_r).
- Vol-expansion exit (Daniel-Moskowitz panic state): exit non-progressing trade if
  ATR_now/ATR_entry ≥ ~1.5-2.
- Kaminski-Lo theorem: stops add return only in MOMENTUM regimes, cost in random
  walk → gate aggressive exits by a trend filter. CPPI / drawdown floor for sizing.

SOURCES: Kelly (Wikipedia; Thorp f*=μ/σ²; MacLean-Ziemba-Blazenko frac-Kelly);
Vince optimal-f (Mathematics of Money Management); Kaminski & Lo "When Do Stop-Loss
Rules Stop Losses?" (JFM 2014); Daniel-Moskowitz "Momentum Crashes" (JFE 2016);
Barroso-Santa-Clara "Momentum Has Its Moments" (JFE 2015); Moskowitz-Ooi-Pedersen
"Time Series Momentum" (JFE 2012); Sweeney MAE; perp liq mechanics (MetaMask/Bybit).

## 23. Harness upgrade: risk-adjusted verdicts (Sharpe/DD) + the honest re-grade — 2026-06-09

Acted on §22's lesson: the overnight harness now records, per candidate, the
per-trade SHARPE (mean/std), return STD, and MAX DRAWDOWN in R — and adds a
RISK-REDUCER verdict (flat mean-R but std down >=5% AND Sharpe up AND drawdown
shallower). scripts/overnight_research.py evaluate() + findings table; tests added.

HONEST RE-GRADE (the discipline working a 2nd time — prevented over-claiming):
the hypothesis "we wrongly rejected variance-reducers on mean-R" did NOT survive
the proper risk-adjusted test:
  voltarget_size:    dR -0.052, dSharpe -0.010 (per-trade std 1.63->1.24, DD
                     -24.8->-20.1) — DD better but Sharpe flat-negative; NOT a win.
  exit_showme:       dR -0.060, dSharpe -0.025, DD -24.8->-30.9 (WORSE) — trades
                     more often, so cumulative drawdown deepens. NOT a clean reducer.
  exit_tight_showme: ~flat mean/Sharpe, DD -37.8 (worse).
LESSON: per-trade std reduction does NOT automatically improve Sharpe or cumulative
drawdown, because exits change trade FREQUENCY/sequence. CAVEAT (next step): true
vol-targeting's benefit appears in COMPOUNDED equity with position sizing, which a
per-trade-R harness can't fully capture — to test it properly, evaluate on the
sequenced/compounded equity curve (backtest/money.py simulate_account), not pooled
per-trade R. That is the honest next build.

## 24. KudbeeX weekly-cycle + NY-reversal market model (recorded) — 2026-06-09

Live read while the NY session opened (SOL ~65.8, −1.5% on the day; his short from
§20 @66.43 working, grinding toward 64.5). Recording his DISCRETIONARY market model
(this is the reasoning layer — the project's stated edge, §3):

THE MODEL (his words, distilled):
- NY session is "picking up the trend" BUT "New York is good for rehearsals — the
  NY reversal": the NY open often FAKES the prior direction then reverses. Don't
  assume the first NY move is the real move ("the fast move is the false move", §4).
- WEEKLY MARKET-MAKER CYCLE (classic Steve Mauro / BTMM, §4): "Mondays are always a
  false move"; a MIDWEEK REVERSAL is common (down day midweek, up the next); Fridays
  are often profit-running OR a managed price-increase into the close.
- Net live thesis: possible down day today, bounce tomorrow, Friday resolves
  (profit-take or markup).

CROSS-REFERENCE TO WHAT WE'VE MEASURED (honest, so we don't re-chase noise):
- Day-of-week (§16, edge-lab): SUGGESTIVE — Mon worst (−0.217R), Thu/Tue best
  (+0.24–0.26R) — but flagged DATA-MINING RISK; needs walk-forward before trusting.
- NY / Tuesday daily-open slices (§2): came back NOISE (too few events) as raw
  mechanical filters. The KILLZONE/session filter (§16) DID help (+0.144R, London/
  NY-brinks/macro) — so SESSION TIMING carries signal even though calendar slices
  don't.
- His model is a SEQUENCE/regime (Mon-false → midweek-reversal → Fri-resolve), not a
  raw day dummy — that's a DIFFERENT, untested framing. The causal features already
  exist to test it: build_levels computes `week_phase`, `cycle_phase` (MM weekly
  template), `day_of_week`, `killzone`, `in_ny`, `minutes_into_ny`.

STATUS: recorded as an OPEN HYPOTHESIS (not a believed rule). To test honestly would
require a walk-forward "week-phase reversal" study (does fading the Mon/early-week
move, or the first NY thrust, pay OOS?) run through the significance-gated harness
(§23) — NOT a hard-coded calendar rule (§16/§2 caution). Offered; do on request.
Meanwhile it stays in the HUMAN read layer: his live calls are scored via
source='human' (journal), which is the rigorous test of whether the READ has edge.

## 25. REAL-EXECUTION confirmation of the §20/§24 SOL short + measured FEE rate (cost-model calibration) — 2026-06-09

The §20/§24 SOL short was NOT paper — it was a REAL live position, and we now have
the broker contract details (BTCC SOLUSD Perp, 9x, all Market Orders = TAKER).
This closes the loop: the discretionary read (§20 BB-upper rejection short @66.43)
was executed, scaled out into the 64.50 tap, then FLIPPED LONG at the lows — the
exact "green-vector reclaim of the low" bounce play discussed live.

LIVE FILLS (broker truth, not the journal estimate):
- SHORT, position #32007241, opened 06/08 22:10:13 @ avg **66.43** (matches journal
  84dcb6ce / §20 to the cent). Closed in two green tranches INTO the 64.50 tap:
    · 1.98 SOL @ 64.98 — 06/09 09:32:58 — P/L +0.04419 SOL — fee 0.000891 — o/n 0
    · 1.79 SOL @ 65.19 — 06/09 10:21:11 — P/L +0.03406 SOL — fee 0.0008055 — o/n 0
  Gross realized ≈ **+0.0782 SOL (~$5.1 @ ~$65)**, zero overnight/funding fees.
- LONG flip, position #32015403 (catching the bounce off Psy-Lo 64.50):
    · 1.15 SOL @ 65.19 — 06/09 10:19:43 — fee 0.0005175
    · 1.01 SOL @ 64.70 — 06/09 10:34:16 — fee 0.0004545
    · 1.03 SOL @ 64.72 — 06/09 10:36:07 — fee 0.0004635
  (Scaled out of short and into long around the SAME 64.7–65.2 zone — textbook
  "test the low, reclaim, ride back up". Longs left OPEN at log; not yet a tracked
  bracket because no stop/target was set — offer stands to log a resolvable one.)

MEASURED FEE RATE (the calibration that matters):
- **Taker = 0.045% per side (4.5 bps).** Verified on ALL 5 fills: fee(SOL) =
  amount(SOL) × 0.00045 exactly (e.g. 1.98 × 0.00045 = 0.000891 ✓). Margin(SOL) =
  amount / 9 (9x), also exact — so these screens are internally consistent.
- **Round-trip taker ≈ 0.09%.**
- Code currently assumes `FEE_PCT = 0.0004` (config/validated_defaults.py) =
  0.04% round-trip MAKER. Real TAKER is **2.25× that**. The strategy's edge depends
  on MAKER (limit-retrace) fills; any time a leg fills via market/stop (taker), use
  0.09% round-trip, not 0.04%. This especially threatens the cost-sensitive 5m/15m
  forward scalps — a market-order stop-out costs more than the model books.
- OPEN ITEM: we do NOT yet have the exchange's MAKER rate (all 5 fills were Market
  Orders). Need ONE limit-order fill screenshot to confirm whether FEE_PCT=0.0004
  is right for the maker leg, or whether it should move. Until then 0.0004 is an
  ASSUMPTION, 0.00045/side taker is a MEASURED FACT.

FEE BUDGET (his question — keeping costs low / vouchers):
- These 5 transactions cost **0.003132 SOL total ≈ $0.20** @ ~$65. A **$20 voucher
  ≈ 100× that batch ≈ hundreds of fills of runway** at this size. Fees are NOT the
  bottleneck at current size; SLIPPAGE + taker-vs-maker discipline is. The cheapest
  fee saving is structural: prefer LIMIT (maker) entries — already what the
  validated strategy (§1) does — and avoid market-order exits where possible.

## 26. ZERO-FEE TradFi campaign = a strategic unlock for the validated edge — 2026-06-09

Signed up to BTCC's promo: **0 fees on ALL TradFi perpetual-futures pairs**, start
**June 1 2026 (UTC+8)**, end date TBD (announced separately). Eligible: metals
(Gold XAUUSD, Silver, Platinum, Palladium, Aluminum), energy (Brent UKOIL, WTI
USOIL, NatGas), **global indices (S&P 500, Nasdaq 100, Dow, Nikkei, DAX, FTSE)**,
forex (EUR/GBP/AUD/NZD-USD), and US stock tokens (NVDA, TSLA, AAPL, MSFT, etc.).
NOT crypto — SOL/BTC perps still pay the 0.045%/side measured in §25.

WHY THIS IS BIG (not hype — it resolves the project's central fragility):
- §1's verdict is blunt: the edge IS the execution, and **market-order/taker cost
  turns the strategy NEGATIVE.** Fees aren't a tax on the edge; near the cost line
  they ARE the difference between + and −. §25 then measured real taker = 0.09%
  round-trip on crypto.
- The validated walk-forward (§1) was run on 6 assets **including GOLD and S&P 500**
  (corr 0.00 to crypto — genuine diversification). Those are EXACTLY the instruments
  the campaign zeroes out.
- So: the campaign offers a venue where the validated strategy runs at **0 cost on
  assets it's already proven on.** That flips the §1/§25 cost fragility from a
  liability into a tailwind — and the maker-vs-taker discipline stops mattering on
  those pairs (even a market exit is free during the promo).

ALREADY-PRESENT ENABLER: the ingest layer has a **`YahooClient`** (ingest/yahoo.py)
that fetches these instruments TODAY — `GC=F`/`GLD` (gold), `^GSPC`/`SPY` (S&P),
`USO`/`CL=F` (oil), `EURUSD=X` (forex). No new data vendor needed to forward-test.

HONEST CAVEATS (so we don't over-rotate on a promo):
- The fee waiver is TEMPORARY (end date unknown). Treat it as a forward-test window
  and an edge while it lasts, NOT a permanent assumption baked into the model.
- BTCC's TradFi perp price ≠ the Yahoo underlying exactly (SP500 token vs ^GSPC,
  XAUUSD vs GC=F): use Yahoo for SIGNAL/LEVELS, execute on BTCC; expect basis.
- TradFi has SESSION GAPS / RTH hours (unlike 24/7 crypto) — the level/range logic
  (NY-date ranges, killzones) must be checked against equity/futures sessions before
  trusting it there.

BUILT (2026-06-09) — zero-fee TradFi forward-scan is LIVE:
- `RouterClient` (ingest/router.py) gives the journal + paper loop ONE client that
  routes by spec: bare/`binance:` -> Binance, `yahoo:` -> Yahoo. `TradeJournal` and
  `paper_scan` now default to it, so a `yahoo:GC=F` trade RESOLVES against Yahoo, not
  Binance (backward-compatible: bare crypto symbols unchanged).
- `paper_scan` tags TradFi trades `*_tradfi` (setup label) + "[TradFi 0-fee venue]"
  in the note, so the cost-free book scores SEPARATELY from the fee-paying crypto one.
- The hourly Action (paper-trade.yml) now runs a 2nd scan after crypto: gold (GC=F),
  silver (SI=F), S&P (^GSPC), Nasdaq (^NDX), Dow (^DJI), WTI (CL=F), Brent (BZ=F),
  nat-gas (NG=F), EUR/GBP-USD — **1h only** (validated TF, Yahoo-supported, dodges
  session-gap noise on sub-hourly bars), trend-filtered, one commit for both books.
- Seeded live: first scan logged 4 shorts (GC=F/SI=F/CL=F/BZ=F, ~50% conf, with-trend).
- Tests: `test_router_client_dispatches_by_spec`, `test_paper_scan_tags_tradfi_venue`.
NET-OF-FEE SCORING (BUILT 2026-06-09, follow-up now CLOSED): the journal scores
per-venue NET of fees. `venue_of(p)` routes by symbol spec (`yahoo:` -> tradfi 0-fee,
else crypto), `fee_r_of(p)` converts the round-trip fee to R via the SAME cost model
as backtest/bracket.py (`fee_pct * entry / risk`, +½ round-trip if TP1 banked), and
`net_outcome_r = outcome_r − fee_r`. Fee rates live in config (`VENUE_FEE_PCT`):
crypto = `TAKER_FEE_PCT` 0.0009 (the MEASURED §25 taker — conservative/honest),
TradFi = 0. `scorecard()` gained `net_expectancy_r`/`net_total_r`; new `venue_record()`
splits gross→net by venue; surfaced in `cli journal-score` + `/api/journal` (`by_venue`).
Tests: 6 in test_journal.py. NOTE: as of build, ALL 14 resolved trades are crypto
(net −1.015R vs gross −0.846R; fee 0.169R/trade) — the TradFi book is still OPEN, so
the "TradFi net≈gross" contrast can't be SHOWN until those resolve. The censoring-bias
caveat below still applies: these resolved crypto trades are fast stop-outs, NOT an edge
readout.
STILL OPEN (honest): TradFi session/RTH handling in build_levels is unverified
(NY-range logic assumes 24/7) — watch the `_tradfi` record for level-quality artifacts
before trusting it.

## 27. Session Relay Protocol — one chat = one audited PR, with a handoff baton — 2026-06-09

Adopted a development PROCESS spine to match the memory spine. The container is
ephemeral, so we now treat each chat as ONE reviewed unit of work and make the
handoff an audited artifact, not trust. Full spec: `docs/SESSION_PROTOCOL.md`.

THE LOOP (human-triggered, auditor-GATED merge):
- New chat: SessionStart hook surfaces the baton (`docs/HANDOFF.md`) → `/handoff-audit`
  spawns an INDEPENDENT auditor subagent that reviews the PREVIOUS chat's PR diff
  vs. its claims (over-claiming, scope creep, untested assertions, security), runs
  tests, writes `docs/audits/<branch>.md`, and emits PASS/CONCERNS/FAIL.
- Merge of chat N's PR is GATED on chat N+1's audit (PASS → merge → sync main →
  start next branch). Nothing lands on `main` unreviewed.
- Chat end: `/closeout` asks the handoff questions, updates memory, opens exactly
  ONE PR, and writes the baton for the next chat (next branch + scope + risks).

WHY (the thesis applied to process): the significance gate + multiple-testing
ledger exist so we never mistake luck for edge. This is the SAME instinct applied
to CODE — an independent auditor on every handoff is the significance gate for the
dev process. CI (`ci.yml` tests) is the floor; the audit is the ceiling.

DECISIONS (his calls): auditor-GATED merge; auditor = in-SESSION subagent (no
API-key secret needed — recommended for the human-triggered, non-autonomous flow);
codified protocol he triggers (skills + hook), not a fully autonomous worker. A
CI-based audit Action (needs ANTHROPIC_API_KEY) was deliberately deferred — only
worth it if we later go autonomous.

INVARIANTS: one open PR at a time (don't start the next branch until the prior PR
merges + main syncs — prevents conflicting branch stacks); the baton is the single
source of truth for "what's next"; memory is read first, every session.

BOOTSTRAP NOTE: work BEFORE the introducing PR (§24–§26) was merged direct to
`main` pre-protocol; the one-PR-per-chat + audit-gate rules apply from that PR on.

STANDING REPLY FORMAT (his ask, now in `CLAUDE.md`): every working reply ends with
a **Summary** (what was actually done — honest, with test/commit state and anything
skipped) and a **Next** (the exact concrete action he should take next, recommended
default first). Honesty over optimism — surface failures in the Summary, don't bury.

## 28. A stale baton causes DUPLICATE builds — keep the baton current — 2026-06-10

Two parallel chats BOTH built net-of-fee scoring (§26 follow-up): an earlier chat in
PR #3 (`claude/handoff-audit-fee-scoring-p0yg4n`, fee constants `CRYPTO_FEE_ROUNDTRIP
=0.0008` assumed maker, logic in a new `journal/fees.py`) and this chat in PR #4
(`venue_of`/`fee_r_of`/`venue_record` in `journal.py`, crypto = MEASURED §25 taker
`0.0009`). PR #4 merged first; PR #3 was closed as superseded. ROOT CAUSE: the baton
(`docs/HANDOFF.md`) still listed net-of-fee as the open NEXT scope after PR #3 had
already built it — so a second chat picked up the same scope. This is the exact
"branch-stack tangle" §27's invariant warns about, realized.

LESSON (process): the baton is only useful if it's CURRENT. `/closeout` MUST flip the
scope the moment work lands; a chat that merges its own PR (as PR #4 did, user-
authorized) must update the baton in the SAME turn, or the next chat re-does the work.
When two PRs target one scope, prefer the one with the MEASURED input (taker 0.0009 is
a §25 fact; 0.0008 maker was an assumption) and the wider surface, close the other with
a comment, don't silently abandon it.

BUILT (net-of-fee, §26 now CLOSED): `VENUE_FEE_PCT` in config (crypto taker 0.0009 /
TradFi 0); journal `scorecard()` net columns + `venue_record()`; `/api/journal`
`by_venue`; `cli journal-score` per-venue gross→net line. 6 tests. STILL OPEN: all 14
resolved trades are crypto (TradFi book open) so the "TradFi net≈gross" contrast can't
be SHOWN yet; and the `FEE_PCT 0.0004` maker vs `0.0009` measured taker contradiction
needs one real limit fill to settle (net-crypto is conservative until then).

---

## 29. TradFi session/RTH audit: stub-day levels WERE artifacts (now fixed) + the false-fill journal bug — 2026-06-10

The §26 watch-item ("does `build_levels` survive TradFi session gaps?") is now
VERIFIED — the suspicion was CORRECT, on three fronts. All three fixed, 183 tests.

**1. Stub-day level poisoning (TradFi-only, CONFIRMED + FIXED).** Globex futures
days group on NY/UTC calendar dates, so the Sunday-evening reopen forms a ~6-bar
"day" (holidays similar). Measured on CL=F 1h: ADR depressed **17%** (4.08 vs 4.89
honest), and Monday's floor pivots + PDH/PDL derived from the Sunday stub — feeding
the LIVE confluence votes `v_pivot` and (via sweeps) `v_sweep`. FIX:
`complete_period_mask()` (context/calendar.py) — a day informs prior-day levels
(ADR `_per_date_range_avg`, floor pivots in `levels/builder.py`, PDH/PDL in
`context/mm_cycle.py`) only if its bar count ≥ 0.5×median; stub-day bars inherit
the last FULL day's levels. **Provably a no-op on 24/7 crypto** (test pins exact
equality with the naive computation), so the validated §1 behavior is untouched.
Verified on real CL=F: ADR 4.08→4.81; Monday pp == Friday (H+L+C)/3 exactly.

**2. Yahoo synthetic "tick row" (TradFi-only, FIXED).** While the market is open,
Yahoo's chart API appends a last-quote pseudo-bar (o=h=l=c=last trade, timestamped
at the last TRADE time, off the interval grid). It flowed into `build_levels` as a
real bar — the live signal was computed ON it (degenerate range → slightly
depressed ATR → tighter stops than validated). FIX: `YahooClient._parse` drops a
trailing row whose spacing from the previous bar is sub-interval (granularity from
the payload's `dataGranularity`; unknown granularity = conservative no-drop).

**3. Pending-limit FALSE-FILL bug (ALL venues, FIXED).** Seconds after a scan logs
a pending limit, no completed bar ≥ `created_at` exists, `_evaluate` returned
"open" for the empty window, and `check_open` stamped `filled_at` — a fictitious
instant fill. **24 of the journal's bracket trades carry such stamps** (filled_at
within ~seconds of created_at), including 2 in the contradictory state
`status=pending` + `filled_at` set (pending↔open oscillation). Because the fill is
RE-derived from bars on every later run, final hit/miss outcomes self-corrected —
the rot was state/timestamps, not R. FIX: empty window + pending → stays pending
(or **cancelled**, not "miss", if the fill window lapses bar-less — matters for
TradFi limits logged into a closed session); fills now stamp the fill BAR's
timestamp, not wall-clock. DATA CAVEAT: pre-fix `filled_at` values in
`data/journal.json` (≤ 2026-06-10) are unreliable as fill TIMES; statuses are
fine. Do not "clean" the journal manually — the hourly bot owns it.

**Still OPEN / known limitations (documented, NOT fixed — judged minor):**
- Wall-clock horizons: `deadline_days` / `fill_deadline_days` tick through closed
  TradFi sessions (a Friday-evening limit can cancel over a weekend unfilled).
  Shrinks the TradFi sample; doesn't corrupt outcomes.
- Weekly levels: builder's `_week_id` uses W-SUN periods, so Sunday-evening Globex
  bars count into the PRIOR week's AWR/PWH/PWL (features.py's `weekly_open` uses
  the Sun-18:00-ET anchor and is already correct). Small effect (6 bars vs ~115).
- FVG votes can form across session gaps (a weekend gap looks like a giant FVG);
  ATR spikes on the first bar after a gap (true-range vs Friday close) → wider
  stops on Sunday/Monday entries. Both are "real price gap" judgement calls.
- GitHub cron throttling: the "hourly" paper Action actually fires every ~2-4h
  (all runs succeed; GitHub schedule delay). Resolution latency only — the bar
  replay re-derives everything — but stale marks persist between runs.

## 30. §28 RECURRED — parallel chats built the same scope again; gate held this time + complementary TradFi findings — 2026-06-10

THE RECURRENCE: two parallel chats both worked the baton's "TradFi session/RTH"
scope. One shipped PR #5 (`complete_period_mask` + Yahoo tick row + false-fill
fix, 3 defects); this chat (`claude/handoff-audit-hvuuab`) independently verified
the same artifacts on live data and built an ALTERNATIVE fix (exchange trade-date
regrouping, NY+6h Globex boundary, opt-in flag). Difference from §28: the
duplicate was caught BEFORE this chat opened its PR — PR #5 was independently
audited (PASS, incl. live-data cross-validation of all four measured artifacts)
and merged through the gate; the trade-date alternative was REVERTED (preserved
in git history, commit `ae9463b`) — one mechanism on main, not two. Per §28:
wider surface won.
LESSON (new, beyond §28): check `list_pull_requests` for an open PR covering your
scope BEFORE building, not at closeout — this chat only discovered PR #5 when
`/closeout` listed open PRs. The baton can't warn about a chat that hasn't closed
out yet; the open-PR list can.

COMPLEMENTARY MEASUREMENTS (this chat's verification, beyond §29's; full report
`docs/research/tradfi_session_levels.md`):
- Monday stub pivots were off by **0.15-4.0 ATR** vs Friday-based (GC/SI/CL/EUR/GBP);
  re-scoring with the two stub-fed votes zeroed flipped **40-75% of Monday
  `_tradfi` signals** (GC=F 16/40, GBPUSD 6/8) — Mondays ≈20% of signal days. So
  pre-fix Monday `_tradfi` journal entries are the taint hotspot.
- **FX dead votes (still OPEN, not in §29):** Yahoo FX 1h volume is ALL ZERO →
  session VWAP is NaN and PVSRA can never fire → `v_vwap`/`v_vector` are silent
  0s for EURUSD/GBPUSD. FX confluence is capped at 8/10, so the 50% gate is
  effectively stricter for FX. Conservative skew; fix = per-venue n_factors or
  accept.
- **Stale-cache transient (from the PR #5 audit):** `~/.cache/kudbee_quant`
  (TTL 86400s) can serve PRE-fix frames up to a day after the fix merged. CI
  runners are fresh → live bot unaffected; local runs may briefly disagree.
- Indices (^GSPC/^NDX/^DJI) were verified CLEAN pre-fix (no stubs; asian/brinks
  NaN degrade to zero votes) — the artifact was futures+FX only.

## 31. Taint audit VERDICT: the pre-fix `_tradfi` book is CLEAN at the signal level + 11-symbol universe expansion — 2026-06-11

The §30 "pre-fix Monday entries are the taint hotspot" worry RESOLVED by replay
(`scripts/taint_audit.py`, report `docs/research/tradfi_taint_audit.md`): all 8
pre-fix `_tradfi` entries (created ≤ PR #5 merge, 2026-06-10T14:59Z) re-scored on
their signal bars under fixed vs pre-fix levels (mask monkeypatched off at both
import sites; patch verified to bite — 92/600 GC=F Monday bars shift pivots, ADR
−2.1%). **Result: 0 TAINTED — vote-for-vote identical both ways on all 8.**
Mechanism: the TradFi book only started Tuesday 06-09; all 8 entries are Tue/Wed,
whose prior-day pivots/PDH-PDL come from FULL sessions — the Monday hotspot never
coincided with a logged trade. ADR bias couldn't flip signals (ADR feeds
`adr_high/low`, which carry no confluence vote). The one profitable pre-fix trade
(SI=F +3R) is CLEAN; the forward record needs NO exclusions.

CAVEAT (recorded, not actioned): 3 of the 8 (all −1R misses) score 40% < the 50%
gate on completed bars under BOTH variants — their signals existed only in the
bot's live view (§29 tick row, since fixed, and/or legitimate mid-hour bar state,
which is still today's behavior). Replay cannot separate the two. They stay in
the record — excising reproducible losses would be survivorship cleanup.

UNIVERSE +11 (user-approved, §30 probe): `HG=F PL=F PA=F ZW=F ZC=F ZS=F ZN=F
ZB=F SB=F KC=F CC=F` added to the hourly 1h TradFi scan (CT=F excluded — broken
feed). All 11 smoke-tested end-to-end (600×1h fetch → build_levels →
confluence_score). UNPROVEN forward — softs (SB/KC/CC) are RTH-like with bigger
session gaps; expect more §29-style edge cases there. Watch, don't trust.

Protocol note: the audit gate has now held TWO PRs in a row (#5, #6 — reports in
`docs/audits/`). §30's blemish corrected in passing: the Monday-flip range's
honest lower bound is ~33% (SI=F 13/39), not 40%.

## 32. Branch-sweep verdict: no journal data lives outside `main` + the salvage lesson — 2026-06-12

User worry ("trades are out there on other branches") DISPROVED by ID-level
check: every remote branch's `data/journal.json` is a strict, stale SUBSET of
main's (0 unique trade IDs across all 11 `claude/*` branches). The bot pushes
only to main; branch copies are snapshots from their fork point. Don't re-check
journals on branches — check main.

SALVAGE LESSON (tested): the zcash branch's "finished" dashboard (commit
`6632c48`, claimed working + "183 tests pass") was wired to IMAGINED API field
names — scorecard `n_resolved`/`n_wins` (real: `n`/`hits`), counts `win`/`loss`
(real: `hit`/`miss`), `resolved_series` as numbers (real: dicts with `.r`) —
and had zero HTML escaping. It would have rendered zeros/NaN in 3 of 6 panels.
Its tests passed because it ADDED none. Rule: salvaged work from a parallel
chat gets re-verified against the live API contract before shipping; "tests
pass" means nothing if the diff has no tests. (Fixed version shipped with a
regression guard pinning the real field names: `tests/test_dashboard.py`.)

Branch hygiene facts: this remote-exec environment CANNOT delete branches
(403 — push scoped to the session branch; GitHub MCP has no ref-delete).
Deletions must be done from the GitHub UI. Verified safe to delete (merged or
content-confirmed-in-main): handoff-audit-hvuuab, hello-1lje1b,
overnight-algo-research-plan-hyqzf6, sol-short-position-0eytax,
fable-5-release-review-mow58s, handoff-audit-fee-scoring-p0yg4n,
handoff-audit-xtn2bz. Held for salvage: zcash-backtest-orderbook-shjg5o
(dashboard source — delete after the salvage PR merges),
crypto-confluences-research-cxrtp3 (research Vols 7–10),
website-design-seo-067ci3 (site pages),
market-trading-tools-analysis-l2rnr1 (29 ahead; headline content in main but
not commit-by-commit verified).

## 33. Per-factor trace/replay layer exists — and replay pct ≠ live-edge pct, now visibly — 2026-06-12

The confluence stack is now introspectable without forking it:
`confluence/trace.py` decorates `factor_votes()` with per-factor labels /
human-readable details (parity with `factor_votes`/`confluence_score` is
pinned by test — `tests/test_trace.py`), `replay.py` replays any journal
bracket bar-by-bar (read-only, 600-bar warmup matching the live scan), and
they're surfaced three ways: `GET /api/trace/{spec}`, `POST /api/sandbox/trace`
(UNVALIDATED what-if: EMA spans 2..2000 + factor subset + display gate — pure
compute, never journals), `GET /api/replay/{trade_id}`, the `trade-flow.html`
node-graph page, and the `trade-trace` CLI. `safe_spec()` was added because
`safe_symbol()` drops the `yahoo:` prefix — meaning **`/api/signal` was always
crypto-only** (left unchanged deliberately; use `/api/trace` for TradFi).

LESSON (the §29/§31 recompute gap is now per-trade visible): replaying
0bee2b4a (YAHOO:CL=F, logged at ≥50% confluence live) recomputes to **20% at
the SIGNAL bar** from refetched Yahoo data. Replay output is for studying
factor EVOLUTION around a trade, not for re-verifying the entry gate — never
read a replay pct as the live-edge pct. The caveat ships in every replay
response/CLI footer; keep it there.

## 34. Hosting architecture: the host is a disposable MIRROR; the repo journal stays the record; alerts travel via a create-only inbox — 2026-06-12

DECIDED (user, 2026-06-12): Render **Starter** ($7/mo, `render.yaml`) hosts the
FastAPI app. Free tier was rejected for a measured reason: 15-min idle
spin-down + 30-60s cold start would drop TradingView webhook POSTs (TV doesn't
retry). Verified pricing 2026-06-12, not assumed.

THE ARCHITECTURE FACT (honor this; don't "improve" it):
- The hosted app's checkout is **ephemeral and disposable** — auto-deploy on
  every push means every hourly journal commit redeploys it. That is the
  *feature* that keeps the dashboard fresh: the checkout IS the data store.
- Therefore the host must NEVER be treated as a source of journal truth, and
  must never push `data/journal.json` (bot-owned, §29-era rule stands).
- TV alerts reach the scored record via `data/alert_inbox/` (alert_inbox.py):
  the host commits one **create-only, content-hash-named** file per alert via
  a Contents-RW-this-repo-only PAT — unique paths can't race the bot — and the
  hourly Action's `ingest-alerts` step drains them into the journal
  (`source="human"`, `inbox=<id>` note marker = idempotency). `"inbox": false`
  in the `/api/alert` response means the alert is host-local only and WILL be
  lost on the next redeploy.
- The Action's commit step now stages `data/alert_inbox` too and does
  `git pull --rebase` before push (an alert landing mid-run would otherwise
  bounce the push).

Verified locally (200/200 tests; uvicorn live: fail-closed 503 / 401 / logged
pending; ingest CLI idempotent end-to-end from a temp dir; repo journal
untouched). UNPROVEN as a live deployment until the Render service exists —
the smoke-test for that is in `docs/HOSTING.md`.

## 35. Execution-sweep over the first 102 live signals: NO entry tweak rescues this week's signal; fees poison the 5m book — 2026-06-12


Research (chat artifact, read-only; refetched bars + the shared
`backtest/resolver.py`, journal semantics mirrored exactly — sanity check:
**81/81 resolved+cancelled trades reproduced their logged outcome**, zero §33
drift this time). Sample: 102 brackets, 2026-06-09 → 06-12. CAVEATS FIRST:
3.5 days, ONE regime (June-9 alt-short wave then reversal), trades heavily
correlated, all in-sample — this is hypothesis-generation, NOT validation.

- **Miss autopsy (61 misses):** 38 were simply wrong (never +0.5R). But 13 ran
  ≥+1R unbanked (7 of them ≥+2R with a 3R target), and **19 hit the stop and
  then ran to the original 3R target anyway**. The pain is exit/banking, not
  entry timing.
- **Entry-slider sweep** (retrace 0→0.60 ATR, market entry, stop 1.0→3.0 ATR,
  layered halves): EVERY variant is net-negative. Filling MORE (market,
  retrace 0/0.10 — the "layer in sooner" idea) is monotonically WORSE
  (−51R net at retrace 0 vs −34R current); only a DEEPER pullback gate
  (0.60 ATR: −7R net, +2.4R gross on 79 fills) approaches breakeven. Wider
  stops also did NOT pay despite the 19 stop-then-ran trades (3R target moves
  away faster than the stop saves). Execution tweaks shuffle the loss; they
  cannot manufacture edge the signal doesn't have this week.
- **Attribution:** 5m crypto book −18.6R net over 31 fills with **~0.24R/trade
  burned in fees alone** (tiny 5m ATR ⇒ huge fee in R) — structurally
  fee-poisoned at FEE_PCT 0.04%/side. TradFi 1h −10.0R (June-11 FX/grain
  shorts). Confluence level did NOT rank edge (60% bucket WORSE than 50%;
  70/80 n too small to read).
- **Unbuilt but proven feasible:** the "sliders → instant re-backtest over
  saved live trades" loop the user wants — this analysis IS that engine
  (recover ATR from `|signal−entry|/0.25`, rebuild brackets, shared resolver).
  Queued as the Execution Lab scope; TP1 partial-banking is the variant the
  autopsy says to test first.

## 36. REGISTERED HYPOTHESIS — fading the signal was net-positive this week, but NOT significant — 2026-06-12


User's idea (the right way around): if "layering in sooner makes it worse,"
the signal may be marking exhaustion — confluence clusters where the crowd
decides price is shifting, and in a macro uptrend those counter-moves are
continuation fuel. Tested on the same 102-signal engine as §35 (flip
direction, identical 0.25-ATR-retrace/1.5-ATR-stop/3R bracket, same fees):

- **FADE everything: +8.7R net (88 fills, +0.10R/trade)** vs −34.3R as traded.
  Robust to execution choice in-sample (market entry +7.5R, 2.5-ATR stop
  +9.3R, fade-only-5m +0.22R/trade, fade-only-60%-bucket +0.18R/trade).
- **Asymmetry lesson:** a −34R book inverts to only +9R, not +34R — the
  3R:1R bracket geometry doesn't mirror and fees hit both sides. "It's
  losing" does NOT mean "the inverse wins big."
- **Significance — the gate FAILS:** naive t=0.55; clustered by 6h scan
  window (simultaneous signals = one market bet) only **12 independent-ish
  bets**, t=0.73, cluster bootstrap **P(no edge) ≈ 23%**. One regime (the
  June-9 alt flush → V-reversal). And inversion-after-seeing-the-loss is the
  textbook in-sample trap.
- **Honest test = forward, not backward:** run a SHADOW FADE BOOK — the
  hourly scan also logs the mirrored bracket of every signal under its own
  setup tag (paper, journal-scored like everything else) and let live data
  accumulate. Sharper variant worth tagging: fade only signals OPPOSING the
  macro (HTF) trend. Needs a small bot change ⇒ its own PR + user sign-off;
  queued with the Execution Lab.

**§36 ADDENDUM — OUT-OF-SAMPLE VERDICT (same day): the blanket fade FAILS.**
Re-ran the journal test (reproduces exactly: orig −34.3R / fade +8.7R), then
took the fade rule to data it had never seen — history strictly BEFORE
2026-06-09 (15m ~31d, 1h ~4mo, 4h ~8mo), 10 journaled coins + 6 never-traded
coins (LTC/BCH/TRX/NEAR/ATOM/UNI) + 4 TradFi, same gate
(`confluence_position(min_pct=.5, trend_align=True)`) and same execution via
`bracket_backtest` (0.25-ATR limit/12-bar window/1.5-ATR stop/3R/72-bar
time-stop, fee_pct 2×FEE_PCT): **fade positive in only 16/52 symbol-TF cells
(pooled ≈ −500R); the ORIGINAL is positive in 39/52** — consistent with its
§1 validation. Last week's fade win was the June-9 V-reversal regime, not an
edge. HYPOTHESIS REJECTED as a blanket rule; shadow fade book is now
OPTIONAL/low-priority. Real watch-item found instead: **journaled crypto on
1h was orig −91.9R / fade +89.8R over the recent ~4 months** — possible edge
DECAY on the 1h crypto book recently (regime-dependence, §22-style honesty:
n large but one window; check again as forward data accrues). Full grid:
chat artifact `oos_fade_test.csv`.

## 37. 5m crypto book PAUSED — forward-confirmed fee drag — 2026-06-13

Live-trades check since the §35/§36 review (journal grew 102 → 143). The
**clean, mechanical** finding repeated forward: over the 35 resolutions on/after
2026-06-12 the **5m crypto book was gross-FLAT (+0.0R over 16 trades, 4/16 wins)
but net −3.2R** — losing only to fees, not direction (~0.20R/trade fee bite at
the measured 0.045%/side taker; tiny 5m ATR ⇒ huge fee in R, exactly the §35
attribution). The book is structurally fee-poisoned: it cannot win net at taker
cost because the per-trade fee in R is on the order of its edge.

DECISION (user-approved 2026-06-13): **dropped `5m` from the crypto
`--intervals` in `.github/workflows/paper-trade.yml`** (now `15m 1h 2h 4h`).
TradFi was already 1h-only. Open 5m trades are left to resolve naturally on the
next hourly runs; only NEW 5m signals stop. This is an EXECUTION/cost change, not
a strategy-default change (§1 untouched). Re-enable only if a structurally
cheaper fill (real maker/limit, or a 0-fee venue) changes the math — one real
LIMIT fill would also settle the standing maker-vs-taker fee question (§25).

Other deltas from the same check (context, NOT validation — ~5-day, one-regime,
correlated sample): since-06-12 was −15.0R gross / ≈−21.2R net, 5/35 wins (14%),
all bot. 1h since 06-12 was −6R but mostly TradFi grains (ZW/ZC/ZS/ZB); 1h-crypto
was only −2R (2 trades) — too small to confirm or refute the §36 1h-decay
watch-item either way, so it stays a watch-item. Whole-book record now: crypto
n=89 hit 20% exp −0.212R→net −0.411R; tradfi n=18 hit 6% −0.778R. Open book had 0
trades past deadline (resolver keeping up); 5 aging 06-09 alt-shorts still inside
their 6–12d windows. Journal left untouched/uncommitted during the check.

## 38. Live order-placement subsystem BUILT — maker-only, double-gated (untested live) — 2026-06-14

The real order path behind `require_live_enabled()` now exists (PR #14 shipped
only the stub that raised). It is **logic-complete and hermetically tested, but
has NEVER placed a real order in production** — treat as unproven live.

- **`execution/exchange.py`** — `ExchangeClient` Protocol + native HMAC-SHA256
  signed `BinanceBrokerClient` (plain `requests`, matching `ingest/binance.py`;
  ccxt deliberately NOT taken — it can slot behind the Protocol later). Keys read
  from env only (`BINANCE_API_KEY/SECRET`, `BINANCE_TESTNET`), never logged;
  construction is lazy so a missing key only fails at call time. Symbols pass the
  same SSRF-safe `parse_spec` whitelist before any URL use.
- **MAKER-ONLY by construction.** The order primitive is Binance `LIMIT_MAKER`;
  there is intentionally **no** market-order method. This is the §25/§1 discipline
  enforced in code: the venue rejects rather than fills as a taker if the limit
  would cross, so the bot can never accidentally pay taker. (This is also the path
  that, on a first real fill, finally settles the standing maker-rate open item
  from §25 — `FEE_PCT 0.0004` maker assumption vs `0.0009` measured taker.)
- **`execution/killswitch.py`** — `MAX_DAILY_LOSS_USD` checked before every live
  submit; sums only TODAY's (UTC) realized **live** losses via an honest R→USD
  bridge (`net_outcome_r × position_size_usd × |entry−stop|/entry`). Paper/legacy
  trades (no `position_size_usd`) value at $0 and don't move it.
- **`execution/live.py`** — `submit()` = gate → kill-switch → concurrency cap →
  size (`min(req, MAX_POSITION_SIZE_USD)`) → rest maker limit → journal as
  `mode="live"`, `status="pending"`, with `exchange_order_id`. `poll()` stamps
  `filled_at` from the **venue clock, not bar time** (avoids the §29 fictitious
  fill); `cancel()`/`reconcile()` round it out. Stop/target *resolution* still
  flows through the shared OHLCV resolver, so live and backtest never disagree.
- Paper remains the default; `build_executor()` returns live only when both flags
  are set AND (at submit) real keys exist. 24 new no-network tests (fake exchange);
  suite 259 passed / 5 skipped; ruff clean. §1 / `FEE_PCT` untouched; no
  journal/alert_inbox edits; no secrets. NOT wired into the hourly Action (that
  stays the documented opt-in). Doc: `docs/LIVE_TRADING_SETUP.md` (rewritten;
  testnet smoke-test runbook included).

## 39. New-signals audit — 3 signals built opt-in & validated; meta-gate lift is near the noise floor — 2026-06-14

Extended the entry system with genuinely-missing signals (NOT re-adding the 5
removed votes), each opt-in/OFF and validated on real 1h data (top-10 majors,
8000 bars, canonical bracket). Branch `claude/confluence-new-signals-audit`.
Honest, mixed-to-negative outcome — kept as infrastructure, NOT enabled live.

- **Signal #1 taker delta / CVD / delta-divergence** (`levels/delta.py`, derived
  from `taker_buy_base` which `ingest/binance.py` parsed then DROPPED — now kept).
  As a `confluence_position(delta_align=)` FILTER it **fails OOS** (+0.019R→−0.009R,
  helps in-sample only — same failure mode as the 5 removed votes). As meta-model
  FEATURES it **passes** the GBT expectancy-gate (flips to significant p=0.0073,
  +0.094R best-threshold). Linear model sees nothing → nonlinear/tail-only.
- **Signal #2 per-session volume profile** POC/VAH/VAL/naked POC
  (`levels/volume_profile.py`, opt-in in `LEVEL_COLUMNS` via `OPTIONAL_LEVEL_COLUMNS`).
  Proximity FILTER is **inconclusive** (lifts OOS +0.057R but DEGRADES in-sample and
  halves trades — regime-dependent). FEATURES pass the gate but **near-boundary**.
- **Signal #3 killzone gate** (`confluence_position(killzone_gate=)`): **FAILS OOS**
  (+0.019R→−0.067R). The hour map is the real find: **in-killzone hours +0.021R vs
  OFF-hours +0.102R (~5×)** — 16h UTC is one of the best hours and is OFF-killzone;
  06h is a weak killzone hour. The FX London/NY/Brinks folklore does NOT hold on a
  24/7 crypto book. (Engine walk_forward disagreed — killzone helped the always-in
  Sharpe — but the bracket is what we trade; resolved to the bracket = discard.)
- **KEY meta-lesson:** the GBT expectancy-gate baseline sits at p≈0.064 (right at the
  boundary), and BOTH Signal #1's delta features AND Signal #2's vp features tip it to
  ~p=0.005 with a near-identical best gated expectancy (~0.329R). Two unrelated feature
  sets landing in the same place = the marginal lift is **small and near the noise
  floor**, not a banked edge. Don't enable in live gating on one window — forward-test.
- **60% confluence band:** the stale −31R figure does NOT reproduce — OOS the ~0.60
  band is **+0.25R (net-positive)**, one of the better bands; `delta_align`/killzone
  do not rescue it (they hurt it). This independently **corroborates PR #17's
  near-miss autopsy** (don't drop the 60% band — it's net-positive OOS).
- Files: 3 opt-in modules behind `config/features.py` flags (default OFF) + 3
  `confluence_position` filter params (default OFF); validation scripts under
  `scripts/validate_*`; per-signal reports under `docs/research/signal-{1,2,3}-*.md`.
  No live-config change. Defaults §1 / `FEE_PCT` untouched.

## 40. Admin/investor dashboard overhaul — login gate + Tailwind + curated runner — 2026-06-15

Front-end re-haul (this chat's PR, branch `homepage-admin-dashboard-redesign`).
User-confirmed scope: shared-password login now (no email/DB yet), a curated
(non-RCE) test runner, and Tailwind via a compiled build step.

- **Auth (`kudbee_quant/api_auth.py`):** ONE shared password
  (`KUDBEE_DASHBOARD_PASSWORD`) → a stateless, HMAC-signed session cookie
  (`kudbee_session`, HttpOnly/Secure/SameSite=Lax, 12h; key `KUDBEE_SESSION_SECRET`).
  Hand-rolled (native `hmac`, no new dep), **fail-closed** like `check_token`
  (unset ⇒ 503/locked; wrong ⇒ 401; constant-time). `/` and `/dashboard` redirect
  to `/login` without a session; gated APIs return 401. Payload dict shape leaves
  room for `sub`/`role` when real accounts land. Login limiter 5/min.
- **Curated runner (`kudbee_quant/api_runner.py`):** fixed-dict whitelist of
  ENGINE actions (signal/backtest/validate/sweep/bracket-sweep/paper-scan), every
  param Pydantic-bounded + symbol-whitelisted; async in-memory jobs on a 2-worker
  pool (429 when busy), `POST /api/run/{action}` → poll `GET /api/run/{id}`.
  **NOT a code executor.** **NEVER writes the journal:** paper-scan uses the NEW
  `paper_scan(dry_run=True)` seam (the only change to `paper/paper.py`) — guarded
  by `test_paper_scan_dry_run_never_writes_journal`. Results are EPHEMERAL
  (in-memory; gone on redeploy) — surfaced honestly in the UI.
- **New gated read endpoints:** `/api/open-trades`, `/api/trade-history`,
  `/api/research` (wrap `review.py` + research JSON/`family_ledger`). Public
  marketing reads unchanged.
- **Tailwind (compiled + committed):** `package.json`/`tailwind.config.js`/
  `assets/css/tailwind.css` → `npm run build` writes `assets/css/app.css` and
  copies to `kudbee_quant/static/app.css`. Both compiled files committed so
  Netlify (`command=""`) and the Render `pip install` build need no Node.
  `node_modules/` gitignored.
- **CSP — now THREE sources of truth:** `netlify.toml` + `_headers` (static host)
  and a NEW strict FastAPI response header in `api.py` (`script-src 'self'`, no
  inline) for the Render-served dashboard/login (which had NO CSP before). That's
  why dashboard/login JS is external (`static/app.js`, `static/login.js`).
  `netlify.toml` CSP left as-is (still `style-src 'unsafe-inline'`) — NOT tightened,
  because the marketing pages still use inline styles; do that audit before dropping it.
- **SEO:** dashboard/login carry `noindex` meta + `X-Robots-Tag`, and robots.txt
  disallows them. `llms.txt`/sitemap already current (no new public pages added).
- **Status:** 301 passed (was 259+5 skipped; +17 new auth/runner tests, skips now
  run with deps installed); new files ruff-clean (pre-existing api.py B904/E402 left
  as the file's style). Smoke-tested locally end-to-end (login→cookie→dashboard,
  static assets, gating, headers). §1 / `FEE_PCT` / journal / alert_inbox untouched;
  no secrets committed.
- **UNVERIFIED in production:** never deployed to the real Render host (no service
  exists yet — see HOSTING.md). Email-verified self-serve accounts + captcha + API
  keys are a deliberate later phase (need an email provider + persistent store).

## 41. Cycle-aware OOS backtest — the live 1h config survives the regime; min_pct 0.6 refuted OOS — 2026-06-15

Ran the EXACT live rules (`confluence_position(min_pct=0.5, trend_align=True)` +
`bracket_backtest(stop_atr=1.5, target_r=3.0, limit_retrace_atr=0.25, max_bars=24)`,
the canonical `BRACKET_KW`) over two prior-cycle CHOP analogs (2018-07/10 and
2022-05/08 — the equivalent ~786-day-post-halving phase we are in now) plus a broad
recent span (2024-06→now), at 5m/15m/1h. **137,326 resolved OOS trades** (params
frozen at validated defaults, never refit; all three regimes unseen). Fees modeled
gross→full-taker (0.09% round-trip, §25). Code: `scripts/cycle_backtest.py` +
`scripts/cycle_backtest_matrix.py`; report `docs/research/cycle_backtest.md`; new
`BinanceClient.klines_range()` (forward-paging date-window fetch, disk-cached).

FINDINGS (net-of-fees, the honest lens):
- **Timeframe is decisive (this is the headline).** 1h: **+0.096R net-maker /
  +0.060R net-FULL-taker**, n=8,124, bootstrap p<0.001 — positive and taker-survived.
  15m: +0.037R maker but NEGATIVE at taker in every regime (maker-only / cost-fragile).
  5m: −0.046R maker, −0.19R taker — DEAD in every regime (vindicates the §37 pause).
- **Do NOT quote the pooled "overall" (−0.019R, p=1.000) without context** — it is
  71% 5m trades, i.e. a book the live bot doesn't trade. Restricted to the validated
  1h TF the edge is clean and >1,000 OOS trades (8,124).
- **Survives the CURRENT regime:** recent 1h is the STRONGEST (+0.102/+0.064, n=6723,
  p<0.001). **Survives the CHOP analogs but thinner & low-confidence:** 2018 1h
  +0.121/+0.085 (n=450), 2022 1h +0.043/+0.019 (n=951, weakest, not individually
  significant). Regime-DAMPENED, not regime-broken — consistent with §1 "thinner in
  chop". CAVEAT: the chop samples are small; treat "survives chop" as positive-but-
  low-confidence, not proven.
- **min_pct 0.5→0.6 is REFUTED OOS — in every regime.** On 1h the 50% band is the
  BEST band (+0.103R) and per-R expectancy FALLS as the floor rises (ALL: 0.5 +0.096
  → 0.6 +0.040 → 0.7 +0.005); at 0.6 the **2022 chop analog flips NEGATIVE**
  (+0.043→−0.020). This closes the long-pending `--min-pct 0.6` question (PR #17/#20
  baton): the OOS answer is **NO — keep 0.5.** Corroborates the autopsy OVERFIT verdict.
- High-confluence 1h bands (70/80+) go NEGATIVE in both chop analogs — "more
  confluence = safer" is itself regime-fragile.

ACTION: **affirm the live config exactly (1h, 0.5, trend-on, 3R, 1.5-ATR, 0.25
maker) — no change.** Keep 5m paused, do not add 15m at size, keep min_pct at 0.5,
size conservatively in the current chop regime (1h net-taker cushion is thin,
~+0.02–0.06R). Method note: prior OOS scripts (`near_miss_oos.py`) ran the engine
with DEFAULT bracket args (market entry, 1.0 stop, flat fee) — NOT the live
execution; this run uses the exact live bracket so costs/fills match production.


## 42. Execution head-to-head — maker-retrace WINS net-of-fees on every TF; market entry never wins; cancels ARE the runners but aren't harvestable by blanket market — 2026-06-15

OFFLINE research (TASK 2026-06-15). Tested whether entering at the signal with a
MARKET order beats the live 0.25-ATR maker retrace, on the SAME OOS sample. Live
path untouched. Harness: `kudbee_quant/backtest/execution_modes.py` (+6 tests),
`scripts/execution_backtest.py`; full results `data/execution_backtest_results.json`;
writeup `docs/EXECUTION_BACKTEST.md`. Signal = the real production
`confluence_position(min_pct=0.50, trend_align=True)`; geometry = validated §1
(1.5-ATR stop, 3R, retrace 0.25, entry_window 6). **Per-leg honest fees** (§25):
taker 0.00045/side IN and on every stop/time-stop (market out), maker 0.0002/side
on resting limit fills and targets. OOS = 2018_chop (5 majors), 2022_chop (10),
recent (10); 5m fetched + resampled to 15m/1h so all TFs share the same bars.

VERDICT (decisive metric = net-of-fees expectancy/trade, pooled): **the CURRENT
maker retrace (A) wins on all three timeframes and in all 9 regime cells.**
- 1h: A **+0.1265R** (p=0.000) > C hybrid +0.065 > B market +0.055. A survives both
  chop windows (2018 +0.249, 2022 +0.087, recent +0.109). This is the winning
  execution; honestly-costed number **+0.1265R/trade** (legacy round-trip-maker
  costing: +0.1397R). Lower than the §1 ~+0.19-0.24R headline because 2/3 windows
  are chop/bear AND stops now pay taker (more conservative than the old model).
- 15m: A ≈ breakeven +0.0014R (p=0.45, NOT significant) but still beats B (−0.096).
- 5m: ALL lose; **market makes 5m WORSE** (B −0.204 vs A −0.100). §37 reinforced —
  no execution change rescues the fee-poisoned 5m book (hypothesis tested, not
  assumed). Maker beats market by ~+0.07–0.10R/trade on every TF; hybrid always
  sits between (pays taker on the chase).

ADVERSE SELECTION (STEP 3, the key one): the ~14-15% of signals the retrace CANCELS,
re-resolved as market entries, are **strong net winners every regime** (1h +1.22R
69.9% win, 15m +1.11R, 5m +1.10R; all p=0.000, large n). So the retrace IS
anti-selecting — a long is "cancelled" precisely when price never pulled back, i.e.
it ran immediately; the book fills pullbacks/reversals and skips the runners.
**BUT this is NOT a reason to switch to market entry**, for two honest reasons:
(1) you can't isolate the cancels in real time — the only tradeable version is
"take every signal at market" = variant B, which LOSES on every TF (the reversals
cost more than the runners gain); (2) the +1.1R is UPWARD-BIASED by selection
conditioning (cancellation = no 0.25-ATR pullback in 6 bars correlates with not
being stopped, since the stop is 1.5 ATR away). Treat +1.1R as a *diagnostic that
cancels lean to runners*, not as harvestable edge.

DEAD END logged (so we don't re-test): blanket market / next-bar-open entry, and
limit-then-market hybrid, both LOSE vs the maker retrace on 5m/15m/1h. NO live
change. The only open follow-up (future research, forward-test first): a SELECTIVE
chase that market-fills a cancelled signal ONLY under a momentum/trend gate — the
seam exists (`run_variant` + `adverse_selection`). §1 / FEE_PCT / journal / live
path all untouched.

## 43. Hourly scan flipped to TOP-100 + 5m RE-ENABLED — user-directed forward experiment (against §37/§31) — 2026-06-14 (merged 2026-06-15)

> Originally drafted as "§39" in PR #18; renumbered to §43 on merge (§39 was taken by
> the new-signals audit). Merged 2026-06-15 via the `/handoff-audit` chat at the user's
> explicit direction ("merge it as a paper experiment").

The user directed the hourly paper Action to scan the **full top-100 universe**
(`config/crypto_universe.yaml`, ~101 pairs via `universe_loader.universe_specs()`)
and to **re-enable the 5m timeframe** — `--intervals 5m 15m 1h 2h 4h`. This is the
config the user originally expected ("5m across the top 100"); the bot had been
running top-10 on 15m/1h/2h/4h with 5m paused.

HONESTY — this runs AGAINST our own evidence, and the user confirmed (twice when the
PR was drafted, and again on the merge decision):
- **5m is fee-poisoned (§37):** forward-confirmed gross-flat / net-negative purely
  on fees (tiny 5m ATR ⇒ huge fee in R). The near-miss autopsy (PR #17) re-confirmed
  no R:R tweak rescues the low/sub-hourly book at taker cost. The cycle backtest (§41)
  and execution head-to-head (§42) both re-confirm 5m is net-dead.
- **Top-100 long tail is UNPROVEN forward (§31):** only the top-10 majors are
  walk-forward validated; the tail is a static snapshot, thinner/wider-spread.

WHY it's still defensible: this is **PAPER**, so it is a forward EXPERIMENT that
GENERATES the data to confirm/refute the fee concern on the wider book — consistent
with the project thesis (honest forward validation, let the data speak). It is NOT a
validated config and must not be cited as edge.

OPERATIONAL WATCH-ITEMS (the real risks): ~100 symbols × 5 timeframes per hourly run
is ~50× the prior API/build_levels load — watch for Action runtime/timeout and
Binance rate-limits (mirror `data-api.binance.vision`); the bot-owned
`data/journal.json` will grow much faster. If the Action times out or the 5m book
re-confirms §37, REVERT to the top-10 / no-5m config. Change shipped in
`.github/workflows/paper-trade.yml` (the §37 pause comment replaced with the §43
forward-experiment note). §1 defaults / `FEE_PCT` untouched.

---

## 44. VWAP factor flipped to ROTATION (mean-reversion) — user-directed, NOT OOS-validated, now LIVE — 2026-06-16 (PR #31, merged)

The user directed the **VWAP confluence vote to flip from momentum to rotation
(mean-reversion):** `v_vwap = −sign(close − vwap)` — price stretched ABOVE the
session VWAP now votes SHORT (fade back into it), BELOW votes LONG. VWAP was already
a live vote (built by default in `levels/builder.py`), so this is a **polarity flip,
not a new factor** — two opposite VWAP votes would just cancel in the sum-of-votes
engine, so polarity is the only coherent way to express "rotation." Code:
`kudbee_quant/confluence/stack.py` (`v_vwap`), with an in-code NOTE flagging it for
OOS re-validation.

HONESTY — this **changes a previously-validated live default and is NOT validated as
better than the momentum sign.** The one-off A/B screen (`scripts/compare_vwap_rotation.py`,
1h, 10 majors, §1 gate, per-bar model, zero-fee) recovered both nets from one vote
pass and found the blanket flip **HURTS on majors**: momentum 47.26% win / +197%
gross / 13,175 trades vs rotation 47.76% win / −51% gross / 2,165 trades. PR #31 was
opened DRAFT for exactly this reason, then **merged by the user** — so the rotation
sign is now LIVE in the hourly paper bot. **Open risk for the next chat:** this is an
unvalidated change to a §1-validated default. The narrower conditional the user
actually described — *daily-open read AND price below VWAP → 2× long size* — was NOT
tested on the bracket model and is the more faithful version of the idea than the
blanket per-bar flip. Revisit: either OOS-validate the flip on the bracket harness or
test the conditional-size rule; don't treat rotation as settled.

Also shipped this session (PR #31): `docs/OPEN_SETUPS.md` — a **manual** discretionary
trade-tracking board (GOOGL / HYPE / COMP / DEGEN / ETH longs, $100 = 1R, TP1 1.5R /
TP2 2.8926R). It is NOT read by the bot and is separate from `data/journal.json`.

### Assessment of the shared "Crawlee + latency + cluster" PDF (Perplexity thread)
The user shared a long external thread proposing (a) a Crawlee news-sentiment worker
pool feeding source-aware scores, (b) a fast-path/batch-path latency overhaul to cure
a "1–1.5 hour signal→entry delay," and (c) a data-feed benchmark harness. **Most of
it does NOT apply to THIS bot:** we are pure price-action on **bar-close** signals via
an hourly GitHub Action — there is no scraper on the hot path, no news layer, and no
1.5h execution delay to fix. Do not build the Crawlee/latency/feed-benchmark stack
here on the strength of that thread. **The ONE applicable idea** is its "losing
trades arrive in clusters → are they regime-driven or just variance?" question — which
maps cleanly onto our existing significance-gated study harness
(`confluence_directional_study`, Wilson CIs + FDR) over the live `data/journal.json`.
That is the next unit (the "Cluster Analyzer"), and it directly answers Tino's
"increase sample size, study the losers" point.

## 45. Losing-cluster analyzer — built (read-only, significance-gated) — 2026-06-19 (PR #35)

Built the §44 "next unit." `kudbee_quant/cluster.py` + CLI `kud losing-clusters`
(+ `tests/test_cluster.py`, 88 lines). Read-only over `data/journal.json`, **no
network, no journal writes.** For each context dimension (time-of-day, day-of-week,
confluence-gate strength, ATR/vol regime *proxy* = stop-distance-%, timeframe,
direction) it asks whether a bucket's **net-of-fee** win rate is significantly
*below the book's own baseline* — reusing the confluence study's harness
(`conditional_table`: Wilson CIs + Benjamini-Hochberg FDR). Key honesty choices,
do not regress them: **null = the book's unconditional win rate, NOT 0.5** (this
book wins ~1-in-5 by asymmetric design; testing vs a coin flip flags everything);
a bucket is a "losing cluster" only if `sufficient` AND `significant_fdr` AND below
baseline; **if nothing survives FDR the honest read is "variance, not regime."**
ATR regime is a labelled proxy (offline by design). Re-run for the current verdict;
the framework — not a frozen result — is the durable asset.

## 46. Micro-stake / high-leverage / break-even viability — DISPROVEN at high lev; marginal-only at maker/≤10x; forward-test framework + hosted report — 2026-06-19 (PR #35)

Tested the "tiny stake + high leverage + move stop to break-even once it proves
direction" idea over **497 of 498 resolved bracket paths** (`scripts/leverage_be_study.py`,
read-only, re-fetches each post-fill bar path). Durable findings (all reproducible):
- **"Goes green" is real (95% touch profit) but mostly inside the friction band.**
  Favourable move is near-immediate (median time-to-first-green ≈ 0h), so the BE
  trigger must be EARLY — `lock+0.1R@first_green` tops every friction column; later
  triggers (+0.5R/+1R) are WORSE than original (give the move back).
- **Fees decide it.** Best variant: gross **+0.077R** → maker/zero-fee **+0.038R**
  → realistic taker **−0.219R** → harsh **−0.518R**. `cost_R = roundtrip%/stop%`, so
  tight stops (median 0.74%) amplify fees. The edge exists ONLY at ~0 fee.
- **High leverage backfires — it's a liability, not a multiplier.** Liquidation band
  ≈ 1/L−MMR; ordinary adverse wiggle (median MAE 1.62%, p90 3.87%) breaches it.
  **50x liquidates ~55% of trades (RoR 100% by 500); 25x ~12% (RoR 92%); only 10x
  survives (~1% liq, RoR 0%)** — and 10x is "best" only because it doesn't liquidate,
  EV still ~breakeven-negative. **50x is a ruin machine — settled.**
- Short-side less-bad than long (consistent with §44); tradfi/zero-fee venue least-bad.

**Recommended candidate (paper only, NOT validated):** `lock+0.1R@first_green`, **≤10x**,
**zero-fee/maker venue**, prefer short-side + stop>0.5%. Never taker-side, never >10x.

**Paper-forward-test framework** (`docs/research/leverage_be_forward_test.md`): two
gated tiers. **Tier 1 = shadow overlay** (`scripts/leverage_be_shadow.py`, BUILT,
read-only, writes only to gitignored `data/shadow/`, never the journal) replays the
rule OOS with PRE-REGISTERED thresholds (n≥150 gate; 90% bootstrap CIs; kill if
rolling-100 net<−0.10R or liq>2% at ≤10x — the >2% reconciles with the study's ~1%
baseline, NOT "any liq=0"). Current Tier-1 read: **zero-fee primary lane n=25 →
INCONCLUSIVE** (below gate, mildly negative); **crypto maker-ASSUMED lane n=314 →
PASS** (+0.106R net, 90% CI excludes 0; +0.427R vs original) **but it assumes maker
fills we have NOT proven.** So the make-or-break is **maker-fill feasibility (§42)** —
that is **Tier 2** (an isolated, default-OFF paper book that actually places the maker
limits and measures fill rate; kill if <60%). A Tier-1 pass is necessary-not-sufficient.

**Deliverable:** `leverage-report.html` — an investor-grade, CSS-only (CSP-safe)
research brief on the existing Cloudflare Pages site; canonical/OG set to
**report.kudbeequant.com**, indexable, featured from `lab.html`, in `sitemap.xml`.
No live-edge claims. Going live on the custom domain needs (user-side) a `main` merge
+ a Cloudflare custom-domain attach.

## 47. Tier-2 maker ENTRY fill feasibility — PASS (~87%) from existing journal data, read-only — 2026-06-19 (PR after #35)

The §42 "can we get maker fills?" make-or-break is **partly answerable now without any
new infra**: the live paper engine already enters with a 0.25-ATR maker-retrace LIMIT and
the journal records FILLED vs CANCELLED. `scripts/leverage_be_tier2_fills.py` (read-only,
no orders/writes) measures it: **overall maker ENTRY fill rate 86.6% (557 filled / 643
decided; 86 cancelled), median time-to-fill 0.22h** — well clear of the pre-registered
<60% kill. By venue: **crypto 87.6%** (major 88.3 / alt 87.2), **tradfi/zero-fee 76.4%
(n=55)** — the zero-fee venue (the leverage rule's primary target) is the *weakest* but
still passes. **Verdict: §42's ENTRY leg is de-risked.**
HONEST LIMITS (do not over-quote): this is the **entry** maker fill only. The break-even
**EXIT** (stop-to-BE trigger) is typically a **taker on crypto** — only the zero-fee TradFi
venue is fee-free both sides — so the crypto net still carries an exit-side fee the study's
"low/maker" model under-charges. And paper fills ≠ guaranteed real-exchange fills at micro
size. Evidence, not proof. **Remaining Tier-2 work:** (a) model the BE-exit taker fee
explicitly (re-rate the candidate net with maker-entry + taker-exit, not both-maker);
(b) a live `BINANCE_TESTNET` micro-stake confirmation. The report (`leverage-report.html`)
now carries this as "Finding 4."

## 48. Live paper book is NET-NEGATIVE — diagnosed (§45 tool) + reverted to validated config — 2026-06-19 (PR #39)

**The honest live state:** the hourly paper book is **−0.295R/trade, 18% win, −149R over
506 resolved** (needs ~26% win for a 3R system; it's at 18%). This was masked by all the
research side-work; surfaced via `review-trade-history` + the §45 cluster analyzer.

**Diagnosis (live, net of fees) — the validated CORE is ~fine; the EXPERIMENTS bled:**
- **Top-10 majors / 1h ≈ breakeven** (−0.03R gross). The §1 core is not broken.
- **Top-100 alt expansion (§31) = the biggest 1h drag: −0.496R** (XRP −16R, DOT −13R, SNX…).
- **Every crypto TF is net-negative:** 5m −0.63R (§37), 15m −0.36, 1h −0.29 (least bad),
  2h −0.38, 4h −0.55. → 1h is the only defensible TF.
- **Longs collapsed: 7% win, −0.80R** on 1h (regime; a *significant* FDR cluster).
- **§45 cluster analyzer (FDR-gated) flagged real losing clusters:** hour **18h = 2% win,
  p<0.001 (n=80)**, 06h = 0% (n=27), Mon/Wed, direction=long. Losses CONCENTRATE in
  specific windows — regime/timing structure, not pure variance. (This validated the §45
  tool: it earned its keep.)

**Action (PR #39):** reverted `.github/workflows/paper-trade.yml` crypto scan to the §1
forward set — **`TOP_10_CRYPTO`, `--intervals 1h`** (was top-100 via `universe_specs` on
5m/15m/1h/2h/4h). TradFi book unchanged. **VWAP rotation flip (§44) deliberately KEPT** —
live data does NOT condemn it (majors *post*-flip were small-n POSITIVE: n=7 +1.22R), so
the §44 open-risk lean ("revert the flip") is now SOFTENED to "keep observing" by live data.
No change to §1 geometry / `FEE_PCT` / `bracket.py` / `resolver.py`.

**Next edge-builder (not done):** a **killzone/hour gate** (PR #20's gate, currently OFF) to
cut the 18h/06h toxic clusters — forward-validate before enabling. Watch the reverted book:
does top-10/1h turn positive once the alt+5m drag is gone? Even majors/1h is only ~breakeven
live vs ~+0.2R backtested, so a real backtest→live gap (regime/decay) may still remain.

## 49. Pay-yourself (breakeven) exit ARMED on the hourly bot — config-premise was wrong; needed CLI wiring — 2026-06-21 (PR #47)

**The bug (confirmed):** the hourly Action had **never** armed the breakeven exit — `0 of 701`
journal trades had `tp1` set. The cron ran `paper-scan` with no TP1 flag, so every prediction
got `tp1=None` and the "stop→breakeven at +1R" logic in `resolver.py` could never fire; deep-
in-profit trades took full −1R stops.
**The premise that it was config-only was FALSE:** `paper-scan` exposed only `--tp1-r`, NOT
`--tp1-frac`/`--no-be` (those were on the *backtest* parser), and `_paper_scan` never threaded
`tp1_frac`/`be_after_tp1`. Adding `--tp1-frac 0.0` to the cron as-specified would have errored
(`unrecognized arguments`), been swallowed by the trailing `|| true`, and **silently stopped
both books from logging any trades.** Caught it audit-first before shipping.
**Fix (minimal wiring, mirrors the tested backtest parser):** `cli.py` — add `--tp1-frac`
(default 0.5 = prior `paper_scan` default, backward-compatible) + `--no-be` to the paper-scan
parser, thread both into `_paper_scan`. `paper.py` — `paper_scan` accepts `be_after_tp1`, passes
to `Prediction`. `paper-trade.yml` — both 1h scans now pass `--tp1-r 1.0 --tp1-frac 0.0`
(**breakeven-only**: bank nothing at +1R, stop→breakeven, ride full size to +3R). Three
adversarial resolver tests added (runner→+3R, **breakeven-save→0R not −1R**, clean-stop→−1R).
`378 passed`. **LIVE now** — new 1h predictions stamp `tp1=entry+1R`; forward-only (the 701
historical trades stay `tp1=None`). Note: `paper-scan --help` still crashes on a PRE-EXISTING
bare-`%` argparse bug (`1%)` in help strings) — cosmetic, cron-irrelevant, left untouched.

## 50. Flattened 40 stale-timeframe (2h/4h) zombie positions in the journal — honest retirement — 2026-06-21 (PR #48)

The 2026-06-19 §1 revert (§48 / PR #39 → 1h-only) left **40 filled positions open on retired
TFs (26× 4h, 14× 2h)**, predating the §49 breakeven fix (`tp1=None`), re-managed into stop/
target every hour. **KEY AUDIT FINDING:** `journal-score`'s `scorecard()` buckets by **`setup`
only**, and the setup label is **timeframe-agnostic** (`confluence_r_50pct_tf` is the same on 1h
and 4h) — so once these resolved they'd have **dragged the 1h-only record**. Corollary used:
`scorecard`/`venue_record`/`source_record`/`resolved_series` all filter to `status in (hit,miss)`
and `check_open` only touches `open`/`pending`, so a non-scoring status both hides them from every
record surface AND stops them being re-managed. **Mechanism (B):** `scripts/flatten_stale_tf.py`
(idempotent) sets the 40 → `status="flattened"` (truthful — they filled; *not* `cancelled`,
*not* hit/miss), `reason_closed` carries the read-only at-mark R snapshot, `outcome_r` stays
`None` (no mark figure can leak into a bucket). Raw-JSON targeted edit (NOT via `TradeJournal.save`)
so every non-target record stays byte-for-byte identical; only 3 fields × 40 change; count stays
703; idempotent (2nd run = 0 changes). The 6→5 open 1h positions and all resolved records
untouched. Most of the 40 were *in profit* at flatten (would have given it back with no BE).

## 51. Exit-geometry sweep (5m) — NO geometry rescues 5m; quarter-Kelly says DO NOT BET — 2026-06-22 (PR #49)

Extended `scripts/leverage_be_study.py` with `--exit-geometry` (read-only, offline): on **5m
only**, sweep **stop width** (0.5/1.0/1.5/2.0× today's stop) × **BE trigger**, target held at 3R
of the scaled stop, re-walking each path **adverse-first** via the existing tested `sim_policy`
(R arrays rescaled so 1 NEW-R = w×original stop → widths compare directly; friction maps as
`friction_r/w`). **Honest result: ALL 24 combos net-negative.** Least-bad = **2.0× stop /
BE@first_green / 3R = −0.243R/trade (real), −0.476 (harsh), 3% win, n=182**; tightening (0.5×) is
worst (−0.96…−1.18R). Sizing the −0.243R edge over 100 trades / $1,000: 2% risk → $610 (−40% DD),
3% → $475 (−53%), **5% → $283 (−72% DD)**; **quarter-Kelly ≤ 0 → DO NOT BET.** Corroborates §37/§48
— 5m has no exit-geometry rescue. Outputs `data/exit_geometry_5m.json` + `reports/exit_geometry_5m.md`
(committed). Also added `1` (no-lev) to `LEVERAGES`. Journal/engine/workflow untouched; `378 passed`.

## 52. Experiment §A — 5m long-only book + long_only/killzone_gate flags (FORWARD-TEST, not validated) — 2026-06-22 (PR #50)

User-directed forward experiment, separately tagged so it never touches the validated 1h book.
`paper.py`/`cli.py` gain `long_only` (skip shorts) + `killzone_gate` (keep only London/NY/Brinks
windows, reuses `KILLZONE_GATE_FLAGS`, no-op without the columns); setup tags gain `_lo`/`_kz`.
`paper-trade.yml` adds an **Experiment §A** step: **5m, `--long-only`, pay-yourself
(`--tp1-r 1.0 --tp1-frac 0.0`), `--trend-filter`**, run after the 1h scan so the net-exposure
guard sees open positions. **HONESTY (the reason I paused mid-task):** the commit's original
"longs 32% vs shorts 14%" is a **subset** figure — VERIFIED against `excursion_audit.json`
(n=48, Jun 9-13: longs 11/34=32%, shorts 2/14=14%) — but the **full-journal 5m sample (n=182)
reads ~16%/17%**, so long-only is a **HYPOTHESIS being forward-tested, NOT a validated edge.**
**Killzone gate ships UNARMED:** the same audit shows it HURTS 5m (20% win *inside* sessions vs
28% *outside*); the flag is there for future **1h** validation only. The "18h-UTC toxic" claim is
from **1h** cluster analysis (§48), not 5m. `380 passed` (+2 flag tests). **WATCH:** after ≥30
forward `_lo` trades, `journal-score` filtered to `timeframe=5m` — net-negative → **revert the §A
step** (same trigger as §37). Both flags default-off → no change to the validated path.

## 53. Experiment §C — clean_trend_stack (1h) + PER-BOOK dedup (UNVERIFIED claim) — 2026-06-22 (PR #55)

Owner-directed forward experiment from an external overnight harness (owner reports n=804,
+0.1152R — **NOT verified in this repo**; shipped as an UNVERIFIED, separately-tagged paper book).
`paper.py`/`cli.py` gain `--clean-trend-stack`: gate to 13/50/800-EMA cleanly stacked one
direction for 10 bars AND a **widening** 13/50 gap (a separating trend; skips braided ones).
Setup tags gain `_cts`. **Key structural change — PER-BOOK dedup:** the one-open-trade key went
from `(symbol, timeframe)` to `(symbol, timeframe, book)` where `book` = the flag/venue suffix
(`_book_of()` strips the `…pct` prefix → `_tf_cts` etc.). WITHOUT this, §C (a strict subset of the
baseline 1h signals) collides with the baseline on `(symbol, 1h)` and logs NOTHING. The net-exposure
guard still caps COMBINED per-coin risk. Backward-compatible (baseline-vs-baseline behavior
unchanged). `385 passed`. **WATCH:** forward `_cts` record; revert §C step if net-negative.

## 54. Per-book Telegram summary + :35 read-only status heartbeat — 2026-06-22 (PR #56)

Enriched `format_summary` (3 gated blocks, message only grows when there's something to say,
back-compat tested): **per-book breakdown** (open count + unrealized R split core/trend/longs/tradfi,
validated `core` first), **best & worst** open by unrealized R, **today** = fee-net R closed since
00:00 UTC (`net_outcome_r`, so it matches the honest record). `review.open_trades_report` trades now
carry `setup` (book derived from it). **New workflow `paper-status.yml`:** `cron "35 * * * *"`,
`permissions: contents: read`, runs `notify-summary` ONLY — no scan, no journal write, no commit —
so it can't race the bot or trade a half-formed 1h bar. The 1h SCAN cadence is deliberately
untouched (validated book needs closed bars). Silent no-op without `TELEGRAM_*`. `390 passed`.

## 55. Deadline/stale-trade alert + de-flaked auth test — 2026-06-22 (PR #57)

4th summary block: `⏰ Expiring: SOL 2.1h • overdue: XRP` — open trades within 6h of (or past)
their deadline, via `hours_to_deadline` on the report (off `p.deadline()`), gated/omitted when
nothing's close. **Also fixed a PRE-EXISTING flaky test** (`test_tampered_cookie_is_rejected`):
it tampered the LAST 2 base64 chars of the 32-byte HMAC signature, but those carry padding
('don't care') bits, so the mutation sometimes decoded UNCHANGED → the "tampered" token stayed
validly signed → intermittent CI failure (keyed off the time-based `exp`). Fix: flip the FIRST
signature char (always 6 meaningful bits of byte 0). Stress-ran 40/40. Auth logic untouched.
`391 passed`.

## 56. §B dynamic volume universe — opt-in, OFF the validated path (NET-NEW, may differ from owner's spec) — 2026-06-22 (PR #58)

`universe_rank.py`: `rank_by_volume()` / `volume_ranked_universe()` rank a candidate pool by mean
`quote_volume` (exchange USD volume) over a lookback; unfetchable/delisted symbols skipped (never
fatal); `min_quote_volume` floor. `universe.CRYPTO_CANDIDATES` = broader liquid-major pool. CLI
`universe-rank` (read-only — ranks + prints, never trades). **HONESTY:** built from the descriptive
NAME; the owner's external §B spec is **not in this repo** (searched prior sessions), so this does
NOT claim to be it and may differ — structured to reconcile easily. **OFF by default, NOT wired into
`paper-trade.yml`** — the validated book still trades the static `TOP_10_CRYPTO`. Stub-tested (no
network) + live-smoked (BTC>ETH>DOGE by USD vol). `396 passed`. **NEXT:** owner confirms whether
this matches the intended §B or supplies the real spec to reconcile.

## 57. Traders-Reality M-level system — BUILT + measured; NO edge (do not ship) — 2026-06-22 (PR feat/tr-mlevel-system)

Built the full TR M-level grid (floor-pivot midpoints M0–M5 + R3/S3), prior-day color, and AMR band
in `build_levels` (lookahead-audited; kept OUT of the live-scored `LEVEL_COLUMNS` so the live
`factor_votes` stack is untouched), plus a per-bar `target_price` option in `bracket_backtest`
(scalar path byte-identical) so the harness can target specific levels. Then ran **6 candidates** that
test whether Tino's actual method adds edge, pooled across the top-10 majors (1h, ~4000 bars,
split-half + bootstrap p), baseline +0.081R:

| candidate | ΔR | n | p | h1/h2 | verdict |
|---|---|---|---|---|---|
| mlevel_reject (level-rejection vote) | −0.006 | 293 | 0.52 | −/+ | INCONCLUSIVE (neutral) |
| brinks_window (killzone-only entries) | +0.030 | 338 | 0.40 | +/− | INCONCLUSIVE (not robust, p≫0.05) |
| daycolor_target (M3/M1, M4/M2 targets) | −0.093 | 613 | 0.88 | −/− | HURTS |
| session_return (prior-session/Asian targets) | −0.139 | 561 | 0.97 | −/− | HURTS |
| mlevel_magnet (nearest-M-level target) | −0.132 | 765 | 0.97 | −/− | HURTS |
| daycolor_filter (fade extremes) | −0.290 | 140 | 0.98 | −/− | HURTS |

**NO WINNERS.** The dynamic-target ideas (magnet/day-color/session) HURT hardest — capping winners at
a nearby level forfeits the 3R right-tail the edge depends on (cand win-rate rises but mean-R falls).
Consistent with §2 (the confluence stack is saturated; price-derived structure doesn't add edge).
**Do not re-test these.** Levels remain available as frame columns for charts/other uses; nothing was
wired into the live stack or workflow. `415 passed`.

## 58. TR/BTMM weekly-cycle confluence layer — BUILT + measured; still NO edge — 2026-06-22 (PR feat/tr-confluence-candidates)

Extended §57 with the weekly-cycle features (`day_of_week`, `level_day`, `week_ib_high/low` [Mon+Tue IB,
NaN until Wed], `consec_run_len/dir` [completed bars only]) — all on the existing NY-day anchor,
lookahead-audited — and ran **all 12** TR/BTMM candidates pooled across the top-10 majors (1h, baseline
+0.0555R, split-half + bootstrap p). Spec gate: WINNER = Δ≥+0.015 ∧ both halves +ve ∧ p<0.05.

| candidate | ΔR | n | p | both+ | verdict |
|---|---|---|---|---|---|
| three_push_stophunt (fade a ≥3 run) | +0.144 | 122 | 0.19 | YES | INCONCLUSIVE (p≫0.05, n thin) |
| mlevel_reject | +0.029 | 289 | 0.40 | YES | INCONCLUSIVE |
| weekly_ib (fade into Mon+Tue box) | +0.025 | 539 | 0.39 | no | INCONCLUSIVE |
| brinks_window | +0.022 | 334 | 0.41 | no | INCONCLUSIVE |
| monday_skip | −0.035 | 583 | — | — | HURTS |
| monday_fade | −0.040 | 597 | — | — | HURTS |
| daycolor_target | −0.097 | 612 | — | — | HURTS |
| level_count_3day | −0.117 | 289 | — | — | HURTS |
| mlevel_magnet | −0.118 | 759 | — | — | HURTS |
| session_return | −0.131 | 560 | — | — | HURTS |
| daycolor_filter | −0.248 | 142 | — | — | HURTS |
| midweek_reversal | −0.380 | 74 | — | — | INCONCLUSIVE (thin, n<120) |

**WON: 0 · HURT: 7 · INCONCLUSIVE: 5.** No candidate clears the full luck-proof gate.
`monday_skip`/`monday_fade` HURT → Monday trades are NOT the drag (removing them removes good trades).
The only leads worth a *future* deeper look (NOT a ship): `three_push_stophunt` (Δ+0.144, both halves
strongly +ve, but n=122 ≈ floor and p=0.19) and `mlevel_reject` (robust both-halves but p=0.40). Same
verdict as §57/§2: this layer doesn't add a significant edge. Nothing wired live. `419 passed`.

## 59. three_push lead chased on 3x history — it EVAPORATED (TR/BTMM experiment CLOSED) — 2026-06-22 (PR feat/three-push-deepdive)

Followed up the only §58 lead (`three_push_stophunt`, Δ+0.144 / both halves +ve / n=122 / p=0.19) by
re-running it + 4 variants on **3x the history (12000 1h bars, 499 days vs the prior 4000)**, where the
baseline is a much harder +0.0068R (the 2025 window was leaner):

| variant | ΔR | n | h1/h2 | verdict |
|---|---|---|---|---|
| three_push_stophunt (the lead) | −0.031 | 392 | −0.136 / +0.081 | HURTS (no longer both-halves +ve) |
| three_push_pure (raw confluence, bigger n) | −0.040 | 476 | −/+ | HURTS |
| three_push_2r (nearer target) | −0.003 | 395 | −/+ | NEUTRAL |
| three_push_4 (>=4 run) | −0.139 | 116 | −/− | THIN |
| three_push_kz (killzone-gated) | −0.257 | 175 | −/− | HURTS |

**The lead was a small-sample artifact** — tripling the data flipped Δ+0.144 → −0.031 and broke the
both-halves robustness. This is the gate working as designed: the p<0.05 + both-halves requirement is
exactly what stops a lucky n=122 from being shipped. **TR/BTMM experiment is now CLOSED — 0 winners
across §57–§59 (28 candidate evaluations). Do not re-chase three_push.** The lesson (re-confirms §2):
the confluence edge is saturated and structural; more signals/structure don't add a luck-proof edge.
Nothing wired live; the M-level/weekly columns remain available for charts.

## 60. "Scan the top 30-40 most-liquid pairs" — BACKTESTED, REJECTED for live (HOLD) — 2026-06-22 (PR claude/arm-pay-yourself-exit)

The owner asked to widen the live scan to the top 30-40 most-liquid pairs. Instead of wiring it
(against §48), I backtested it: expanded `universe.CRYPTO_CANDIDATES` to ~40 liquid USDT pairs,
ranked by mean quote-volume, and ran the **canonical validated confluence bracket net of fees**
(`scripts/validate_volume_universe.py`, real Binance 1h, ~8000 bars). Split CORE (top-10 by vol)
vs TAIL (ranks 11-40):

| split | IS exp | OOS exp | OOS n |
|---|---|---|---|
| CORE (top-10) | −0.0125R | −0.0072R | 368 |
| TAIL (11-40) | −0.0251R | **+0.0373R** | 1087 |
| ALL (top-40) | −0.0219R | +0.0260R | 1455 |

The pooled OOS number for the tail looked *marginally positive* (+0.037R, > core) — **but the
significance-gated harness REJECTED it**: profitable OOS on only **3% of 30 assets**, median OOS
Sharpe **−2.60**, **effective-N 1.3** (median ρ=0.79 — the alts all move together), worst DD −62%.
The positive pooled blip is a **single-regime artifact**: 30 correlated alts riding one up-move in
the recent 30% OOS window, not a stable cross-asset edge. **RECONCILED VERDICT = HOLD / DO NOT WIRE**
(pooled-R and the harness must agree before even paper-trading; they don't). Re-confirms §48 (the
long tail bled). The expanded candidate pool + `volume_ranked_universe` stay OFF the validated path;
the live book remains **top-10 only**. `reconcile_verdict()` is unit-tested. Revisit only on more
history / across regimes, or as a separately-tagged paper book if the owner still wants forward data.

## 61. Dropped-run problem: it's the TRIGGER, not storage — heartbeat + denser cron + (owner) external trigger — 2026-06-22 (PR claude/arm-pay-yourself-exit)

Owner's pain: ~70% of scheduled runs drop, so Telegram goes quiet and trades are missed. He asked if a
**database** would fix it. **It would not** — the drops are GitHub Actions' best-effort `schedule:` cron
silently skipping runs (a *trigger* problem), not a storage problem. Three honest layers, in order of power:
1. **External reliable trigger → `workflow_dispatch`** — the bulletproof fix. **OWNER-ONLY to deploy**
   (needs his login + a fine-grained GitHub PAT with Actions:write; my integration token gets 403 on
   dispatch). Two equivalent options, both documented in **`docs/RELIABLE_TRIGGER.md`**: (A) **cron-job.org**
   — free website, no CLI, the owner's chosen path (POST the dispatches endpoint with the PAT in an
   Authorization header, body `{"ref":"main"}`, every 15 min); (B) the **Cloudflare Worker**
   (`cloudflare/trade-bot-cron`, PR #66) for those who prefer wrangler. Only one is needed.
2. **Denser in-repo cron** — bumped `paper-trade.yml` from 2→**4 attempts/hour** (`5,20,35,50`). Idempotent
   per-(symbol,tf,book) dedup makes re-scans safe (no dup OPENS); more independent attempts ⇒ higher chance
   one lands each hour. Costs only Action minutes.
3. **Run heartbeat / gap detector (NEW, this PR)** — `notifications/heartbeat.py`: `record-run` CLI stamps
   `data/heartbeat.json` each scan (bot-written, like the journal; committed by the scan). The Telegram
   summary now carries a health line: `⏱ Runs: last 8m ago • 22/24h covered`, or when dropping
   `⚠️ Scheduler gap 3h10m • only 9/24h covered (62% dropped) — deploy the external trigger`. `runs_24h`
   counts DISTINCT covered clock-hours (dense retries don't inflate it). This makes a silent scheduler
   VISIBLE — answers "I'd rather have accurate info than 70% dropped." Read-only in the summary; gated so
   absent heartbeat ⇒ no line (back-compat). 9 unit tests; `450 passed`.

**Answer to "slow down trades?"** — no; trade cadence isn't the cause, the hourly scan is fine and the
dedup already makes re-runs safe. The fix is reliability of the trigger + visibility, not fewer trades.
**The one thing still on the owner: deploy layer 1** (Cloudflare Worker) for a true fix; layers 2–3 are
shipped and reduce/expose drops in the meantime.

## 62. Owner's indicator suite (Bollinger/RSI+KDJ div/Fibonacci/spider/M-zone) — MEASURED — 2026-06-22 (PR claude/confluence-indicators-lab)

Owner asked to add Bollinger Bands (paired with RSI + KDJ divergence), Fibonacci-confluence, "spider"
(angled/Gann) lines, and M-zone/day-color gating to "build more confluence." Instead of bolting them
on (the stack is saturated, §2), built each as a causal indicator (`scripts/lab_indicators.py`:
bollinger, kdj, kdj_divergence, fib_confluence, spider_touch — no-lookahead, unit-tested) and as
GATE candidates in `scripts/overnight_candidates.py`, then ran the significance-gated harness
(baseline pooled +0.075R / 645 trades, top-10 1h). Verdicts (ΔR vs baseline; MIN_TRADES=120):

| candidate | verdict | ΔR | n | note |
|---|---|---|---|---|
| **bb_squeeze** | **SUGGESTIVE** | **+0.060** | 288 | both halves + (+0.033/+0.077). Bollinger SQUEEZE as a regime filter — the one real lead. Not a WINNER (didn't clear p<0.05). |
| osc_div_combo | THIN | +0.415 | 30 | both halves strongly + but n far below 120 — intriguing, unprovable yet |
| kdj_div_confirm | THIN | +0.247 | 25 | both halves + but thin |
| rsi_div_confirm | THIN | +0.066 | 18 | thin |
| spider_touch | THIN | +0.032 | 50 | not robust (h1 +0.38 / h2 −0.25) |
| bb_fade | THIN | — | 3 | no sample |
| bb_div_combo | THIN | — | 0 | combo too restrictive — zero trades |
| **fib_confluence** | **NEUTRAL** | +0.010 | 622 | fibs clustering with EMAs/pivots/opens = NO measurable edge |
| fib_at_price | HURTS | −0.057 | 377 | entering AT fibs hurts |
| mzone_band | HURTS | −0.033 | 473 | restricting to the M2–M4 band hurts |
| mzone_daycolor | HURTS | −0.132 | 357 | the day-color zone rule HURTS the validated book |

**Honest bottom line:** most of the suite washes out or hurts (re-confirms §2/§48 — more indicators
≠ more edge). The single survivor is **Bollinger SQUEEZE as a REGIME filter** (SUGGESTIVE, +0.06R,
both halves positive, n=288) — worth a confirmation run on 3× history before any paper book. The
oscillator-divergence combos look strong (+0.25–0.42R, both halves +) but are THIN (n=25–30): they
filter so hard there aren't enough trades to trust — need much more history/symbols to judge. Nothing
wired live; all gates stay in the candidate harness (off the validated path). `455 passed`.

### §62 addendum — LEVEL-CLUSTER ("magnet") is the real lead (2026-06-22)

Follow-up to the owner's question "what about when M2 lines up with a prior-day/weekly level or a
3-day-old daily open — they always come back to these areas, especially with vector candles." Built
`level_cluster()` (scripts/lab_indicators.py): counts INDEPENDENT levels stacking within 0.20 ATR of
the close — M-grid + pivots + session opens + prior day/week H/L + ADR/AWR + VWAP + round numbers +
**the last 6 days' daily opens** (causal, via daily_open day-grouping). Verdicts vs baseline +0.075R:

| candidate | verdict | ΔR | n | halves |
|---|---|---|---|---|
| **level_cluster (>=3 stacked)** | **SUGGESTIVE** | **+0.110** | 230 | +0.097 / +0.138 |
| level_cluster_strong (>=4 stacked) | THIN | +0.239 | 91 | +0.203 / +0.283 |
| level_cluster_vector (cluster + climax) | THIN | −0.185 | 46 | −/− |
| level_cluster_magnet (cluster as target) | HURTS | −0.076 | 495 | −/− |

**The owner's clustering intuition is VALIDATED** — entering only where ≥3 independent levels stack
roughly TRIPLES per-trade expectancy (+0.075→+0.185R) with both halves positive, and there's a clean
DOSE-RESPONSE (≥4 → +0.24R). This is the strongest forward-looking lead in the project so far (better
than bb_squeeze). NOT yet a confirmed WINNER (SUGGESTIVE, didn't clear p<0.05) — needs a confirmation
run on 3× history before a tagged paper book. **Honest counter-finding:** the vector-candle pairing
HURT (−0.185R) and using clusters as profit TARGETS hurt — the cluster is an ENTRY-LOCATION filter,
not a target or a vector-candle combo. Nothing wired live; stays in the candidate harness.

## 63. Level-cluster CONFIRMATION deep-dive — promising near-miss, NOT confirmed — 2026-06-22 (PR claude/level-cluster-confirm)

Chased the §62 level-cluster lead (3-pass `scripts/validate_level_cluster.py` on 3× history, 12000
bars top-10, + a 22-symbol power test). Findings:
- **PASS 1 (threshold×tolerance grid):** OOS-positive across nearly the whole grid; tol=0.20/K≥3 →
  +0.18R OOS (ΔR +0.12); dose-response holds (K=2→3→4 climbs). Robust to tolerance choice.
- **PASS 2 (ablation):** no single source group is essential — dropping any one keeps 87–136% of the
  edge (round-numbers most load-bearing at 66% when dropped). It's the STACKING, not one level type.
- **PASS 3 (robustness):** 8/10 symbols beat baseline OOS, but bootstrap **OOS p=0.18 / IS p=0.34** —
  not significant; IS half only +0.03R on top-10.
- **Power test (22 symbols, 8000 bars):** BOTH halves clearly positive (IS ΔR +0.093, OOS +0.081),
  IS p→0.07, **OOS p=0.22** — still not <0.05.

**Verdict: PROMISING NEAR-MISS, NOT CONFIRMED.** The cluster effect is consistently positive, dose-
responsive, cross-symbol and ablation-robust — but never clears p<0.05 OOS. The best near-miss in the
project (most leads fail sign/both-halves; this fails only statistical power). Per the honesty
contract: **NOT wired live, NOT claimed validated.** Defensible next step = a separately-tagged PAPER
book (like §C) to accrue forward trades and settle significance over time — owner's call. Do not
re-bolt the vector-candle pairing (HURT) or cluster-as-target (HURT); the edge is ENTRY-LOCATION only.
`level_cluster()` gained an `exclude_groups` ablation param. Nothing wired live; tests still green.

## 64. TR Level Intelligence — D1 persistence layer (BUILT, off the trading path; D1 UNVERIFIED) — 2026-06-22 (PR claude/tr-level-intelligence-qc4i2p)

A NON-CRITICAL side-channel that records what the bot already computes — it adds NO signal and
touches NO trading logic. New `kudbee_quant/intelligence/` package:
- **d1_client.py** — thin Cloudflare D1 REST client (`d1_query` / `d1_execute`).
- **level_recorder.py** — writes the LAST bar's full TR grid (M0–M5, pivots, opens, Asia/Brinks,
  ADR/AWR/AMR, EMA stack, week-IB, range-used, DOW/level-day) to `daily_levels` via INSERT OR
  REPLACE → idempotent per (date, symbol, timeframe). All 54 LEVEL_FIELDS verified present in
  `build_levels()` output.
- **vector_tracker.py** — upserts PVSRA `bull_climax`/`bear_climax` bars to `unrecovered_vectors`
  (INSERT OR IGNORE), then marks recovery within 0.3% tolerance (bull→low zone, bear→high zone) and
  updates `days_open`.

Wiring: `cli._record_intelligence()` runs AFTER `paper_scan()` (NOT inside paper.py — trading logic
left byte-identical), fetches a fresh 1h frame per symbol, and is gated on `D1_DATABASE_ID` +
wrapped in try/except per-symbol AND overall → a D1 outage can never block a scan or an alert.
Telegram: `/levels` `/history` `/vectors` (read-only; D1 errors degrade to friendly text).
Schema in `cloudflare/trade-bot-cron/migrations/0001_tr_levels.sql` (3 tables; `session_analytics`
defined but not yet populated). 9 new tests over an in-memory sqlite D1 proxy; full suite 474 green.

**HONESTY CAVEAT — D1 is UNVERIFIED end-to-end.** No Cloudflare creds/network in the build sandbox,
so: (a) `wrangler d1 create` + migration were NOT run (owner must, with their CF account);
(b) `wrangler.toml` `database_id` is a `REPLACE_WITH_DATABASE_ID` placeholder; (c) `/levels`
`/vectors` `/history` were rendered against an in-memory sqlite D1 (faithful proxy), NOT real D1.
The recorder only sees the scan's loaded window — a vector older than ~600 bars can't be re-checked
for price recovery (its `days_open` still ticks via SQL). Layer is OFF until the three CF_*/D1 env
vars are set; default path is a silent no-op.
