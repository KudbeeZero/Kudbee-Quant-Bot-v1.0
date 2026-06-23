# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** finish the unit → open ONE PR → merge →
  only then start the next. (Honor "owner merges" — never self-merge unless the owner
  explicitly authorizes a batch, as in a prior `/loop`.)
- **This chat = the TR LEVEL INTELLIGENCE chat.** ONE PR open: **#78**
  (`claude/tr-level-intelligence-qc4i2p` → `main`), **DRAFT, AWAITING_AUDIT**, CI/tests green
  locally (474 passed after merging current `main`).
- **Owner closeout answers (one-tap):** shipped = *TR Level Intelligence (D1) — persist
  `build_levels()` + unrecovered PVSRA vectors, `/levels` `/history` `/vectors`*; next priority =
  *provision the D1 DB (`wrangler d1 create` + migration) + forward-verify the commands on live
  data*; off-limits = *standard set + the trading/levels core (`build_levels`,
  `pvsra_vector_candles`, `paper_scan`, backtest harness)*.
- **NOTHING new is live in trading.** The intelligence layer is a NON-CRITICAL side-channel: OFF
  until `CF_ACCOUNT_ID`/`CF_API_TOKEN`/`D1_DATABASE_ID` are set; default path is a silent no-op,
  every D1 write is try/except-wrapped and runs AFTER `paper_scan()`. No signal added, no trading
  logic touched.
- **🚩 D1 is UNVERIFIED end-to-end** (see §64): no CF creds/network in the sandbox, so the
  `wrangler` create+migrate was NOT run, `wrangler.toml database_id` is a placeholder, and
  `/levels` `/vectors` `/history` were rendered against an in-memory sqlite proxy, not real D1.
- **Audit status:** `AWAITING_AUDIT`. Next chat runs `/handoff-audit` on **PR #78** — merge gate.
  Use the PR-body "Audit checklist". `data/journal.json` was NOT edited this session (bot-owned;
  the only data delta is the routine `main` merge of `data/heartbeat.json`/`journal.json`).

## What this chat did (for the auditor to verify against the diff)

- **§64 / PR #78 — TR Level Intelligence (D1).** New `kudbee_quant/intelligence/` package:
  `d1_client.py` (D1 REST), `level_recorder.py` (last-bar 54-field TR grid → `daily_levels`,
  `INSERT OR REPLACE`, idempotent per date+symbol+tf), `vector_tracker.py` (climax upsert +0.3%
  recovery → `unrecovered_vectors`). `cli._record_intelligence()` runs **after** `paper_scan()`,
  gated on `D1_DATABASE_ID`, try/except per-symbol + overall. Telegram `/levels` `/history`
  `/vectors` + help. Migration `0001_tr_levels.sql` (3 tables; `session_analytics` defined, not
  populated) + `wrangler.toml` D1 binding; `CF_*`/`D1_DATABASE_ID` in `.env.example`/`render.yaml`
  (`sync:false`). 9 new tests over an in-memory sqlite D1 proxy. **`474 passed`**, ruff clean.
  **VERIFY:** no change to `levels/builder.py` / `signals/pvsra.py` / `paper/paper.py` / backtest.

## NEXT chat

- **🟡 OWNER PRIORITY — PROVISION D1 + VERIFY LIVE (PR #78 first).** After the audit PASS-merges #78:
  (a) `wrangler d1 create kudbee-tr-levels`, apply `migrations/0001_tr_levels.sql`, paste the
  `database_id` into `wrangler.toml` AND Render (`D1_DATABASE_ID`); set `CF_ACCOUNT_ID` +
  `CF_API_TOKEN` in Render. (b) Run a paper-scan, then forward-verify `/levels` `/vectors`
  `/history` on real D1. Advisory slug hint: `claude/provision-tr-d1`.
- **WATCH the live changes (carried from prior batons — still live on `main`):**
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
  (`bracket.py`/`resolver.py`); **the trading/levels core — `build_levels()`,
  `pvsra_vector_candles()`, `paper_scan()` trading logic, the backtest harness** (this chat
  deliberately left them byte-identical; the intelligence layer reads, never mutates).
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
- 2026-06-23: PR #78 — TR Level Intelligence (D1) persistence: `daily_levels` +
  `unrecovered_vectors`, `/levels` `/history` `/vectors` (§64). Non-critical, OFF the trading path,
  D1 UNVERIFIED end-to-end. DRAFT, AWAITING_AUDIT. Next chat: `/handoff-audit` #78, then provision D1.
