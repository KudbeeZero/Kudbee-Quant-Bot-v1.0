# BRAIN.md — the cognitive architecture (every memory route, mapped by brain region)

> The container is ephemeral; the brain is git. This file is the single map of
> **every route to every memory layer** — code, data, and docs — organized like
> neuroanatomy so the whole system reads as one mind, not a pile of files.
>
> It does not replace the layer list in `kudbee_quant/memory/__init__.py` (L1–L7);
> it *deepens* it. Each region below names its real files and its subsections —
> the bread and butter. If a route isn't here, it isn't wired; add it.
>
> **Rule of this file:** every region cites real files. No aspirational anatomy.
> When a new capability lands, file it under the region it belongs to (or add a
> region) so the map never drifts from the code.

---

## The seven layers, as regions

The existing spine (`memory/__init__.py`): **L1 Semantic · L2 Episodic · L3
Experiment · L4 Procedural · L5 Working · L6 Reflective · L7 Loop**. Below, each is
placed in the brain, given subsections, and cross-wired to the regions it talks to.

---

## 🧠 Neocortex — long-term semantic knowledge (L1)
*What we know for sure. The slowest-changing store; the thesis lives here.*
- **Route:** `docs/MEMORY.md` (manual, git-versioned) + `docs/PHILOSOPHY.md`.
- **Subsections (association areas):**
  - **Validated lessons** — §1 the validated strategy; §9–§26 the measured facts.
  - **The honest scoreboard** — §2 what beats the null vs what's proven dead.
  - **Hard negatives** — settled "do NOT re-test" verdicts (trailing §72, psych-level
    §69, deadline re-backtest §70, VWAP rotation §74/§75). Re-testing these is a
    lesion, not curiosity.
  - **Standing user preferences** — the top of `MEMORY.md`; conventions the owner set.
- **Talks to:** the Reflective cortex re-grades what may enter here; the Hippocampus
  feeds it consolidated episodes worth generalizing.

## 🌊 Hippocampus — episodic memory: every trade, encoded → consolidated → retrieved (L2)
*The event log. Individual experiences before they become general knowledge.*
- **Route:** `data/journal.json` via `kudbee_quant/journal/`.
- **Subsections:**
  - **Encoding** — `log_alert` / `Prediction` write a new event (entry, stop, target).
  - **Consolidation** — the shared `backtest/resolver.py` turns an open event into a
    settled outcome (`outcome_r`); `check_open` sweeps pending → hit/miss.
  - **Retrieval** — `scorecard()`, `resolved_series()`, `venue_record()`,
    `source_record()` read the past back out (bot vs human, per venue, forward curve).
  - **Provenance guard** — cancelled/flattened statuses never pollute the scorecard
    (§50/§65/§66); a memory that lies about what happened is worse than none.
- **Talks to:** the Neocortex (episodes → lessons), the Reflective cortex (the ledger
  audits these events for luck), the sensory cortex (a signal becomes an episode).

## 🔬 Dentate gyrus / pattern-separation — the experiment store (L3)
*Every hypothesis and its verdict, kept distinct so we never re-run a dead end.*
- **Route:** `data/overnight_results.json`, `data/overnight_queue.json`,
  `docs/research/overnight_findings.md`; harness `scripts/overnight_research.py`.
- **Subsections:**
  - **Candidate registry** — `scripts/overnight_candidates.py` (each idea a function).
  - **Verdicts** — WINNER / SUGGESTIVE / NEUTRAL / HURTS / THIN, significance-gated.
  - **Pre-registrations** — `studies/*_preregistration.md` (lock the question first).
- **Talks to:** the Reflective ledger (family-wide re-grade), the Neocortex (a survivor
  may graduate to a lesson — only after forward proof).

## ⚙️ Basal ganglia — procedural memory: strategies as learned habits (L4)
*The trained action patterns. What the bot does without re-deciding from scratch.*
- **Route:** `kudbee_quant/memory/registry.py` (`Strategy`, `StrategyRegistry`);
  the validated config in `config/validated_defaults.py` is the ingrained habit.
- **Subsections:**
  - **The habit itself** — 1h · ≥50% confluence · 3R · 0.25-ATR maker retrace ·
    ride-3R (post-§76). Changing it is retraining, not a tweak — owner-gated.
  - **Candidate motor programs** — registered but not yet habitual (opt-in flags).
- **Talks to:** the Cerebellum executes the habit; the Neocortex says whether it's
  still validated; the Reflective cortex flags when a habit has decayed.

