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
