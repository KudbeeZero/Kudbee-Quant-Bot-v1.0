# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/trade-viz-draggable-indicators-yncx2t`
- **Last PR:** #10 — https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/10
- **Audit status:** `AWAITING_AUDIT`.
- ⚠️ **TWO open PRs (parallel-chat collision, §28/§30 pattern again):**
  PR **#9** (`claude/hello-7olm3u` — mission-control dashboard + TV-usable
  alert webhook + its own MEMORY "§32") was opened by a PARALLEL chat during
  this one. Both PRs touch `kudbee_quant/api.py`, `kudbee_quant/api_security.py`
  and append to `docs/MEMORY.md` — whichever merges second has real conflicts.
  This chat pre-renumbered its memory section to **§33** to dodge #9's §32.

## What this chat did (for the auditor to verify against the diff)

- **Trade Flow visualizer (PR #10), the user-confirmed scope:** node-graph
  confluence view — live flow / UNVALIDATED sandbox (drag factors out of the
  stack, EMA span overrides 2..2000, display-only gate) / journal-trade replay
  with SIGNAL/FILLED/TP1/RESOLVED event mapping — plus `trade-trace` CLI.
- New: `kudbee_quant/confluence/trace.py` (decorates `factor_votes`, parity
  pinned by test; `stack.py` zero-diff), `kudbee_quant/replay.py` (read-only,
  600-bar warmup = live-scan context), `trade-flow.html` + `assets/js/trade-flow.js`
  (vanilla JS, CSP 'self', Pointer-Events drag), `tests/test_trace.py` +
  `tests/test_trace_api.py` (18 tests).
- API: `GET /api/trace/{spec}`, `POST /api/sandbox/trace` (own 30/min scope,
  no token — compute-only), `GET /api/replay/{trade_id}`; `safe_spec()` added
  because `safe_symbol()` drops `yahoo:` → **/api/signal was always
  crypto-only** (documented, deliberately unchanged). `resolved_series` rows
  now carry `id`/`symbol`/`timeframe` (additive).
- **201 tests pass** at the merged-main head; live-verified on Binance+Yahoo
  data and driven in headless Chromium (drag-to-disable re-scored the gate to
  /9 live). `data/journal.json` and `validated_defaults.py` zero-diff.
- MEMORY **§33**: trace/replay layer + lesson — replay pct ≠ live-edge pct
  (trade `0bee2b4a`: ≥50% logged live, 20% recomputed at the SIGNAL bar).
- **Post-closeout rider (disclosed in PR #10 body):** `.claude/agents/
  laravel-specialist.md` added at the user's request (tooling-only, other-repo
  agent; no `kudbee_quant/**` impact). Also delivered the user a full-journal
  spreadsheet (105 trades; 15H/62M, −21.8R gross) — chat artifact, not committed.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/land-two-prs` — harness assigns the
  real name; the *scope* below is what binds.
- **Scope (one priority, user-confirmed 2026-06-12):** **audit + land BOTH
  open PRs, in creation order** — `/handoff-audit` PR #9 first (dashboard +
  webhook; it claims a §32 and a 191-test run), merge only on PASS; then audit
  PR #10 (this chat), resolve the conflicts the second merge hits
  (`api.py` imports/limiters region, `api_security.py` tail, `docs/MEMORY.md`
  tail — keep BOTH features and the §32/§33 numbering note), re-run the full
  suite on the resolved result, and reconcile this baton. **No new building
  until the board is clean** — the queued "Jarvis dashboard" scope was
  CONSUMED by PR #9; the TV-webhook queue item likewise.
- **Queued AFTER the board is clean (user-confirmed 2026-06-12): Execution
  Lab** — sliders (retrace/stop/target/TP1) over the SAVED live signals with
  instant re-sim via the shared resolver (§34 proved the engine; ~1s for 102
  trades). First experiments per the §34 autopsy: TP1 partial-banking (13
  misses ran ≥+1R unbanked; 19 stopped then ran to target), and the 5m-book
  fee question (~0.24R/trade fee drag — pausing 5m in the workflow is a USER
  decision, present the §34 numbers and ask). **Plus §35 (user's hypothesis,
  registered 2026-06-12): a SHADOW FADE BOOK** — log the mirrored bracket of
  every signal under its own setup tag so the fade idea gets a true forward
  test (+8.7R net in-sample but only ~12 independent bets, P(no edge)≈23% —
  NOT validated; do not size it, just log it). Variant to tag separately:
  fade only signals opposing the macro/HTF trend.
- **Open risks / watch-items:**
  - **NEW (§33):** replay pct ≠ live-edge pct is now visible per trade — never
    read a replay's confluence pct as a re-verification of the entry gate; the
    caveat ships in every replay response/CLI footer, keep it there.
  - `/api/signal` remains crypto-only (`safe_symbol` drops the source prefix);
    `/api/trace` is the routed alternative. Decide in a future chat whether
    signal should adopt `safe_spec` (breaking-change check: journal symbols).
  - PR #9 is from a parallel chat and is UNAUDITED — treat all its claims
    (191 tests, salvage provenance, alert-auth changes) as unverified until
    its audit passes.
  - §31 watch-items stand: 11 new TradFi symbols UNPROVEN forward; §29 pre-fix
    `filled_at` unreliable; maker-vs-taker fee contradiction still open (one
    real LIMIT fill settles it); scorecard still not an edge readout.
- **Off-limits (standing list unchanged):** validated strategy defaults (§1)
  and `FEE_PCT` (no change without walk-forward); `data/journal.json`
  (bot-owned — no session commits); crypto daily grouping stays calendar-dated;
  no deleting stale `claude/*` branches without explicit OK.

## Baton history

- `BOOTSTRAP` — relay protocol introduced (PR #2).
- `2026-06-09` — PR #2 merged from UI pre-audit; post-hoc audit PASS. Protocol
  hardened on `claude/handoff-audit-xtn2bz`: baton hands off scope (not a branch
  name), `/handoff-audit` checks real PR state + post-hoc path, status reconciled.
- `2026-06-10` — PR #4 merged (user-authorized, CI green): net-of-fee scoring (§26
  DONE) + protocol hardening. Duplicate PR #3 closed as superseded (§28). Next scope:
  TradFi session/RTH level verification.
- `2026-06-10` — PR #5 opened (`claude/fable-5-release-review-mow58s`): PR #4
  post-hoc audit PASS + TradFi session fixes (§29) — stub-day levels, Yahoo tick
  row, pending false-fills; 183 tests.
- `2026-06-10` — PR #5 **audited (PASS) and merged** by `claude/handoff-audit-hvuuab`
  (gate held). §28 recurred: that chat's duplicate trade-date fix reverted as
  superseded (§30). PR #6 opened (docs-only). Next scope: `_tradfi` taint audit +
  universe expansion (+11 assets); Jarvis dashboard queued after.
- `2026-06-11` — PR #6 **audited (PASS) and merged** at `dd809c9` by
  `claude/hello-1lje1b`; that chat shipped PR #7 (taint audit §31 + 11-symbol
  universe), self-audited PASS with caveat, merged. Next scope: Jarvis dashboard.
- `2026-06-12` — PR #10 opened (`claude/trade-viz-draggable-indicators-yncx2t`):
  Trade Flow visualizer (trace/sandbox/replay + CLI, §33), 201 tests,
  AWAITING_AUDIT. Parallel chat opened PR #9 (dashboard + webhook, §32 claim)
  mid-session — next scope: audit + land BOTH, #9 first, resolve conflicts.
