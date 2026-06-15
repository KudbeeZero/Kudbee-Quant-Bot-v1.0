# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/confluence-new-signals-audit-a6gxt6`
- **Last PR:** #20 — https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/20
  (new entry signals, opt-in/default-OFF, independently validated).
- **Audit status:** `MERGED (audit PASS)` — PR #20 gated by `claude/handoff-audit-h90pmc`
  (independent arm's-length subagent, isolated worktree): 304/304 reproduced,
  default-OFF byte-identical invariance re-verified, §1/`FEE_PCT`/journal/alert_inbox
  untouched, parsimony honored (no new vote), honest-negative reports (2 of 3 signals
  OOS-failures, IS/OOS separated). Report `docs/audits/pr-20-audit.md`. Merged at
  `0244ba0` — note: the branch had **no GitHub CI check** (none triggered); the
  auditor reproduced the full green suite + ruff locally and the user approved the
  merge on that basis. Gate streak: #5,#6,#7,#9,#11,#12,#13,#14,#16,#17,#20.
- Prior PRs CLOSED OUT: #14 (post-hoc CONCERNS, merged from UI), **#16** (live
  order-placement, audit PASS), **#17** (near-miss autopsy, audit PASS), #19
  (vector-candle logger) all MERGED to `main`.
- **PROTOCOL BREAKDOWN flagged this session (parallel chats):** the `claude/handoff-audit-h90pmc`
  session found 4 un-gated PRs the prior baton never mentioned. Resolved #20 (above).
  **Still needing attention:**
  - **#18 OPEN — top-100 universe + 5m re-enable on the LIVE hourly Action**
    (user-directed §39). CI green, but it changes production *against our own evidence*
    (§37 5m fee-poison, §31 unproven top-100 tail — the PR is honest about this). NOT
    audited, NOT merged — held for an explicit user go (it's a paper-book experiment,
    defensible, but it is a live-automation change).
  - **#19 MERGED from the UI without an audit** (vector-candle logger, research-only,
    `data/vector_log.json` new artifact) — no post-hoc audit report on disk yet.
  - **#15 OPEN, stale** — docs-only audit artifact for PR #14 from a parallel chat;
    PR #14 was already audited via `docs/audits/claude-hello-3vl2b8.md`. Recommend close
    as superseded.

## What this chat did (for the auditor to verify against the diff)

