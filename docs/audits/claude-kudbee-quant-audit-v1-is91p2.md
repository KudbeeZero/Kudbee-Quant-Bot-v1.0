# Audit — repo-state audit (audit-first, SYSTEM ROLE v2.2) — 2026-07-01

- **Session branch:** `claude/kudbee-quant-audit-v1-is91p2` (harness-assigned)
- **Scope:** state-of-repo audit against six known open items + website fast pass.
  READ-ONLY on code/config/live trading; this report is the only artifact.
- **Verification basis:** full test suite run in this container: **716 passed, 0 failed**
  (49s). Journal at HEAD: 828 predictions / 681 resolved / 2 open-pending.
  Clone is shallow (50 journal-sync commits); history checks done via the GitHub API.

## 1. Current repo state

- Branch = `main` + routine bot journal syncs only; working tree clean.
- **No open PRs.** #118 (website polish + SEO) and #117 (§41-gap pre-registration)
  were both merged 2026-06-27 on the owner's "close and merge all PRs".
- **Audit status per baton: `AWAITING_AUDIT`** — post-hoc audits of #118 + #117 are
  due (like #103/#84 before them). This report is NOT that audit (see Next Baton).
- MEMORY.md last updated **2026-06-25** (§72 is the last section) — two sessions
  of results (study #116, the forward shadow scorer, and a live-geometry change,
  all below) are **not yet recorded in MEMORY**.

## 2. Known-item verification (confirm/update, not rediscovery)

### 2a. Breakeven exit (tp1) wiring — premise STALE; something more important found

- `--tp1-r 1.0` **IS wired** in `.github/workflows/paper-trade.yml` on both live
  steps (baseline 1h line 77, §C line 109) — but with **`--tp1-frac 0.5`
  (bank-half + BE)**, not the `0.0` breakeven-only variant the item asked about.
- History: §49 / PR #47 (2026-06-21) armed `--tp1-frac 0.0` (breakeven-only).
  Commit **`8f3b7f14`** (2026-06-24, "fix(paper): bank 50% at TP1") flipped it
  `0.0 → 0.5`. That change has **no MEMORY section and no PR number in the
  message** (same session as the owner-approved direct-to-main `c43b8a7`).
- **The material finding:** the geometry that commit made live — bank-half/BE —
  is exactly **geometry B**, which both the paired backtest (#116: B −0.055R vs
  A ride-3R −0.007R, A−B=+0.048R, paired boot_p 0.000, n=3,730) and the forward
  shadow re-score (B −0.155R vs A −0.053R, A−B=+0.102R, n=112) rank as the
  **worst of the three variants measured**. No live change is proposed here
  (governance requires the §41 gap explained first — see 2c) — but the live
  book is currently running the measured-worst management rule, and that fact
  is undocumented in MEMORY.
- `kudbee_quant/execution/tiered_exit.py` (3-stage TP1/TP2/runner config) is a
  config layer over the shared resolver and is **NOT deployed anywhere** — the
  paper-scan CLI exposes no TP2/runner flags and no workflow references it.
- `flows/paper_trade_cycle.yaml` is a Kestra **scaffold, not stood up** (header
  says so); it carries no tp1 flags at all. Not a live surface today.

### 2b. Ride-3R vs Bank-Half/BE shadow validation — SHADOW-ONLY (governance respected)

- `studies/management_shadow_results.md` (n=112 real resolved 1h trades):
  A −0.053R / B (live) −0.155R / C −0.062R; **A−B forward = +0.102R**,
  corroborating #116's +0.048R. Mechanism DIFFERS between forward and backtest
  (forward: the BE-slide is the dominant drag, C−B=+0.093R; backtest: the
  partial close dominates, A−C=+0.035R).
- Status: **still shadow, on-demand only, not wired to any cron** — exactly as
  governance requires. The study itself states any live change needs a separate
  human-approved PR and that the §41 gap must be explained first.
- **Provenance note for the #118 post-hoc audit:** the shadow scorer + results
  + tests shipped **inside PR #118**, whose baton entry claims the diff is
  "marketing-surface only". The code is read-only research (benign), but the
  scope claim in HANDOFF is inaccurate and must be recorded honestly.

### 2c. §41 gap investigation — PRE-REGISTERED, NOT YET RUN (open)

- `studies/section41_gap_preregistration.md` merged via PR #117 (2026-06-27).
  Hard rule: results only after the prereg is on `main` — it now is.
- **No results file exists anywhere in the repo** → the investigation has not
  been executed. It remains the gating item before any management/governance
  proposal (the +0.096R §41 anchor vs −0.007R reproduction, and the 8,124 vs
  3,730 n-gap, are still unreconciled).

### 2d. Live-forward vs backtest execution/fill-quality gap — NO new study since last review

- Nothing new in `research/` or `docs/audits/` on fill quality/latency. What
  stands: §48 ("majors/1h ~breakeven live vs ~+0.2R backtested — a real
  backtest→live gap may remain"), §61 (dropped runs are a GitHub cron TRIGGER
  problem; heartbeat + 4 attempts/hour shipped; the bulletproof Cloudflare
  Worker cron is built but owner-deploy is still pending), and the §44
  assessment that this bot has no intra-hour execution path to "speed up"
  (bar-close signals; cron delay = resolution latency, not fill-price decay).
- The question has effectively been **absorbed into the §41 gap investigation**
  (its hypothesis #1, population/n-gap, is the strongest lead).
- **New forward datapoint (this audit):** the §70 24h-deadline watch trigger is
  **MET** — 56 core 1h trades resolved since 2026-06-24 (+16.93R gross,
  +0.302R/trade) plus 36 `_cts` (+0.461R/trade). Both positive so far under the
  shorter window; the formal `journal-score` comparison vs the pre-#96 baseline
  is now due (raw gross figures here, not the net-of-fee scorecard).

### 2e. Hard-negative list — NO drift found

Checked against the live scan path (`paper-trade.yml` → `paper-scan` defaults):

| Hard negative | Status |
|---|---|
| Raised confluence gate | CLEAN — `--min-pct` not passed; default 0.5 (validated floor) |
| Psychological round-level entries (§69) | CLEAN — exists only in `scenarios/library.py` + overnight candidates (research), not the live path |
| Size-by-confluence (§17) | CLEAN — overnight candidate only |
| Wider stops | CLEAN — `--stop-atr` not passed; default 1.5 (validated) |
| Variance-ratio trend filter (§17) | CLEAN — overnight candidate only |
| `--trailing-atr` (§72 settled negative) | CLEAN — default `None`, absent from workflow |
| Killzone gate (unarmed until 1h-validated) | CLEAN — flag exists, not passed |

### 2f. Live-trade governance / security — PASS (hard check)

- **Double env opt-in** (`TRADING_MODE=live` + `ENABLE_LIVE_EXECUTION=true`)
  enforced at the single choke point `config/runtime.py:require_live_enabled`,
  called at `LiveExecutor` **construction** AND re-checked on every `submit()`.
  Default config raises `LiveExecutionBlocked`. Unknown mode fails safe (raises).
- **No autonomous path to a live order:** `LiveExecutor`/`build_executor` are
  exported but **invoked nowhere** in the CLI, workflows, or scan path — the
  scheduled Actions run `paper-scan`/`journal-check` only. The Kestra scaffold
  pins `TRADING_MODE=paper`, `ENABLE_LIVE_EXECUTION="false"`.
- **Kill-switch intact:** `killswitch.py` checked before every live submit;
  losses-only accumulation (winners don't bank headroom); plus concurrency cap,
  `MAX_POSITION_SIZE_USD` cap, and maker-only limit orders.
- **Telegram `/trade` → `/yes` is PAPER-ONLY** ("never an exchange call"),
  60-second confirmation TTL, one-time gate. Human approval remains structurally
  required for anything live. **The AI cannot fire a live trade autonomously.**

## 3. Website fast pass (vs what the engine actually supports)

Delegated page-by-page review; net result:

- **COMPLETE (11):** index, lab (data regenerated 2026-06-27), methodology,
  glossary, leverage-report, trade-story, trade-flow (both intentionally
  noindex), contact, 404, blog hub + 7 posts.
- **PARTIAL (5):** compare, start-here, about, be-report, live-signals —
  functional but on the unfinished-polish list; live-signals depends on the
  backend `/api/signal` being reachable (graceful offline fallback, no fake
  static data).
- **No fabricated stats found.** All quantitative claims trace to the engine,
  journal, or a named study. Honest-voice norm holds.
- **Flags:**
  1. `index.html` cites the walk-forward "median ~+0.19–0.24R/trade" — true to
     MEMORY §1 (backtest), but stronger than the lab page's recent-sample
     0.049R; a reader can confuse backtested with live expectancy. Context
     wording, not fabrication.
  2. `be-report.html` is indexable but missing from `sitemap.xml` (post-dates it).
  3. Placeholder domain `kudbeequant.com` still sitewide (known; baton already
     flags the find-replace once the real domain is chosen).
  4. The remaining SEO/polish work matches the baton's NEXT-chat scope in
     `studies/website_polish_progress.md` (trade-story/flow meta, be-report
     meta, sitemap lastmod, llms.txt, global pass, responsive).

## 4. Honesty ledger (discrepancies this audit must put on record)

1. **Undocumented live-geometry change:** `8f3b7f14` (2026-06-24) flipped the
   live TP1 fraction 0.0 → 0.5 with no MEMORY section and no PR trail — and the
   resulting bank-half/BE rule is the measured-worst management variant (#116 +
   shadow). Needs a MEMORY entry and an owner-visible decision record.
2. **PR #118 scope claim inaccurate:** baton says "marketing-surface only / NO
   change under kudbee_quant/", but #118 carried the management shadow scorer,
   its results, and tests. Benign read-only research, wrong claim — the post-hoc
   audit of #118 must record this deviation.
3. **MEMORY is 2 sessions stale:** no §73+ for study #116, the shadow results,
   or the 8f3b7f14 change.
4. **Post-hoc audits of #118 + #117 are due** (`AWAITING_AUDIT`), per protocol.
5. Baton's "582 tests green" is superseded: **716 pass** at HEAD (suite grew;
   nothing failing).

## 5. Recommendation — smallest safe next step (owner approval required)

**Docs-only reconciliation unit** on a scoped branch, e.g.
**`claude/post-hoc-audit-118-117`**:

1. Run the protocol post-hoc audits of **#118 and #117** (diff vs claims —
   including the #118 scope discrepancy above) → `docs/audits/`.
2. **MEMORY §73**: record study #116 + the forward shadow result + the
   `8f3b7f14` tp1-frac 0.0→0.5 change (and that live currently runs measured-
   worst geometry B, pending §41-gap resolution).
3. Append the orchestration-ledger rows; refresh the baton (including: the §70
   50-trade deadline checkpoint is reached — run the formal `journal-score`
   comparison).

No code, no workflow, no live-config change. The first *research* unit after
that should be **running the pre-registered §41 gap investigation**
(read-only, branch suggestion `claude/section41-gap-run`) — it gates everything
management-related, including any future decision about tp1-frac.

## Net

Governance/security: **PASS**. Hard negatives: **no drift**. Tests: **716/716**.
Open risks are documentation debt (undocumented live-geometry change, stale
MEMORY, due post-hoc audits) and the unrun §41 investigation — not code drift.