## 🎯 Prefrontal cortex — working memory + executive decision (L5)
*The here-and-now: what context a decision needs and the gate that makes it.*
- **Route:** `kudbee_quant/memory/working.py` (`WorkingMemory`), `bias.py` (BiasBook),
  and the live decision gate in `paper/paper.py` (`paper_scan`).
- **Subsections:**
  - **Directional bias** — `data/biases.json`: the human read that scalps trade WITH
    (§0 — the operating model). Human direction + machine execution = the edge.
  - **Open hypotheses** — the "what are we watching" queue.
  - **The gate** — confluence ≥ min_pct + trend filter + event-calendar block (§71),
    now reading CLOSED bars only (§77).
- **Talks to:** the sensory cortex (perception in), the Cerebellum (action out), the
  Amygdala (risk veto), the Hippocampus (the decision becomes an episode).

## 👁 Thalamus + sensory cortex — perception: raw bars → structured reality
*Sensory relay and the areas that turn ticks into meaning.*
- **Thalamus (relay):** `kudbee_quant/ingest/` — `binance.py`, `yahoo.py`, `router.py`,
  `cache.py`. Sensory intake, de-noised: drop the forming candle (§77), drop Yahoo's
  tick row (§29), TTL cache, gap/dupe validation. **Wrong input = hallucination**, so
  this is guarded hard (E2 cross-venue mislabel is a known open risk).
  - **Subsections:** fetch/paging, disk cache (atomic writes), OHLCV validation.
- **Sensory cortex (perception):** `signals/` (PVSRA vectors), `levels/` (the level
  grid, lookahead-audited via `shift(1)`), `confluence/stack.py` (10 factor votes → a
  score). This is where bars become "a setup."
  - **Subsections:** vector candles, key levels, the confluence vote stack.
- **Talks to:** the Prefrontal gate consumes perception; the Hippocampus stores it.

## 🤸 Cerebellum — fine motor execution: place the trade precisely (the "how")
*The edge is in execution. This is the trained, precise motor act.*
- **Route:** `kudbee_quant/execution/` (`paper.py`, `live.py`, `base.py`,
  `tiered_exit.py`, `exchange.py`) + `backtest/bracket.py`.
- **Subsections:**
  - **Entry** — 0.25-ATR maker limit retrace (maker, never taker — §25 taker kills it).
  - **Management** — ride-3R (§76); tiered exit config available, not deployed.
  - **The double gate** — `config/runtime.py::require_live_enabled` (paper unless BOTH
    live opt-ins). ⚠️ Pre-live motor deficits catalogued in
    `docs/audits/security-review-2026-07-02.md` (no venue-side stop, etc.) — must heal
    before live bring-up. Owner sign-off only.
- **Talks to:** the shared resolver (below) so backtest and live never disagree.

## 🌉 Corpus callosum — the shared resolver: one truth across hemispheres
*Backtest hemisphere and live hemisphere resolve trades through ONE pathway, so
they can never diverge (the §18 structural win).*
- **Route:** `backtest/resolver.py` — a pure function; `bracket.py` (backtest) and
  `journal/` (live) both delegate. No global state, no same-bar look-ahead.

## 🛡 Amygdala — threat & risk: the survival veto
*Fear, sized correctly. Stops the account from dying before the edge pays.*
- **Route:** `kudbee_quant/risk/` (correlation guard, drawdown guard, session sizer,
  Kelly / risk-of-ruin) + `execution/killswitch.py` + `exposure.py`.
- **Subsections:**
  - **Daily loss kill-switch** — fail-closed cap on a bad day (pre-live gaps flagged).
  - **Exposure guard** — per-coin gross-risk cap (net-exposure, §14).
  - **Sizing** — quarter-Kelly / ~1% risk; leverage is a cap, never the bet (§13/§22).
- **Talks to:** vetoes the Prefrontal gate; the Reflective cortex tunes its priors.

## 🧭 Anterior cingulate — error monitoring: "am I fooling myself?" (L6)
*The self-critic. Catches luck wearing the mask of edge.*
- **Route:** `kudbee_quant/memory/reflection.py` + `memory/testing_ledger.py`
  (`family_ledger`); `scripts/reflect.py`.
- **Subsections:**
  - **Multiple-testing ledger** — re-grade every "winner" under BH-FDR over everything
    ever tried (§18/§19). Expected false winners under noise ≈ N·α.
  - **Regime / overfit alarms** — is this edge regime-fragile? Split-half stable?
  - **Contamination check** — before shipping on a prior study, verify its data/code
    era doesn't overlap a since-confirmed bad window (§76 — the SOL-rotation lesson).
- **Talks to:** gatekeeps what enters the Neocortex; grades the Loop's own calls.

