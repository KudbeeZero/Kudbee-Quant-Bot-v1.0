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
