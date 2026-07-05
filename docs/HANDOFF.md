# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`. Branch `claude/weekly-trades-status-z8thda`, PR **AWAITING_AUDIT**
  (see below) — this is a normal one-PR closeout, not streaming (the diff is docs-only but the
  session's substance was a rejected strategy-change proposal, worth a reviewed PR per the "money
  path gets a PR" rule even though nothing code-level changed).
- **⚙️ WORKFLOW (2026-07-02, owner-set):** STREAMING & actionable — commit low-risk/docs/verified
  work directly to `main`; open a PR only when it earns one (large/risky, the money path, a
  preview-worthy visual, or a requested review); merge-on-green when the owner has authorized it.
  See `CLAUDE.md` + `docs/BRAIN.md`. Self-updating memory: repeated instruction / new convention /
  twice-made mistake → save it as you go.
- **🧭 THE LIVE DECISION SURFACE IS `docs/CROSSROADS.md`, NOT THIS SECTION.** Every open fork
  (owner-decisions, do-next, watch) lives there with evidence + a recommended default, and gets
  moved the same turn a decision is made. **Read it, not a narrative recap here.** Current open
  owner rows: **X0** (why the app layer wasn't wired — historical record), **X1** (live pre-live
  gate — 8 latent bugs, money path, needs sign-off), **X2** (the consolidated 5-step bring-up
  checklist: DNS→Cloudflare, Pages custom domain incl. `www`, **deploy the API to Fly.io**,
  Email Routing, Worker `TRIGGER_SECRET`).
- **✅ MOST RECENT WORK (2026-07-03):** owner asked for a weekly trade status (given in plain
  English: +14.8R / 64% win rate this week vs -130.3R all-time on the old book) then proposed
  tightening the exit to 1.2R target / 0.5-ATR stop after a ~$1400 historical loss. First backtest
  pass looked great but was **wrong** — `tp-backtest` defaults to `--interval 1d` (not the bot's
  `1h`) and full-sample (no OOS holdout), which silently flatters results. Re-run correctly (1h,
  30% OOS) reversed the verdict: current defaults net **+9.7R**, the tighter stop nets **-94.2R**,
  across the same 6 coins — reconfirming the already-settled §10 finding. **No code, Telegram, or
  workflow changes were made.** MEMORY **§81**. Full detail in the PR below.
- **Audit status:** `AWAITING_AUDIT` (this PR). Prior: `PASS` (2026-07-02, post-hoc on streaming
  commits). Prior formal checkpoint before that: PR #127 repo-state audit + post-hoc #118/#117
  (2026-07-01), MEMORY §73. Full narrative: `docs/MEMORY.md` §74–§81.
- **⚠️ PROCESS NOTE:** this baton had gone stale (last reconciled 2026-06-27) while the workflow ran
  streaming — nothing forces a baton update the way a PR-per-chat merge gate used to. Reconciled
  2026-07-02. If a future chat notices the baton lagging `docs/MEMORY.md`'s highest `§` number again,
  that's the same gap recurring — update it as part of `/handoff-audit`, not just `/closeout`.

## What recent chats did (for the auditor to verify against the diff / MEMORY)

- **This session (2026-07-03, PR AWAITING_AUDIT):** weekly trade status report (read-only, no
  diff) → owner proposed tightening TP/stop to 1.2R/0.5-ATR after a ~$1400 loss → first backtest
  wrongly ran on `1d` bars full-sample (tool default footgun) and looked profitable → caught the
  error, re-ran on the correct `1h` timeframe with 30% OOS holdout, which reversed the result
  (current +9.7R vs proposed -94.2R across BTC/ETH/SOL/AVAX/ADA/LINK) → **rejected the change,
  nothing deployed**. Only diff: MEMORY §81 (this finding + the `tp-backtest` footgun warning) and
  this baton. Auditor: verify §81's numbers are actually reproducible with
  `tp-backtest <SYM> --interval 1h --target-r 1.2 --stop-atr 0.5 --oos-frac 0.3` (and the `3.0`/`1.5`
  baseline variant) — the whole point of this PR is that the number is easy to get wrong silently.
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
redesign, the security/engine review, the forming-candle fix, N1–N3, the tp-backtest
footgun/tighter-R:R re-test) is **DONE** — see `docs/MEMORY.md` §74–§81 for the full record. Do
not re-derive any of it. What's actually open now:

- **This chat's suggested next priority (not urgent, owner hasn't confirmed):** backtest the
  post-TP1 "stop-to-TP1" idea properly from the start (1h, OOS) — after TP1 fills, move the
  runner's stop to the TP1 price instead of breakeven. Genuinely untested, does not contradict
  §10/§81 (different mechanism: post-fill stop placement, not entry R:R geometry). Low priority
  vs. the CROSSROADS board below if the owner doesn't ask for it explicitly.
- **Owner decisions — work the `docs/CROSSROADS.md` board, not this list.** X1 (live
  pre-live gate, 8 latent bugs, money path — needs sign-off) and X2 (the consolidated
  5-step bring-up checklist: DNS→Cloudflare, Pages custom domain incl. `www`, **deploy the
  API to Fly.io**, Email Routing, Worker `TRIGGER_SECRET`) are both OPEN, owner-side. Move
  a row the same turn a decision is made — that discipline is the whole point of the board.
- **BACKLOG — TradingView indicator suite, phases (b)/(c).** Phase (a) (sync the Pine
  indicator to the current engine) shipped §78/N2. Still queued: (b) split standalone
  indicators (PVSRA candles, session/killzone boxes, M-levels/pivots, confluence meter);
  (c) publish-quality polish (inputs, tooltips, alerts). Keep the Pine vwap sign = momentum
  (§75 parity is test-pinned on the Python side).
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
  a genuinely new angle, e.g. per-symbol geometry); `--trailing-atr` OFF (§72 settled hard negative
  — do not re-test without new rationale);
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
- 2026-07-03: PR (this, `/closeout`) on `claude/weekly-trades-status-z8thda` — weekly status report
  (read-only) + a proposed TP/stop tighten (1.2R/0.5-ATR) that was backtested, found to be a
  `1d`-vs-`1h` + full-sample measurement error, corrected (1h, 30% OOS), and **rejected**
  (+9.7R baseline vs -94.2R proposed across 6 coins) — reconfirms §10. **Nothing deployed.**
  Docs-only diff: MEMORY §81 + this baton. AWAITING_AUDIT. NEXT: audit this PR, then either the
  post-TP1 stop-to-TP1 idea (if owner wants it) or back to the CROSSROADS X1/X2 board.