## 🔄 Anterior PFC / metacognition — the self-improving loop (L7)
*The layer that grades its own judgments over time.*
- **Route:** `kudbee_quant/memory/loop_agent.py` (`LoopAgent`, `format_cycle`).
- **Subsections:** per-book drift calls → later self-scoring; reliability calibration
  (empty until it accrues graded cycles — do not trust its proposals cold, §64).

## 🫀 Brainstem — autonomic life support: keep breathing while asleep
*Involuntary. Runs whether or not a chat is awake.*
- **Route:** `.github/workflows/paper-trade.yml` (hourly scan+resolve+commit),
  `paper-status.yml`, `cloudflare/trade-bot-cron/` (reliable external trigger),
  `data/heartbeat.json` (run telemetry).
- **Subsections:** the cron heartbeat, the Telegram afferent/efferent nerves
  (`telegram_commands.py` + `notifications/`, owner-allow-listed, paper-only `/yes`),
  the D1 level-intelligence store (parked until provisioned, §67).

## 🪢 Hippocampal replay across sleep — continuity of self between sessions
*The container is wiped like sleep; identity survives via the baton. This is how
"the same team" persists across amnesia.*
- **Route:** `docs/HANDOFF.md` (the baton), `docs/SESSION_PROTOCOL.md` (relay ritual),
  `docs/AGENT_ORCHESTRATION_LEDGER.md` (session→branch→PR→audit timeline),
  `docs/audits/` (per-unit gate evidence).
- **Subsections:** wake (`/handoff-audit`), sleep (`/closeout`), the ledger's honest
  deviation log. **This is the file that makes the brain a *team* and not a goldfish.**

---

# Part II — the creative & decision-making brain (how a mind *makes* and *chooses*)

The regions above run the machine. But music isn't played by the motor cortex alone,
and a fork in the road isn't crossed by memory alone. Creation and choice recruit a
second network. This part maps it through the lens the owner set: **how a brain
creates music**, and what makes a **crossroads decision** a good one.

## How a brain writes a song (and how ours writes an edge)
A musician improvising is running four systems at once: the **Default Mode Network**
imagines the next phrase, the **auditory/temporal cortex** hears whether it fits the
rhythm and key, the **reward system** lights up when it *resolves*, and the
**prefrontal cortex** vetoes the notes that break the piece — all in a loop, fast,
with the inner critic turned down just enough to let ideas out. Making an edge is the
same loop: imagine a candidate, hear it against the market's rhythm, feel the reward
if it survives, veto it if it's overfit.

## 🌌 Default Mode Network — imagination & improvisation (where NEW ideas are born)
*The mind-wandering network. In musicians it DE-activates the inner critic during
improv so novel combinations can surface. This is the muse — and our idea factory.*
- **Route:** `scripts/overnight_candidates.py` (each candidate = an improvised phrase),
  `scripts/overnight_research.py` (the jam session), the idea backlog
  `docs/research/overnight_idea_backlog.md`.