- **New-signals audit + 3 signals (PR #20)** — extended the entry system with
  genuinely-missing signals WITHOUT re-adding the 5 removed votes; each opt-in,
  default OFF, independently validated on real 1h data (top-10 majors, 8000 bars,
  canonical bracket). Mostly an **honest negative**; kept as infra, NOT enabled live.
  - **#1 taker delta / CVD / delta-div** (`levels/delta.py`) — un-dropped
    `taker_buy_base` in `ingest/binance.py` (+ `resample`). `delta_align` FILTER
    **fails OOS**; meta FEATURES **pass** the GBT gate (p=0.0073, +0.094R).
  - **#2 volume profile** POC/VAH/VAL/naked-POC (`levels/volume_profile.py`,
    `OPTIONAL_LEVEL_COLUMNS`) — filter **inconclusive** (helps OOS, hurts IS);
    features pass but near-boundary.
  - **#3 killzone gate** (`confluence_position(killzone_gate=)`) — **FAILS OOS**;
    hour map shows OFF-hours +0.102R vs in-killzone +0.021R (16h UTC best & off-KZ).
  - **60% band:** +0.25R net-positive OOS — the stale −31R does NOT reproduce;
    **corroborates PR #17's autopsy** (don't drop the 60% band).
  - Gating in `config/features.py` (flags default OFF) + 3 `confluence_position`
    filter params (default OFF). Validation: `scripts/validate_*`. Reports:
    `docs/research/signal-{1,2,3}-*.md`. MEMORY §39. 304 passed; new modules ruff-clean.
    §1 / `FEE_PCT` / journal / alert_inbox untouched; no new votes.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/signal-4-oi-liquidations` — harness assigns
  the real name; the *scope* below is what binds.
- **Scope (user-chosen 2026-06-14):** **Signal #4 — open-interest + liquidation-cluster
  levels** (the BUILD list's stretch item). New ingest module; map OI / liquidation
  clusters as liquidity draws (level columns), gated behind config default OFF, then
  validate the SAME way (walkforward + meta-model CV, IS vs OOS) and keep ONLY on an
  OOS improvement. **Data-availability risk:** Binance OI history ≈ last 30 days
  (`fapi /futures/data/openInterestHist`); public liquidation HISTORY is restricted
  (only the live `forceOrders` stream) — a clean OOS test may not be achievable
  without an alternative source. Report the data limit honestly; if OOS isn't
  possible, deliver the levels + a forward-only plan rather than overclaiming.
- **STILL PENDING (user decision, from PR #17):** the autopsy's `--min-pct 0.6`
  hourly-scan tweak. Verdict was: do NOT drop the 60% band / lower the target (both
  OVERFIT, OOS-refuted; 3R correct, 60% gate net-positive OOS — now corroborated by
  PR #20). The only OOS-supported tweak is `--min-pct 0.5→0.6`, and even that is
  modest — RECOMMEND a forward shadow-test (journal 0.5 vs 0.6 in parallel), NOT a
  hard flip. **Awaiting user approval before any live-config change.**
- **Also queued:** (b) wire the live executor (PR #16) into a CLI / hourly Action —
  start `BINANCE_TESTNET=true` smoke-test (`docs/LIVE_TRADING_SETUP.md`); (c) top-100
  universe flip decision (`docs/TOP100_1H_UNIVERSE.md`).
- **FIRST (carryover): verify the 5m pause landed** — confirm the hourly Action logs
  NO new `5m` signals (§37 still unverified in production).
- **Live deploy walkthrough (queued):** once the user creates the Render service
  (`docs/HOSTING.md`), smoke-test the live host (health, dashboard, `/api/alert` with
  `"inbox": true`, the commit landing in `data/alert_inbox/`).
- **Open risks / watch-items:**
  - **PR #20 signals are NOT validated for live use:** delta_align & killzone gate
    FAIL OOS; volume-profile is inconclusive; the meta-feature lift (delta + vp) is
    near the noise floor (baseline gate p≈0.064, any mild feature set tips it to
    ~0.005 with the same ~0.329R). One window/universe — **forward-test before
    enabling any flag (`ENABLE_TAKER_DELTA`/`ENABLE_VOLUME_PROFILE`) or filter live.**
  - **Live execution EXISTS but UNPROVEN live (PR #16):** maker-only, double-gated,
    logic-tested only — never placed a real order. Paper still default. Start testnet.
  - **Top-100 membership UNPROVEN forward (§31):** only top-10 majors are
    walk-forward validated; the long tail is a static fallback snapshot.
  - **5m pause UNVERIFIED in production (§37).**
  - **Deployment UNPROVEN:** render.yaml + inbox tested locally only.
  - **Possible edge decay on 1h crypto book** (§36/§37) — re-check as data accrues.
  - **Branch deletions pending (§32):** safe to delete via GitHub UI — the
    handoff-audit-*, hello-*, overnight-*, sol-short-*, fable-5-*, zcash-* set.
  - **§33** replay pct ≠ live-edge pct; **§31** 11 TradFi symbols unproven forward;
    **§29/§30** standing caveats + maker-vs-taker fee open item (one real LIMIT fill
    settles it).
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; `data/journal.json`
  (bot-owned — no session commits); `data/alert_inbox/` (host+Action-owned — no
  manual session commits); crypto daily grouping stays calendar-dated; held salvage
  branches only with explicit user OK. **PLUS (this chat):** keep the new feature
  flags + filters OFF in the live path until forward-validated, and hold the
  parsimony line (no removed vote — BOS/RSI-div/funding/OB/macro — back as a vote).

## Baton history
- … (prior entries in git) …
- 2026-06-14: PR #20 — new entry signals (taker delta/CVD, volume profile, killzone
  gate), all opt-in/default-OFF, independently validated; honest negative (filters
  fail OOS, meta-feature lift near noise floor); 60% band confirmed net-positive OOS.
  Next scope: Signal #4 (OI + liquidation-cluster levels).
