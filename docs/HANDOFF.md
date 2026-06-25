# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** finish the unit → open ONE PR → merge →
  only then start the next. Honor "owner merges" — never self-merge unless the owner explicitly
  authorizes it.
- **This chat = the TRAILING-STOP-BACKTEST chat (RESEARCH ONLY).** Shipped **PR #103**
  (`claude/trailing-stop-backtest-jz0aho`, green, 520 tests, ruff clean) — **already MERGED by the owner**:
  a read-only backtest of the EXISTING chandelier trail vs the live bank-half/ride-to-3R rule. Files:
  `research/trailing_sweep.py` + `research/trailing_sweep_results.md` + 2 CSVs + `tests/test_trailing_sweep.py`.
  Imports `bracket_backtest` + the shared `resolve_bracket`; reimplements nothing. **No live flag, workflow,
  paper.py, resolver, or bracket.py logic touched.** MEMORY **§72**.
- **VERDICT (settled HARD NEGATIVE, §72): keep `--trailing-atr` OFF.** No trail multiple clears the
  bootstrap significance gate (best `boot_p` 0.293 @ atr=1.0). The only net-positive variant (atr=1.0)
  wins purely by collapsing drawdown while **cutting 82% of former +3R runners short** (−480R on that
  cohort) — it abandons the asymmetric edge. Do NOT re-test trailing without a genuinely new rationale.
- **NOTHING new is live from this chat.** Pure research; trading core byte-identical. `data/journal.json`
  bot-owned, not hand-edited (the only journal change this session was the routine bot sync via `main`).
- **Audit status:** `AWAITING_AUDIT` — the research **PR #103 is already MERGED** (post-hoc audit due,
  like #84/#82). **This chat's OPEN closeout PR is docs-only** (MEMORY §72 + this baton).

## What this chat did (for the auditor to verify against the diff)

- **PR #103 (this chat, MERGED) — trailing-stop research.** Audit-confirmed (file:line) the trail is
  already implemented + OFF in live: `paper.py:69/:210`, `journal.py:70-73/:231-236`,
  `bracket.py:61/:170/:264`, `paper-trade.yml:75-77/:90`. **STEP-0 gate verified real**
  (`resolver.py:137-165`): trails at `trailing_atr*atr_at_entry` behind the favorable extreme, ratchets
  monotonically, never loosens, no same-bar look-ahead. To diff-confirm: (1) the new files are all under
  `research/` + `tests/` — NO change to the trading/levels core, the resolver, bracket logic, paper.py,
  or the workflow. (2) `tests/test_trailing_sweep.py` includes the regression lock that paired-baseline
  reproduces `bracket_backtest` baseline EXACTLY, plus the monotonic-ratchet + `trailing_atr=None` no-op
  guards. 520 tests green.
- **Honest caveats (in §72 + the results MD):** (a) my §41 ride-3R reproduction (−0.015R/n=3540) did NOT
  match §41's +0.096R/n=8124 — UNRECONCILED; only the relative head-to-head is verified. (b) Secondary,
  OUT-OF-SCOPE: the live bank-half/BE rule was the WORST variant here (−0.055R) — a `be_after_tp1`
  question for a future chat, NOT acted on.
- **PR #101 (`fix/journal-fill-atomic`) MERGED this session** (arrived via `main` fast-forward:
  journal.py + notify.py + tests). **PR #99 (`fix/summary-pending-reconcile`) still OPEN** on origin —
  owner to merge; audit POST-HOC if merged outside the gate.

## NEXT chat

- **🟢 NEXT-CHAT SCOPE — POST-HOC AUDIT the merged work, then reconcile the open fix.** Run
  `/handoff-audit`: (1) post-hoc audit **PR #103** (trailing research) against the checklist above and
  **PR #102** (binary-event filter, merged before this chat) if not yet recorded; (2) confirm **PR #101**
  is correctly in `main`; (3) **PR #99** (`fix/summary-pending-reconcile`) still needs the owner's merge —
  verify it's still absent from `main`, then leave for the owner. Advisory slug hint: `claude/handoff-audit`.
