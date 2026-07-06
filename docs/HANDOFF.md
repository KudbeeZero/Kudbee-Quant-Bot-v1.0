# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`, streaming (no branch/PR for this chat — see below).
  This session (2026-07-06, continuation of the `claude/n4-ps42u7` chat, running under
  an owner standing directive to keep working the queue autonomously and keep
  everything merged/green): shipped **N4** (PR #140, MERGED), merged **PR #138**, stood
  up the **Branch Execution Ledger** (135 branches classified,
  `docs/AGENT_ORCHESTRATION_LEDGER.md`), got owner approval on **X5** (packaged as
  `scripts/delete_dead_branches.sh` — owner runs `--run`, agent containers can't delete
  remote refs), shipped **N5** (deploy/CI hardening, §85), ran a full **Telegram audit**
  (§86, no-server polling command answerer — confirmed live via 2 green scheduled runs
  — fill-event ping, `daily_recap` armed), shipped **N6** (research-honesty fixes, §87,
  all 5 items), and shipped **N7** (ledger harvests, §88) — the LAST item in the
  §83-review agent queue, closing it out entirely: conf_70/psych-1h/VAH-trap verdicts
  recorded in MEMORY, the #102/#14 audit reports landed in `docs/audits/`, the no-JS
  site fix confirmed already live, and `scripts/delete_dead_branches.sh` extended to
  cover all 123 deletable branches (102 dead + 21 superseded, pinned-SHA verified).
  **Agent-side queue is now EMPTY** — everything left on `docs/CROSSROADS.md` is an
  owner-decision row (X1-X5). All direct commits to `main` (streaming) — no PR opened
  this session. Suite: 772/772; CI confirmed green through `190a6745` (N6).
- **New session (2026-07-06, this branch):** the prior session ended abruptly. Audited
  PR/branch state fresh (0 open PRs, all recent PRs through #140 merged, working tree
  clean, this branch had 0 unpushed commits — nothing left dangling). Picked up the one
  remaining agent-actionable backlog item: **N2 phases (b)/(c)**, splitting the Pine
  indicator suite into standalone tools — shipped, MEMORY §90, direct-to-`main`. Pine-only,
  no Python/engine/live changes.
- **⚙️ WORKFLOW (2026-07-02, owner-set):** STREAMING & actionable — commit low-risk/docs/verified
  work directly to `main`; open a PR only when it earns one (large/risky, the money path, a
  preview-worthy visual, or a requested review); merge-on-green when the owner has authorized it.
  See `CLAUDE.md` + `docs/BRAIN.md`. Self-updating memory: repeated instruction / new convention /
  twice-made mistake → save it as you go.
- **🧭 THE LIVE DECISION SURFACE IS `docs/CROSSROADS.md`, NOT THIS SECTION.** Every open fork
  (owner-decisions, do-next, watch) lives there with evidence + a recommended default, and gets
  moved the same turn a decision is made. **Read it, not a narrative recap here.** Current open
  owner rows: **X0** (historical record), **X1** (live pre-live gate — 8 latent bugs, money path,
  needs sign-off), **X2** (bring-up checklist, now 6 steps: DNS→Cloudflare, Pages custom domain
  incl. `www`, **deploy the API to Fly.io**, Email Routing, Worker `TRIGGER_SECRET`, and the
  **`KUDBEE_API_TOKEN` repo secret** — §86 found this last one missing, and it's what would let
  Telegram commands answer instantly instead of via the ~10-20min polling fallback), **X3**
  (transparency posture), **X4** (§83 core-engine fixes, change-gated, needs sign-off), **X5**
  (branch cleanup — **APPROVED**, script ready, owner runs `bash scripts/delete_dead_branches.sh
  --run`). ~~N4~~/~~N5~~/~~N6~~/~~N7~~ all shipped 2026-07-06 — the agent-side queue is empty.
- **Verify live:** CI confirmed green through `70a95397` (N7) and every workflow this
  session. `fly-deploy.yml` genuinely no-ops every run (`FLY_API_TOKEN` unset, confirmed
  from live job logs, not a workflow bug) — **owner explicitly deferred the Fly deploy**
  to self-serve later via `docs/HOSTING.md` (asked directly this session). Not a stalled
  item; don't re-raise unprompted (see CROSSROADS X2). Cloudflare Pages (the marketing
  site) auto-deploys from `main` on every push and stays in sync regardless.
