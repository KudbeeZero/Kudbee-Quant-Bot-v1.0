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
STILL OPEN (honest): journal R is GROSS of fees, so the 0-fee edge shows up as
"net≈gross for TradFi vs crypto loses ~0.09%/trade" only when we score NET — a
follow-up (subtract per-venue fee in scorecard). And TradFi session/RTH handling in
build_levels is unverified (NY-range logic assumes 24/7) — watch the `_tradfi` record
for level-quality artifacts before trusting it.

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

## 28. Net-of-fee scoring — the zero-fee TradFi edge is now MEASURABLE — 2026-06-09

Closed the §26 open follow-up ("journal R is GROSS of fees"). The scorecard now
reports R both gross and NET of a per-VENUE round-trip fee, so the §26 promo edge
is visible instead of implied.

WHAT SHIPPED (first chat under the §27 relay; audited+merged the bootstrap PR #2,
then built this):
- `journal/fees.py`: venue is read AUTHORITATIVELY from the symbol spec (the same
  routing signal the paper loop uses) — `yahoo:` = TradFi (0-fee promo), else
  crypto. `fee_in_r` converts a round-trip fee% to R via `fee_pct * entry /
  |entry-stop|` (R is risk-normalised, so a price-% cost must be divided by the
  risk width). Non-bracket trades (no stop) can't be sized → charged 0.
- `Journal.scorecard()` gains `net_expectancy_r` / `net_total_r`; CLI `journal
  score` renders + explains them. TradFi rows keep net == gross; crypto rows pay
  the drag — the GAP between the columns IS the zero-fee edge.
- Config (scoring-only, `FEE_PCT` untouched/off-limits): `CRYPTO_FEE_ROUNDTRIP =
  0.0008`, `TRADFI_FEE_ROUNDTRIP = 0.0`.

HONEST UNKNOWN (the one thing to nail down): the crypto rate 0.0008 is an ASSUMED
maker round-trip. It sits ABOVE `FEE_PCT`'s 0.0004 "round-trip maker" backtest
figure and BELOW the §25 MEASURED taker (0.0009 rt) — i.e. deliberately
conservative (it UNDER-states net edge, the safe direction). But `FEE_PCT=0.0004`
and `CRYPTO_FEE_ROUNDTRIP=0.0008` are 2x apart and BOTH claim to be "maker" — that
contradiction is unresolved until ONE real limit (maker) fill confirms the true
rate (still the §25 OPEN ITEM). Until then the constant is FROZEN (don't drift it
without a real fill). Tests: fee charged on crypto not TradFi, the fee→R math, and
the per-venue net split. Suite 168 passed.

STILL GROSS (next chat's scope): only the per-setup *scorecard* is net so far. The
forward EQUITY CURVE (`resolved_series`) and `source_record` still report gross —
so the same book shows two different numbers. Make them net too for consistency
(`claude/net-of-fee-equity-curve`) before anyone misreads a gross figure as net.
