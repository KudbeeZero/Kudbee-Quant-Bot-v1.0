# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** finish the unit → open ONE PR → merge →
  only then start the next. This chat ran units **serially and compliantly** — each unit
  was its own PR, merged before the next began (one brief user-directed exception: the docs
  PR was queued while #50 was open, then deferred to after #50 merged).
- **This chat = the EXECUTION chat.** Six PRs **MERGED to `main` this session:**
  **#46** (your trade-flow Walkthrough tab — cleared the board), **#47** (arm pay-yourself
  breakeven exit, §49), **#48** (flatten 40 stale 2h/4h zombies, §50), **#49** (exit-geometry
  5m study, §51), **#50** (Experiment §A — 5m long-only book, §52), **#51** (docs §49–§52 +
  baton). This branch (`docs/update-handoff-memory-s47-sA`) carries the **`/closeout`** PR —
  the final baton.
- **Owner closeout answers (authoritative):** shipped = *breakeven + flatten + 5m study + §A*;
  next priority = **resolve §B**; top risk = *§A unvalidated + VWAP flip*; off-limits = *standard*.
- **Two LIVE changes shipped this session (watch them):**
  1. **Breakeven exit is now ARMED on the hourly 1h book** (§49) — new predictions stamp
     `tp1 = entry+1R`, stop→breakeven, ride to +3R. **Confirm:** look for `tp1=1.0`-equivalent
     (`tp1` non-null) on the first new opens.
  2. **Experiment §A 5m long-only book is LIVE** (§52), separately tagged `_lo` — a
     forward-test HYPOTHESIS, not a validated edge.
- **Audit status:** this `/closeout` PR is **`AWAITING_AUDIT`** (next chat's `/handoff-audit`
  is the merge gate for the baton). The six work PRs (#46–#51) are **already MERGED** — review
  them **post-hoc**: each shipped green CI, scoped diffs, honest bodies; none touch §1 geometry /
  `FEE_PCT` / `bracket.py` / `resolver.py` logic. `data/journal.json` was edited ONLY by the
  idempotent flatten script (#48, 3 fields × 40 records) — otherwise bot-owned.
- **🟡 §B "dynamic volume universe" — PENDING REF.** The owner says §B exists elsewhere; it is
  **not in this repo** (searched all 47 branches + every commit — no trace). This baton does
  NOT document §B (no fabrication). **NEXT: owner provides the §B PR/commit/branch ref (or
  "not built yet") and I'll add it.**

## What this chat did (for the auditor to verify against the diff)

- **§49 / PR #47 — breakeven exit armed.** `cli.py` (+`--tp1-frac`/`--no-be` on paper-scan,
  threaded into `_paper_scan`), `paper.py` (`be_after_tp1` → `Prediction`), `paper-trade.yml`
  (both 1h scans now `--tp1-r 1.0 --tp1-frac 0.0`), +3 resolver tests. Caught that the
  "config-only" premise was false (flag didn't exist; literal change would've silently killed
  the bot via `|| true`). `378 passed`.
- **§50 / PR #48 — zombie flatten.** `scripts/flatten_stale_tf.py` (idempotent) retired 40
  open 2h/4h positions → `status="flattened"` (non-scoring; mark-R in `reason_closed`;
  `outcome_r` None). Raw-JSON targeted edit; non-targets byte-identical; count 703 preserved.
  Found `journal-score` buckets by `setup` (timeframe-agnostic) so zombies would have dragged
  the 1h record.
- **§51 / PR #49 — exit-geometry 5m study.** `--exit-geometry` on `leverage_be_study.py`;
  stop-width × BE-trigger sweep, adverse-first via `sim_policy`. **All 24 combos net-negative;
  best −0.243R; quarter-Kelly ≤0 → DO NOT BET.** Outputs `data/exit_geometry_5m.json` +
  `reports/exit_geometry_5m.md`. `378 passed`.
- **§52 / PR #50 — Experiment §A.** `long_only` + `killzone_gate` flags; §A workflow step
  (5m, long-only, pay-yourself). Long-only verified on `excursion_audit.json` subset (n=48,
  32%/14%) but full-journal n=182 is ~16%/17% → **hypothesis, not validated.** Killzone gate
  ships **UNARMED** (hurts 5m: 20% inside vs 28% outside). `380 passed` (+2 flag tests).
- **This PR — docs.** MEMORY §49–§52 + this baton. Read-only over the repo; no code change.

## NEXT chat

- **🟡 OWNER'S CHOSEN PRIORITY — RESOLVE §B** (dynamic volume universe). The owner confirms
  it exists elsewhere; it is **not in this repo** (47 branches + all commits searched). Get the
  ref (PR/commit/branch/other-repo, or the spec if unbuilt), then document (MEMORY §53 + baton)
  or build it as the next serial unit. Advisory slug hint: `claude/resolve-dynamic-volume-univ`.
- **WATCH the two live changes:**
  - **§A 5m long-only book (§52):** after ≥30 forward `_lo` trades, run `journal-score`
    filtered to `timeframe=5m`. Net expectancy > 0R net of fees → continue; else → **revert the
    §A workflow step** (same trigger as §37). 5m has been net-negative every prior look.
  - **Breakeven arm (§49):** confirm new 1h opens carry a non-null `tp1`; watch whether
    stop→BE actually lifts the reverted 1h book's expectancy over a forward window.
- **STILL OPEN from §48:** the reverted §1 book (top-10/1h) — does it turn positive once the
  alt+5m drag is gone, or is there a real backtest→live gap (regime/decay)? Candidate
  edge-builder: the **killzone/hour gate for 1h** (the flag now exists, UNARMED) to cut the
  18h/06h toxic clusters — forward-validate before arming.
- **Tier-2 leverage (still queued, §47):** (a) re-rate the candidate net with **maker-entry +
  taker-exit** (asymmetric friction; the study's both-maker under-charges crypto); (b)
  `BINANCE_TESTNET` micro-stake. Only then can `lock+0.1R/≤10x/maker` graduate (micro-stake only).
- **Open risks / watch-items (still live):**
  - **🚩 VWAP ROTATION FLIP IS LIVE & UNVALIDATED (§44, PR #31)** — keep observing; be ready to revert.
  - **§A 5m long-only is a paper HYPOTHESIS** — separately tagged, but it IS logging a live
    (paper) book; revert if net-negative.
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
- 2026-06-22: PR (this, `/closeout`) — final baton, `AWAITING_AUDIT`. Owner priority: resolve
  §B (not in repo). Watch the §A 5m long-only book + the breakeven arm forward. §A unvalidated
  + VWAP flip are the live risks.