- **Subsections:**
  - **Generation** — propose candidate edges in execution/regime/sizing (never "one
    more indicator" — §2 parsimony is the key signature).
  - **Divergent play** — many ideas cheaply; most will be killed. That's the point.
- **Generative layer (built 2026-07-02, §79):** `scripts/idea_generator.py` composes
  NEW candidates by combining primitives — a regime GATE × an execution OVERRIDE — so
  the DMN is no longer a fixed registry but an open-ended generator (7 gates × 6
  overrides → dozens of fresh combos the hand-written set never enumerated). It dedups
  against everything already tested (`data/overnight_results.json`) and the hand-written
  registry, and enqueues survivors for the SAME significance gate. It PROPOSES; it never
  claims. `--list` / `--emit N`.
- **Talks to:** the reward system scores each phrase; the anterior cingulate (the
  critic) kills known dead ends before generation and overfit ones after testing.

## 🎼 Auditory / temporal cortex — rhythm, harmony, the market's meter
*Music is pattern in time: pitch, rhythm, harmony. Markets have meter too — sessions,
the weekly market-maker cycle, killzones. This region hears the beat.*
- **Route:** `levels/` session/cycle features (`week_phase`, `cycle_phase`,
  `killzone`, Brinks boxes), `signals/pvsra.py` (the market's dynamics/volume "accent").
- **Subsections:** session rhythm (Asian→London→NY), the weekly cadence (§24 MM
  cycle), volume accents (PVSRA vector = a climax note).
- **Talks to:** feeds the sensory cortex's perception; the reward system prefers
  setups *on the beat* (killzone edge, §16).

## ✨ Dopaminergic reward system (VTA → nucleus accumbens) — valuation & "this feels right"
*The chills when a chord resolves. Dopamine is not pleasure — it's PREDICTION ERROR:
reward vs expectation. It's how the brain learns which choices pay.*
- **Route:** the R-multiple is our reward signal — `outcome_r` / expectancy in
  `scorecard.py`; the meta-model's P(win) (`ml/meta_model.py`) is a learned value head;
  the overnight verdict is the reward that reinforces a candidate.
- **Subsections:**
  - **Reward** — expectancy in R, net of fees (the only reward that counts).
  - **Prediction error** — forward result vs backtest prior (the live-vs-backtest gap
    IS a prediction error the brain must learn from — §48/§77).
- **Talks to:** trains the basal ganglia (habit) and the OFC (value-based choice).
  **Anti-addiction guard:** a win must clear the significance gate before it earns the
  word "edge" — dopamine lies, the ledger (anterior cingulate) doesn't (§19).

## 🧮 Orbitofrontal cortex — value-based choice & reversal learning (the chooser)
*The region that compares options by expected value and, crucially, UPDATES when the
world changes (reversal learning). Damage here = smart but terrible decisions.*
- **Route:** the decision surface is the new **Crossroads Board** (`docs/CROSSROADS.md`)
  — every open fork with its expected value, options, and recommendation.
- **Subsections:**
  - **Compare forks by value** — not "is this good" but "is this the *best* use of the
    next unit of work / risk."
  - **Reversal learning** — when evidence flips, flip the decision (the VWAP
    momentum→rotation→momentum arc §44/§74/§75 is textbook reversal learning; the
    contamination-window rule §76 is the OFC refusing to trust a stale contingency).
- **Talks to:** reads value from the reward system, uncertainty from the insula,
  conflict from the anterior cingulate; writes the chosen action to the prefrontal gate.

## 🫁 Insula — interoception & the gut check (felt uncertainty)
*The "gut feeling." Damasio's somatic-marker hypothesis: good decisions need a felt
sense of risk, not just logic. The insula reports how uncertain the body is.*
- **Route:** our gut is quantified honesty — the bootstrap **p-value** and Wilson CIs
  (`events/study.py`, `cluster.py`), the "UNVERIFIED / low-confidence" tags all over
  `MEMORY.md`. A high p is a queasy gut: don't act.
- **Subsections:** significance as felt-uncertainty; sample-size caveats ("n too thin"
  is nausea); the honest "this is a hypothesis, not a promise" reflex.
- **Talks to:** vetoes the OFC when the gut says *not proven* even if the mean looks good.

## 🧭 Frontopolar cortex (BA10) — explore vs exploit (the strategic fork)
*The most human, most anterior region: holding a goal while considering alternatives —
keep milking the known edge, or spend risk exploring a new one?*
- **Route:** the standing tension between the **validated book** (exploit — §1/§76) and
  the **research harness** (explore — L3/DMN); the Crossroads Board makes the trade-off
  explicit each session.
- **Subsections:** exploit (run the validated config forward), explore (test candidates
  off the live path), and the budget split between them.
- **Talks to:** sets the agenda the OFC then prioritizes.

## 🕯 Limbic valence — emotion as information (the human read)
*Emotion isn't noise to a creator — it's data. In our §0 operating model, the BOT must
be emotionless, but the HUMAN's felt read supplies direction the machine can't derive.*
- **Route:** `bias.py` / `data/biases.json` (the human direction the bot scalps WITH),
  `journal` `source='human'` (scored apart from the bot).
- **Subsections:** human direction as input; strict separation so emotion never leaks
  into the bot's mechanical gate (that separation IS the edge, §0).

---

# The Crossroads Board — real decision-making, in one place

The regions above are the *council*. `docs/CROSSROADS.md` is where they sit down: a
living board of every open fork — the evidence, the options, the recommended default,
and whether it needs the owner. It is the OFC's desk. Keep it current: a decision made
or deferred should move on the board the same turn, or the council is deliberating on
stale information.

---

## How the brain learns (the write-paths that keep it alive)

A brain that never updates is a fossil. Three reflexes keep this one growing — see
the **self-updating memory** rule in `CLAUDE.md`:

1. **A repeated instruction** → write it to the region it governs (a convention →
   `CLAUDE.md`/`SESSION_PROTOCOL.md`; a trading fact → `MEMORY.md`).
2. **A new agreed convention** → same, immediately, so it's honored next session.
3. **The same mistake twice** → a hard-negative or a guard + a test, so the lesion
   can't recur (e.g. §77 the forming-candle test; §75 the VWAP sign-pin test).

The map is only true if it's maintained. Adding a capability without filing it here
is how a brain develops a blind spot.