- **✅ MOST RECENT WORK (2026-07-05, this branch):** Fable-5 **full-codebase review** — owner
  directive after the Fable 5 release: re-read every subsystem with fresh eyes and reconcile all
  docs/memory layers. Five independent reviewer agents swept core/ops/research/infra/docs;
  PR #137 post-hoc audited **PASS** (740/740 green). Nothing invalidates §1. Key finds: journal
  durability gaps (non-atomic save, no per-symbol isolation, NaN pass-through), core-engine
  causality bugs (London Brinks lookahead, entry-bar fill blind spot), ML honesty gaps (CV purge
  leak, fill-bar features), infra drift (telegram-register self-healing against dead Render —
  FIXED; flyctl@master unpinned). Everything filed: MEMORY **§83** + CROSSROADS X3/X4/N4–N6;
  ~15 docs reconciled (README, runbooks, ledger, PHILOSOPHY, etc.).
- **Prior work (2026-07-03, PR #137, merged + post-hoc PASS):** weekly status; two exit-management
  proposals honestly tested and **rejected** — 1.2R/0.5-ATR (§81, reconfirms §10) and stop-to-TP1
  (§82, HARD-NEGATIVE, loses on all 6 coins). No live config changed.
- **Audit status:** PR #137 `MERGED (post-hoc PASS, 2026-07-05)` — audited **twice, independently,
  by two parallel 2026-07-05 sessions** (a real parallel-chat collision, recorded honestly): reports
  `docs/audits/claude-weekly-trades-status-z8thda.md` and `docs/audits/pr-137.md`, both PASS,
  suite 740/740 green at head. Prior:
  `PASS` (2026-07-02, post-hoc on streaming commits); PR #127 repo-state audit + post-hoc
  #118/#117 (2026-07-01), MEMORY §73. Full narrative: `docs/MEMORY.md` §74–§82.
- **⚠️ PROCESS NOTE:** this baton had gone stale (last reconciled 2026-06-27) while the workflow ran
  streaming — nothing forces a baton update the way a PR-per-chat merge gate used to. Reconciled
  2026-07-02. If a future chat notices the baton lagging `docs/MEMORY.md`'s highest `§` number again,
  that's the same gap recurring — update it as part of `/handoff-audit`, not just `/closeout`.
  **Corollary (third occurrence, 2026-07-05): `/handoff-audit` must always check for open PRs
  directly via the GitHub API — never assume the baton's PR list is exhaustive.** Nothing on
  `main` forces a baton write when a PR is opened; only `/closeout` writes it, on a branch,
  pre-merge — so an open PR can be invisible to anyone reading only the baton.

## What recent chats did (for the auditor to verify against the diff / MEMORY)

- **This session (2026-07-06, streaming on `main`, no branch):** merged PR #140 (N4) + PR
  #138 (resolving their baton collision in the process); built the Branch Execution Ledger
  (135 branches: 66 merged + 36 patch-equivalent = 102 dead, 16 superseded, 12 unique-value,
  1 salvage-hold) and got owner sign-off on X5 (packaged as a script, not executed directly —
  agent containers can't delete remote git refs, confirmed via a failed `push --delete`
  test); shipped N5 (flyctl SHA-pin, workflow `permissions:`, `requirements.lock`, Fly-aware
  webhook base-URL resolution, MATIC delisting cleanup, Kestra-flow universe alignment,
  `/summary` copy fix — MEMORY §85); ran the owner-requested Telegram audit end-to-end using
  live evidence (Actions logs, `getWebhookInfo`, state files, not code claims) — found
  outbound alerts genuinely working, slash commands genuinely dead (no registered webhook)
  and the scheduled digest suite silently unable to be enabled at all (no flag-forwarding
  path existed); fixed the enable-path, added a no-server polling command answerer, added
  a fill-event ping, armed daily_recap — MEMORY §86 (+ addendum: a commit body that quotes
  the literal skip-ci token gets silently skipped by CI — filed as a guard). Also corrected
  one ledger row (`feat/session-crossover-alerts` was mis-classified OWNER; the feature is
  actually live on main). Confirmed telegram-poll.yml live via 2 green scheduled runs.
  Then shipped **N6** (§87), closing the §83-review agent queue: `ml/cv.py`'s purge was
  entry-time-only (leaked label-end overlap across fold boundaries — fixed with a
  `horizon` param, auto-computed by `ml/labels.py::build_dataset` from each frame's own
  bar spacing × `max_bars`, no caller signature changes needed); `scenarios/audit.py`
  could report `clean=True` on zero checks (both call sites fixed + a hard
  `AuditResult.__post_init__` guard against recurrence); `overnight_research.py`'s
  parquet cache had no staleness check (now refuses fallback data older than 72h, using
  the file's own mtime as the stamp); `ingest/resample.py` could hand a partial trailing
  bucket downstream looking closed (now drops it unless source data reaches the bucket's
  end boundary); `memory/registry.py`'s broken-import path silently swallowed every
  exception (now logs loudly). 16 new tests, 772/772 total. Also wrote
  `docs/dsa_study_plan.md` at the owner's request — unrelated to the trading system, a
  study plan mapping a DSA infographic onto this codebase's real structures. Then
  shipped **N7** (§88), the last item in the queue: pulled the conf_70 (Δ+0.195R p=0.035,
  re-verify caveat — predates §75-§77), psych-1h (HARD NEGATIVE), and VAH-trap (REJECT)
  verdicts directly from their source branch commits into MEMORY; copied the #14 and
  #102 audit reports (which existed only on never-merged branches) into `docs/audits/`
  with provenance notes; verified the no-JS white-screen site fix is already live on
  `main` (`assets/css/style.css:517-525`) — nothing to ship there. Updated the ledger
  (section B 12→8, section C 16→21) and extended `delete_dead_branches.sh` with a
  pinned-SHA verification mode for the 21 section-C branches (dry-run: 123/123
  deletable, 0 skipped).
- **2026-07-05 (branch `claude/fable-five-codebase-review-9d61n5`):** ran the
  handoff gate (PR #137 → post-hoc **PASS**, `docs/audits/claude-weekly-trades-status-z8thda.md`)
  → Fable-5 full-codebase review via 5 independent subsystem reviewers → findings filed as
  MEMORY §83 + CROSSROADS X3/X4/N4–N6 → reconciled ~15 stale docs (README Netlify→Pages/Fly,
  telegram-setup runbook Render→Fly, `telegram-register.yml` Render→Fly [the only code-ish
  change], ledger retirement banner + REC-014, PHILOSOPHY checkboxes, MEMORY §34/§40
  supersession pointers, OPEN_SETUPS historical banner, BRAIN path cites, webmanifest copy).
  **No strategy, engine, paper-loop, or Telegram-behavior changes.** Auditor: the diff should
  be docs + `telegram-register.yml` + `site.webmanifest` only.
- **2026-07-05 (branch `claude/handoff-audit-dn37my`, PR #138):** parallel `/handoff-audit`
  session — discovered PR #137 open and absent from the baton (via `list_pull_requests`, not the
  baton), spawned an independent auditor (true merge-base located, every claim diff-verified,
  740/740 at head, `stop_to_tp1` confirmed default-off + research-only), verdict **PASS**
  (`docs/audits/pr-137.md`), marked #137 ready-for-review and squash-merged it, reconciled the
  baton. Docs-only; collided with the Fable-5 review session's own baton update (resolved here).
- **2026-07-03 (PR #137, merged, post-hoc PASS):** weekly trade status report (read-only, no
  diff) → owner proposed tightening TP/stop to 1.2R/0.5-ATR after a ~$1400 loss → first backtest
  wrongly ran on `1d` bars full-sample (tool default footgun) and looked profitable → caught the
  error, re-ran on the correct `1h` timeframe with 30% OOS holdout, which reversed the result
  (current +9.7R vs proposed -94.2R across BTC/ETH/SOL/AVAX/ADA/LINK) → **rejected the change,
  nothing deployed** (MEMORY §81). Follow-up: implemented + backtested the post-TP1 "stop-to-TP1"
  idea properly (default-off `stop_to_tp1` kwarg, isolated to the research CLI) → **also rejected**,
  loses on every one of the 6 coins (MEMORY §82). Independently audited PASS this session
  (`docs/audits/pr-137.md`) and merged.
- **2026-07-02 (streaming, no PR):** mobile hero fix, Render→Fly.io migration,
  `/api` proxy fix, `data/` privacy-leak fix, CROSSROADS board consolidation. See the audit report
  above for verified detail.
- **§74–§79 (2026-07-01→07-02, PRs #128–#136 + streaming):** §41 gap fully explained (VWAP rotation
  flip, PR #129) → v_vwap reverted to momentum (PR #130, §75) → management-geometry contamination
  audit + clean rerun → ride-3R shipped to paper (PR #131, §76) → website SEO/mobile sweep (PR
  #132) → redesign "The Journal" (PR #133) → security + engine review (PRs #134/#135) → forming-
  candle fix (PR #136, §77) → binance.us cross-venue data-honesty + Pine sync (§78, streaming) →
  DMN idea generator (§79, streaming). Each is detailed in `docs/MEMORY.md` under its own §.
- **PR #118 (website premium polish + SEO/AEO) + #117 (§41 pre-registration)** — both merged
  2026-06-27, both post-hoc audited PASS (`docs/audits/pr-118-posthoc.md`, `pr-117-posthoc.md`).
  Superseded visually by the later redesign (PR #133) but their SEO/forms work stands.

## NEXT chat

Everything below §73 (§41 gap, VWAP revert, management geometry, the website SEO sweep +
redesign, the security/engine review, the forming-candle fix, N1–N7, the tp-backtest
footgun/tighter-R:R re-test, **stop-to-TP1 (§82 — now a settled HARD-NEGATIVE, do NOT
propose it as "untested" again)**, the Fable-5 review §83, and the §86 Telegram audit)
is **DONE** — see `docs/MEMORY.md` §74–§88 for the full record. Do not re-derive any of
it. What's actually open now:

- **The agent-side queue is EMPTY.** N4-N7 (everything the §83 Fable-5 review put in the
  agent's court) are all shipped. There is no pre-assigned "next scope" for the next
  chat — read `docs/CROSSROADS.md` fresh, look for anything new the owner has said or
  any CI/PR activity needing attention, and pick up from there. Under the owner's
  standing streaming/proactive directives (`CLAUDE.md`), that can mean: watching for new
  owner asks, doing a fresh pass for small safe fixes, or simply confirming everything
  stays green if truly nothing new has come up.
- **Open risks:** CI on this session's final commit (N7) is unconfirmed as of this baton
  write (see "Verify live" above) — quick check first; X2 (Fly deploy) still blocks
  instant Telegram commands and the D1-backed `/levels /history /vectors` features; X5
  is owner-approved but not yet executed (the deletion script needs the owner to run
  it — agent containers can't push branch deletions).
- **Off-limits (standing, unchanged this session):** validated strategy defaults (§1),
  the live execution path, the 24h deadline (§70/§73), section-B ledger branches (owner
  call per-branch, not agent-delete — see the ledger for each one's recommendation).
- **Owner decisions — work the `docs/CROSSROADS.md` board, not this list.** X1 (live
  pre-live gate, 8 latent bugs, money path — needs sign-off), X2 (now 6 steps — see above),
  X3 (transparency posture), X4 (§83 core-engine fixes), and X5 (branch cleanup — APPROVED,
  just needs the owner to run the script) are OPEN. Move a row the same turn a decision is
  made — that discipline is the whole point of the board.
- **N2 (TradingView indicator suite) is now fully DONE** (both phases, §78 + §90) —
  don't re-open. Keep the Pine vwap sign = momentum (§75 parity is test-pinned on the
  Python side).
- **STILL PENDING — D1 provisioning + Telegram webhook registration.** Neither has changed
  since the last check: `cloudflare/trade-bot-cron/wrangler.toml:41` still has
  `database_id = "REPLACE_WITH_DATABASE_ID"` (D1 never provisioned — activates §67
  `/levels /history /vectors`); the Telegram webhook registration status is unverified from
  this container. Both depend on the API being deployed (now **Fly.io**, not Render — see
  X2) before they can be exercised end-to-end. Runbooks: `docs/HOSTING.md`,
  `docs/runbooks/telegram-setup.md`.
- **WATCH — the post-07-01 era-3 forward record (W1, CROSSROADS).** After **50+ resolved
  1h trades** since 2026-07-01, `journal-score` the momentum+ride-3R book (§75/§76/§77 — the
  first time the live bot has run the exact validated config) as its own era; never pool
  across the pre-07-01 rotation era when judging it.
- **Open risks still live (unchanged, not re-verified this session):** §C 1h `_cts` book
  (§53) runs on an owner-external, here-unreproduced +0.1152R claim — revert if forward
  net-negative after ≥30 trades. §A 5m long-only (§52) is a paper hypothesis, net-negative
  every prior look — revert if it stays so. §B universe (PR #58) is opt-in/off the validated
  path, not the owner's spec — reconcile before wiring in. Loop agent (§64) calibration is
  still empty (0 graded forward cycles) — don't trust its proposals yet. PR #78/D1 is PARKED
  (see above). §42 maker-fee assumption still unsettled — blocks Tier-2 leverage graduation.
- **Off-limits (standing, unchanged):** validated strategy defaults (§1) and `FEE_PCT`;
  tightening R:R below §1's 3.0R/1.5-ATR (now settled TWICE — §10 and §81 — do not re-test without
  a genuinely new angle, e.g. per-symbol geometry); post-TP1 `stop_to_tp1` (§82, settled negative —
  the kwarg exists as a default-off research knob, never arm it without a materially different
  angle); `--trailing-atr` OFF (§72 settled hard negative — do not re-test without new rationale);
  the 24h deadline — settled KEEP (§70/§73, do not re-open without ≥30 forward trades under
  the window, per `docs/decisions/deadline_bars.md`); the live execution path
  (`bracket.py`/`resolver.py`); the trading/levels core (`build_levels()`,
  `pvsra_vector_candles()`, `paper_scan()`, the backtest harness) — the memory/intelligence
  layers READ, never mutate. `data/journal.json` is bot-owned — no manual journal refreshes.
  `data/shadow/` (gitignored), `data/alert_inbox/` (host-owned). Keep PR #20 killzone flag
  UNARMED until 1h-validated; keep maker retrace, `min_pct` 0.5. No public live-edge/returns
  claims.

## Baton history
- … (prior entries in git) …
- 2026-06-15: PR #21 — gated admin/investor dashboard (local-only verification). Merged.
- 2026-06-15: PR #23 — cycle-aware OOS backtest; `min_pct 0.6` refuted → keep 0.5. Merged.
- 2026-06-15: PR #24 — execution head-to-head; maker retrace wins; market a dead end (§42). Merged.
- 2026-06-16: PR #31 — VWAP momentum→ROTATION flip (LIVE, unvalidated, §44). Merged from DRAFT.
- 2026-06-19: PR #35 — RESEARCH+REPORT chat (cluster analyzer §45 + leverage/BE study §46 +
  forward-test framework + hosted report). Merged.
- 2026-06-19: PR #36 — Tier-2 maker ENTRY fill feasibility (read-only, §47, 86.6% PASS). Merged.
- 2026-06-19: PR #39 — reverted live bot to §1 config after diagnosing the net-negative book (§48). Merged.
- 2026-06-21: PR #47 — EXECUTION chat: armed the pay-yourself breakeven exit on the hourly 1h
  book (§49); premise was config-only but needed CLI wiring. Merged.
- 2026-06-21: PR #48 — flattened 40 stale 2h/4h zombie positions to a non-scoring status (§50);
  idempotent script, journal byte-stable. Merged.
- 2026-06-22: PR #49 — exit-geometry 5m study: no geometry rescues 5m, quarter-Kelly ≤0 (§51). Merged.
- 2026-06-22: PR #50 — Experiment §A: 5m long-only book + long_only/killzone_gate flags (§52);
  long-only is a forward-test hypothesis, killzone gate ships unarmed. Merged.
- 2026-06-22: PR #51 — docs/baton refresh capturing §49–§52. Merged.
- 2026-06-22: PR #55 — Experiment §C: clean_trend_stack 1h + per-book dedup (§53); UNVERIFIED
  external +0.1152R claim, separately tagged `_cts`. Merged (user-directed `/loop` batch).
- 2026-06-22: PR #56 — per-book Telegram summary + best/worst + today PnL + `:35` read-only
  status workflow (§54). Merged (batch).
- 2026-06-22: PR #57 — deadline/stale alert line + de-flaked a pre-existing flaky auth test (§55).
  Merged (batch).
- 2026-06-22: PR #58 — §B dynamic volume universe: opt-in, OFF the validated path, net-new (§56).
  Merged (batch).
- 2026-06-22: PR (closeout) — docs/baton for the Telegram-suite + §B batch. Owner
  authorized self-merge of the whole batch; no pending merge gate → next chat audits POST-HOC.
  Live books to watch: §C `_cts`, §A `_lo`, breakeven arm, `:35` status ping. Reconcile §B spec.
- 2026-06-23: PR #78 — Cloudflare D1 persistence (TR Level Intelligence). **CLOSED + PARKED** by
  owner (D1 unverified, needs provisioning); code stays on `claude/tr-level-intelligence-qc4i2p`.
- 2026-06-23: PR #79 — L7 self-improving loop agent (§64): grades its own per-book drift calls.
  **MERGED by owner.** Read-only, off the trading path, not yet on a cadence.
- 2026-06-23: PR (`/closeout`) — docs/baton for the loop-agent chat. Work (#79) already
  MERGED → next chat audits #79 POST-HOC. NEXT priority: provision D1 + reopen #78.
- 2026-06-23: PR #82 — cancel-to-close DISPLAY fix (§65): audited the "cancels at 0.00R" claim,
  found it was a display bug not a P&L bug (cancelled = unfilled limit, no R, already excluded);
  stopped counting cancels as closed trades. **MERGED by owner.** Refused the fabricating backfill.
- 2026-06-23: PR (this, `/closeout`) — docs/baton for the cancel-to-close chat. Work (#82) already
  MERGED → next chat audits #82 POST-HOC. NEXT priority UNCHANGED: provision D1 + reopen #78.
  New open risk: 1 hit/miss row with `outcome_r=None`.
- 2026-06-23: PR #84 — per-trade Telegram alerts. **MERGED by owner OUTSIDE the relay gate**; audited
  POST-HOC this session → PASS (`docs/audits/feat-trade-event-alerts.md`).
- 2026-06-23: PR #85 — `/handoff-audit` + **§66**: the §65 null-R row was a `reach_below` CALL (no R),
  not a resolver bug; display-only fix, header now 588/588. **MERGED by owner.**
- 2026-06-23: PR #78 — TR Level Intelligence (D1) **REOPENED, synced to main, §64→§67 renumbered, and
  MERGED on the owner's explicit "merge them"** (CI green, safe no-op until provisioned).
- 2026-06-23: commit `c43b8a7` — CI push-retry in `paper-trade.yml`, **direct to `main` (owner-approved,
  no branch)**.
- 2026-06-23: PR (closeout) — docs/baton + full-suite test report (`496 passed / 0 failed`,
  `docs/audits/session-2026-06-23-test-report.md`). NEXT: owner provisions D1 + registers the Telegram
  webhook; both are test-covered in code, unverified only on the live transport.
- 2026-06-24: PR #87 (runbook), **#89 self-register webhook** (`f6502d2`), **#91 brand upgrade**
  (`8876440`, superseded #90) — all MERGED. PR #88 (`max_bars` research, §68) OPEN for owner-merge:
  shorter exits HURT, 36–48h suggestive-not-significant, keep max_bars=24. This PR (closeout) on
  `docs/closeout-brand-webhook-research`: MEMORY §68 + baton. NEXT: live bring-up (D1 + webhook) + verify.
- 2026-06-24: **PR #96** (`06bf9af`, deadline `_DEADLINE_BARS` 72→24, 1h resolve 3.0d→1.0d) + **PR #98**
  (`4adb1b8`, /summary voice wording) — both **MERGED by owner**, CI-green, 503 tests → next chat audits
  POST-HOC. **PR #97** (`docs/deadline-decision-log`, decision log + MEMORY §70 + this baton) is the
  OPEN closeout PR — AWAITING_AUDIT. NEXT: WATCH the 24h deadline forward (50+ trades), then resume the
  still-pending live bring-up (D1 + webhook).
- 2026-06-25: **PR #102** (`feat/binary-event-filter`, binary-event entries-gate, MEMORY §71, 511 tests
  green) — this chat's OPEN closeout PR, AWAITING_AUDIT. Also marked ready-for-review (owner-directed
  cleanup) two GREEN prior-chat drafts whose fixes are verified absent from `main`: **PR #101**
  (`fix/journal-fill-atomic`) + **PR #99** (`fix/summary-pending-reconcile`) — left OPEN for owner merge,
  not merged/closed. NEXT: audit & merge #102.
- 2026-06-25: **PR #103** (`claude/trailing-stop-backtest-jz0aho`, trailing-stop head-to-head, RESEARCH
  ONLY, MEMORY §72, 520 tests green) — **MERGED by owner**; verdict KEEP `--trailing-atr` OFF (settled
  hard negative). **PR #101** (`fix/journal-fill-atomic`) also MERGED into `main` this session; **PR #99**
  still OPEN for owner merge. This PR (closeout) is docs-only (MEMORY §72 + baton) → next chat audits
  #103/#102 POST-HOC. NEXT: post-hoc audit + reconcile #99; optional `be_after_tp1` study.
- 2026-06-27: **PR #118** (`feat/website-premium-polish`, website premium polish + SEO/AEO + Formspree +
  lab data refresh, marketing-only, 582 tests green) and **PR #117** (`feat/section41-gap-prereg`, §41-gap
  pre-registration, docs-only) — **BOTH MERGED on the owner's explicit "Close and merge all PRs"** at
  closeout. Next chat audits #118/#117 POST-HOC. NEXT: finish the website SEO sweep + remaining
  visual-polish pages (marketing-only).
- 2026-07-01→07-02: **PRs #127–#136** (all confirmed `merged: true`) + streaming direct-to-`main`
  commits — post-hoc audits (#118/#117) + repo-state audit (#127); §41 gap fully explained (§74, #129);
  v_vwap reverted to momentum (§75, #130); management-geometry contamination audit + clean rerun →
  ride-3R shipped to paper (§76, #131); website SEO/mobile sweep (#132) + redesign "The Journal" (#133);
  security + engine correctness review (§77 addendum, #134/#135); forming-candle fix (§77, #136);
  binance.us cross-venue data-honesty + Pine sync (§78, streaming, `/code-review`'d); DMN idea generator
  (§79, streaming); `docs/BRAIN.md` + `docs/CROSSROADS.md` stood up as the live decision surface. Baton
  was NOT reconciled across this streak (workflow shifted to streaming, nothing forced it) — see next entry.
- 2026-07-02: mobile hero/nav overlap fixed; **backend host moved Render → Fly.io** (owner: "not using
  Render") — `Dockerfile`/`fly.toml`/`fly-deploy.yml` added, `render.yaml` retired; found + fixed a
  **real privacy leak** (raw `data/journal.json`, incl. open-position entry/stop/target, was publicly
  downloadable via Cloudflare Pages serving the repo root) + the `/api/*` proxy (was Netlify-only, dead
  on Pages) — both via Pages Functions (§80). `/handoff-audit` run: no open PR existed (streaming
  workflow) so the gate covered this session's direct-to-`main` commit range instead — **independent
  audit PASS** (`docs/audits/streaming-audit-2026-07-02-fly-migration.md`, 737/737 tests, no scope creep,
  every claim diff-verified). Baton fully reconciled this turn (was stale since 2026-06-27). NEXT:
  X1/X2 on `docs/CROSSROADS.md` (Fly deploy is the actionable blocker), TV indicator phases (b)/(c).
- 2026-07-03: PR #137 (`claude/weekly-trades-status-z8thda`) — weekly status report (read-only) +
  a proposed TP/stop tighten (1.2R/0.5-ATR) that was backtested, found to be a `1d`-vs-`1h` +
  full-sample measurement error, corrected (1h, 30% OOS), and **rejected** (+9.7R baseline vs
  -94.2R proposed across 6 coins, §81) — plus the post-TP1 stop-to-TP1 idea, implemented as a
  default-off research kwarg and **also rejected** (§82). Nothing deployed. Left AWAITING_AUDIT
  (draft PR) — see next entry.
- 2026-07-05: `/handoff-audit` on `claude/handoff-audit-dn37my` — PR #137 was **not on the baton at
  all** (opened 2026-07-03, but `main`'s `docs/HANDOFF.md` still read "streaming, no open PR" since
  its own baton update never reached `main` pre-merge); found via `list_pull_requests(state=open)`,
  not the baton (process note above). Independently audited — **PASS**
  (`docs/audits/pr-137.md`: true diff isolated via the real merge-base, `stop_to_tp1` confirmed
  byte-identical when omitted and confirmed isolated to the research CLI, non-trivial new tests,
  740/740 green at head, no scope creep) — merged (was draft; marked ready-for-review then
  squash-merged). Baton reconciled. NEXT: back to the CROSSROADS X1/X2 board (Fly deploy is the
  actionable blocker) — both R:R-tighten and stop-to-tp1 are now closed lines of inquiry.
- 2026-07-06: continuation of the `claude/n4-ps42u7` chat, streaming — merged PR #140 (N4) +
  PR #138; built the Branch Execution Ledger + got owner approval on X5 (packaged as
  `scripts/delete_dead_branches.sh`, owner-run); shipped N5 (deploy/CI hardening, §85); ran
  a full Telegram audit (§86) — found slash commands dead (no webhook) and the scheduled
  digest suite unable to be enabled at all, fixed both (no-server polling command answerer +
  flag-forwarding), added a fill-event ping, armed `daily_recap` — telegram-poll.yml's
  first 2 scheduled runs confirmed green same session; shipped N6 (research-honesty
  fixes, §87: CV label-end purge leak, audit.py clean-on-zero-checks, unstaled overnight
  cache, trailing-partial resample bucket, silent registry-import swallow — 16 new tests);
  shipped N7 (ledger harvests, §88: conf_70/psych-1h/VAH-trap verdicts into MEMORY,
  #14/#102 audit reports landed, no-JS site fix confirmed already-live, delete script
  extended to 123 branches) — closes the entire §83-review agent queue (N4-N7 done).
  All direct-to-`main`, no PR. Suite 772/772. NEXT: agent queue is empty; read
  CROSSROADS fresh for anything new, or confirm CI green on this session's final commit.