- **CANDIDATE next research (owner's call) — the `be_after_tp1` management question (§72 secondary).**
  The live bank-half/BE rule was net-negative in this OOS population. Worth a read-only study of whether
  BE-after-TP1 is capping the edge vs plain ride-3R — research only, no live change. Advisory slug:
  `claude/be-management-study`.
- **CARRY-FORWARD (was the prior scope) — WATCH THE 24h DEADLINE FORWARD.** The 1h resolve window is now
  24h (PR #96, §70), **LIVE + UNVERIFIED**. After **50+ forward 1h trades**, run `journal-score` on
  `_cts`/core vs the pre-#96 baseline: net > 0R → keep; below → revisit per
  `docs/decisions/deadline_bars.md`. **Do NOT revert without data; do NOT re-open the deadline as a
  backtest candidate without ≥30 forward trades under 24h (hard negative, §70).**
- **STILL PENDING (standing priority, NOT done this chat) — LIVE BRING-UP (D1 + webhook), then VERIFY.**
  Two owner-side actions remain unblocked; the next chat verifies the live transport once they're done.
  Advisory slug hint: `claude/verify-live-bringup`.
  - **Provision Cloudflare D1** (activates §67 `/levels` `/history` `/vectors`): (a)
    `wrangler d1 create kudbee-tr-levels`; (b) apply `cloudflare/trade-bot-cron/migrations/0001_tr_levels.sql`;
    (c) paste `database_id` into `wrangler.toml` + Render `D1_DATABASE_ID`, set `CF_ACCOUNT_ID` +
    `CF_API_TOKEN` in Render; (d) paper-scan → forward-verify the 3 commands on real D1.
  - **Register the Telegram webhook** — easiest path now: hit the NEW self-register endpoint in a browser,
    `https://<RENDER>/api/telegram/register-webhook?token=<KUDBEE_API_TOKEN>` (PR #89). Or the manual
    `setWebhook` curl in `docs/runbooks/telegram-setup.md` (+ `setMyCommands` for the menu). Then exercise
    `/help /status /score /positions /scan` (+ rate-limit) and `/trade`→`/yes`/`/cancel`. The
    `TELEGRAM_WEBHOOK_SECRET` must match Render's value (the #1 failure mode). Routing is test-covered
    (`test_telegram_commands.py`); only the live transport is unverified.
- **PR #88** (`max_bars` research, §68) is no longer open — landed; keeps max_bars=24, nothing deployed.
- **🚩 STUCK GOAL (needs owner action): push commit `1322efa` / `/goal clear`.** A `/goal` set this
  session asked to push the owner's local commit `1322efa` (branch `fix/webhook-self-register`). That
  commit lives only on the owner's machine (`/home/claude/qbot`), was never pushed, and is unreachable
  from the ephemeral container — so the literal condition can't be met here. Its INTENT is already
  shipped (the self-register endpoint, PR #89, is on `main`). Resolve by `/goal clear` (recommended —
  work is done) or by pushing `1322efa` from the owner's machine.
- **OPTIONAL follow-up (loop agent, §64):** wire `kudbee loop-agent` into a half-hourly Action (like
  the `:35` status ping) so the L7 loop runs on a cadence — its reliability calibration is empty
  until many cycles accrue forward. Read-only; safe to schedule.
- **WATCH the live changes:**
  - **§C 1h `_cts` book (§53):** after ≥30 forward `_cts` trades, `journal-score` filtered to those
    setups. Net expectancy > 0R net of fees → keep; else → **revert the §C workflow step.** The
    +0.1152R claim is UNVERIFIED here.
  - **§A 5m long-only `_lo` book (§52):** same trigger; 5m has been net-negative every prior look.
  - **Breakeven arm (§49):** confirm new 1h opens carry a non-null `tp1`; watch whether stop→BE
    lifts the 1h book's expectancy forward.
  - **`:35` status workflow (§54):** confirm it actually fires a Telegram ping on the half-hour
    (needs `TELEGRAM_*` secrets set in the repo).
- **STILL OPEN from §48:** the reverted §1 book (top-10/1h) — does it turn positive once the
  alt+5m drag is gone, or is there a real backtest→live gap (regime/decay)? Candidate
  edge-builder: the **killzone/hour gate for 1h** (the flag now exists, UNARMED) to cut the
  18h/06h toxic clusters — forward-validate before arming.
- **Tier-2 leverage (still queued, §47):** (a) re-rate the candidate net with **maker-entry +
  taker-exit** (asymmetric friction; the study's both-maker under-charges crypto); (b)
  `BINANCE_TESTNET` micro-stake. Only then can `lock+0.1R/≤10x/maker` graduate (micro-stake only).
- **Open risks / watch-items (still live):**
  - **🚩 24h DEADLINE IS LIVE + UNVERIFIED (§70, PR #96)** — `_DEADLINE_BARS=24` shortened the 1h resolve
    window 3.0d→1.0d. Forward expectancy under the shorter window is unmeasured. Watch `_cts`/core after
    50+ forward trades vs the pre-#96 baseline; revert ONLY on data (and never re-backtest the deadline
    without ≥30 forward 24h trades). See `docs/decisions/deadline_bars.md`.
  - **🚩 §C 1h `_cts` book is LIVE on an UNVERIFIED claim (§53, PR #55)** — owner's external
    +0.1152R/n=804, not reproduced here; separately tagged, revert if forward net-negative.
  - **🚩 VWAP ROTATION FLIP IS LIVE & UNVALIDATED (§44, PR #31)** — keep observing; be ready to revert.
  - **§A 5m long-only is a paper HYPOTHESIS** — separately tagged, but it IS logging a live
    (paper) book; revert if net-negative.
  - **§B universe (PR #58) is NET-NEW, not the owner's spec** — opt-in/off the validated path;
    reconcile before any thought of wiring it in.
  - **§42 maker fee is an ASSUMPTION** (0.0002/side) — Tier-2 must settle before leverage graduates.
  - **Dashboard (PR #21) UNVERIFIED in production.**
  - **Loop agent (§64, PR #79) calibration is EMPTY** — it has run 0 forward cycles, so its
    per-signal reliability means nothing yet; do not trust/act on its proposals until it accrues
    graded cycles (it only persists state when `loop-agent` is actually invoked).
  - **PR #78 (D1) is PARKED, not abandoned** — D1 is UNVERIFIED end-to-end; reopening requires
    real CF provisioning + a MEMORY-section renumber (now collides with BOTH §64 loop agent and §65).
  - **✅ NULL-R RESOLVED ROW — FIXED THIS CHAT (§66, PR #85).** Located: `7e0d2e94`, a `reach_below`
    directional CALL (no bracket, no R) — the only non-bracket row in the journal; `outcome_r=None`
    is correct for it (not a resolver bug, not a missing-R trade). Display-only fix: the closed-trades
    view + `journal-check` summary now require `kind=='bracket'`. Header is now a consistent 588/588.
    No journal edit (a backfill would have fabricated P&L on a position that never opened).
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; **`--trailing-atr` is now a SETTLED
  HARD NEGATIVE (§72) — keep it OFF; do NOT re-test trailing without a genuinely new rationale**; **the
  24h deadline — do NOT revert `_DEADLINE_BARS` or re-open it as a backtest candidate without ≥30 forward
  trades under the new window (§70 hard negative)**; the live execution path
  (`bracket.py`/`resolver.py`); **the trading/levels core — `build_levels()`,
  `pvsra_vector_candles()`, `paper_scan()` trading logic, the backtest harness** (left
  byte-identical this session; the memory/intelligence layers READ, never mutate).
  `data/journal.json` is bot-owned — the ONLY sanctioned session
  edit was the idempotent flatten script (#48); no manual journal refreshes. `data/shadow/`
  (gitignored), `data/alert_inbox/` (host-owned). Keep PR #20 flags OFF on the validated book;
  hold the parsimony line; paper-scan stays `dry_run=True` for the dashboard runner; killzone
  gate stays UNARMED until 1h-validated; keep maker retrace, `min_pct` 0.5. No public
  live-edge / returns claims.

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
