# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** finish the unit → open ONE PR → merge →
  only then start the next. Honor "owner merges" — never self-merge unless the owner explicitly
  authorizes it.
- **This chat = the DEADLINE + DECISION-LOG + /summary chat** (multi-task, owner-directed). Shipped:
  1. **1h resolve deadline 3.0d→1.0d — PR #96 (`06bf9af`), MERGED by owner.** `_DEADLINE_BARS` 72→24 in
     `kudbee_quant/paper/paper.py` (one constant). 1h trades now force-resolve at market after 24h,
     aligning the live window with the validated `max_bars=24`. CI green, 503 tests. MEMORY §70.
  2. **`/summary` voice wording — PR #98 (`4adb1b8`), MERGED by owner.** Aligned `cmd_summary` phrasing to
     the owner's spec (all-green branches + "on the crypto book" tail). It was ALREADY paragraph/voice
     format from a prior chat — this was wording-only, display-only. 503 tests.
  3. **Deadline decision log — PR #97 (`docs/deadline-decision-log`), OPEN/green, owner to merge.**
     `docs/decisions/deadline_bars.md`: current setting, §68 tension, watch signal, hard negative. This
     is the `/closeout` PR (now also carries MEMORY §70 + this baton).
- **NOTHING new is live beyond the deadline constant.** #96 changed ONE live-path constant (the 1h resolve
  window); #98 is display-only; #97 is docs. No levels/trading-core change; `data/journal.json` bot-owned,
  not hand-edited.
- **Audit status:** `AWAITING_AUDIT` — PR #97 is this chat's open PR (the merge gate is the next chat's
  audit). #96 and #98 were owner-merged CI-green this session → next chat audits them POST-HOC.

## What this chat did (for the auditor to verify against the diff)

- **PR #96 (`06bf9af`) — deadline (MERGED).** CONFIRM: net diff vs `main` = ONE line in
  `kudbee_quant/paper/paper.py` (`_DEADLINE_BARS` 72→24) + its comment; `cli.py`/`.github/workflows/
  paper-trade.yml` byte-identical to `main` (a `--deadline-days` CLI route was built then FULLY reverted).
  `_bars_to_days("1h",24)`=1.0d. `validated_defaults`/`FEE_PCT`/`resolver.py`/`bracket.py` UNTOUCHED.
  503 tests.
- **PR #98 (`4adb1b8`) — /summary wording (MERGED).** CONFIRM: only `kudbee_quant/telegram_commands.py`
  `cmd_summary` changed (~8 lines): all-green branch strings + tail "on the crypto book"; a flat fallback
  kept for the breakeven edge so it never falsely claims "every one in profit". Three-paragraph structure
  unchanged. Display-only — no R math, no journal write. No test asserted the old wording. 503 tests.
- **PR #97 (this, OPEN) — docs + closeout.** Adds `docs/decisions/deadline_bars.md`, MEMORY §70, and this
  baton. No code change; net diff vs `main` is docs-only.

## NEXT chat

- **🟢 NEXT-CHAT SCOPE (owner-chosen) — WATCH THE 24h DEADLINE FORWARD.** The 1h resolve window is now
  24h (PR #96, §70) and is **LIVE + UNVERIFIED**. After **50+ forward 1h trades** under the new window,
  run `journal-score` on `_cts`/core and compare expectancy to the pre-#96 baseline: net > 0R (after fees)
  → keep; below baseline → revisit per `docs/decisions/deadline_bars.md`. **Do NOT revert without data,
  and do NOT re-open the deadline as a backtest candidate without ≥30 forward trades under 24h (hard
  negative, §70).** Advisory slug hint: `claude/watch-deadline-forward`.
- **FIRST: run `/handoff-audit` → merge PR #97** (this closeout PR) on a PASS, so the decision log + §70 land.
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
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; **the 24h deadline — do NOT revert
  `_DEADLINE_BARS` or re-open it as a backtest candidate without ≥30 forward trades under the new window
  (§70 hard negative)**; the live execution path
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
