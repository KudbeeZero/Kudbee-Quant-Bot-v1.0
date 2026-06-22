# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** finish the unit → open ONE PR → merge →
  only then start the next. **This chat ran a user-directed `/loop` BATCH** — the owner asked to
  run three queued items end-to-end ("create a PR for each one, close it, do the same thing, let
  me know at the end"). Each was its own PR, CI-green, merged before the next — serial, but the
  owner explicitly authorized me to **merge them myself** (a deliberate, logged exception to the
  "owner merges" rule, for this batch only).
- **This chat = the TELEGRAM-SUITE + §B chat.** Four PRs **MERGED to `main` this session:**
  **#55** (Experiment §C — clean_trend_stack 1h + per-book dedup, §53), **#56** (per-book Telegram
  summary + best/worst + today PnL + `:35` read-only status workflow, §54), **#57** (deadline/stale
  alert line + de-flaked a pre-existing flaky auth test, §55), **#58** (§B dynamic volume universe —
  opt-in, OFF the validated path, §56). This branch (`docs/closeout-telegram-suite-sB`) carries the
  **`/closeout`** PR.
- **Owner closeout answers (inferred — I auto-filled them; owner was away, correct if wrong):**
  shipped = *§C experiment + Telegram summary upgrades (per-book/best-worst/today/deadline) + :35
  status heartbeat + §B opt-in universe*; next priority = *forward-watch the new live books, then
  reconcile §B with the owner's real spec*; top risks = *§C + §A unvalidated, VWAP flip*;
  off-limits = *standard (validated §1 / FEE_PCT / live path / bot-owned journal)*.
- **Three LIVE changes shipped this session (watch them):**
  1. **Experiment §C `_cts` 1h book is LIVE** (§53) — separately tagged, per-book dedup lets it
     coexist with the baseline. The +0.1152R/n=804 claim is the owner's EXTERNAL harness, **not
     verified here.** Revert the §C step if its forward `_cts` record is net-negative.
  2. **`:35` read-only status ping is LIVE** (§54, `paper-status.yml`) — sends `notify-summary`
     only; no scan/write/commit. Confirm it pings (needs `TELEGRAM_*` secrets).
  3. **Enriched Telegram summary is LIVE** (§54/§55) — per-book / best-worst / today / deadline
     lines; all gated/back-compat.
- **Audit status:** the four work PRs (#55–#58) are **already MERGED** (owner-authorized batch) and
  this `/closeout` PR is being **merged too** (owner said "close each") — so there is **no pending
  merge gate**. Next chat should run `/handoff-audit` as a **POST-HOC** review: each shipped green
  CI, scoped diffs, honest bodies; none touch §1 geometry / `FEE_PCT` / `bracket.py` / `resolver.py`.
  `data/journal.json` was **NOT** edited this session (bot-owned; untouched by every PR).
- **🟢 §B "dynamic volume universe" — now has a NET-NEW opt-in implementation** (§56, PR #58), built
  from the descriptive name. The owner's external §B spec is **still not in this repo**; PR #58 does
  NOT claim to be it and is OFF the validated path. **NEXT: owner confirms it matches the intent or
  supplies the real spec to reconcile.**

## What this chat did (for the auditor to verify against the diff)

- **§53 / PR #55 — Experiment §C + per-book dedup.** `paper.py`/`cli.py`: `--clean-trend-stack`
  gate (13/50/800-EMA stacked 10 bars + widening 13/50 gap), setup tag `_cts`. **Structural:** dedup
  key `(symbol, tf)` → `(symbol, tf, book)` via `_book_of()` so §C coexists with baseline (else it
  logs nothing); net-exposure guard unchanged. UNVERIFIED external claim. `385 passed`.
- **§54 / PR #56 — Telegram summary + :35 heartbeat.** `notify.format_summary` gains per-book /
  best-worst / today-realized blocks (gated, back-compat tested); `review` trades carry `setup`;
  `_realized_today` uses `net_outcome_r`. New `paper-status.yml` (`cron 35`, `contents: read`,
  `notify-summary` only — no scan/write). `390 passed`.
- **§55 / PR #57 — deadline alert + de-flake.** `_deadline_line()` (`hours_to_deadline` on report).
  ALSO fixed flaky `test_tampered_cookie_is_rejected` (tampered base64 padding bits → no-op; now
  flips the first sig char, 40/40). `391 passed`.
- **§56 / PR #58 — §B dynamic volume universe.** `universe_rank.py` (`rank_by_volume` /
  `volume_ranked_universe` by mean `quote_volume`), `universe.CRYPTO_CANDIDATES`, CLI `universe-rank`
  (read-only). OFF by default, NOT wired into the workflow. Net-new; may differ from owner's spec.
  `396 passed`.
- **This PR — docs.** MEMORY §53–§56 + this baton. Read-only over the repo; no code change.

## NEXT chat

- **🟡 OWNER PRIORITY — RECONCILE §B + WATCH the new live books.** (a) Confirm PR #58's volume-ranked
  universe matches the intended §B, or get the real spec to reconcile (still not in this repo).
  (b) Forward-watch the books below. Advisory slug hint: `claude/reconcile-dynamic-volume-univ`.
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
  - **🚩 §C 1h `_cts` book is LIVE on an UNVERIFIED claim (§53, PR #55)** — owner's external
    +0.1152R/n=804, not reproduced here; separately tagged, revert if forward net-negative.
  - **🚩 VWAP ROTATION FLIP IS LIVE & UNVALIDATED (§44, PR #31)** — keep observing; be ready to revert.
  - **§A 5m long-only is a paper HYPOTHESIS** — separately tagged, but it IS logging a live
    (paper) book; revert if net-negative.
  - **§B universe (PR #58) is NET-NEW, not the owner's spec** — opt-in/off the validated path;
    reconcile before any thought of wiring it in.
  - **§42 maker fee is an ASSUMPTION** (0.0002/side) — Tier-2 must settle before leverage graduates.
  - **Dashboard (PR #21) UNVERIFIED in production.**
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; the live execution path
  (`bracket.py`/`resolver.py`). `data/journal.json` is bot-owned — the ONLY sanctioned session
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
- 2026-06-22: PR (this, `/closeout`) — docs/baton for the Telegram-suite + §B batch. Owner
  authorized self-merge of the whole batch; no pending merge gate → next chat audits POST-HOC.
  Live books to watch: §C `_cts`, §A `_lo`, breakeven arm, `:35` status ping. Reconcile §B spec.
