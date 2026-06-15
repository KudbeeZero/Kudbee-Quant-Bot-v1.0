# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/homepage-admin-dashboard-redesign-3tdnki`
- **Last PR:** #21 — https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/21
  (gated admin/investor dashboard: login + Tailwind + curated runner).
- **Audit status:** `AWAITING_AUDIT` — PR #21 not yet gated. Rebased onto current
  `main` (`8568c03`, which includes the #20 audit + the #22 baton reconciliation);
  doc conflicts resolved; suite re-run green.
- **PR #20 RESOLVED → `MERGED (audit PASS)`** — gated by `claude/handoff-audit-h90pmc`
  (independent arm's-length subagent, isolated worktree): 304/304 reproduced,
  default-OFF byte-identical invariance re-verified, §1/`FEE_PCT`/journal/alert_inbox
  untouched, parsimony honored (no new vote), honest-negative reports. Report
  `docs/audits/pr-20-audit.md`. Merged at `0244ba0` (branch had no GitHub CI check;
  auditor reproduced the green suite + ruff locally and the user approved on that
  basis). Gate streak: #5,#6,#7,#9,#11,#12,#13,#14,#16,#17,#20.
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

- **Gated admin/investor dashboard (PR #21)** — front-end re-haul behind a login
  gate. User-confirmed scope: shared password now (no email/DB), curated non-RCE
  runner, compiled Tailwind. MEMORY **§40**. 321 passed (+17 new tests); new files
  ruff-clean. §1 / `FEE_PCT` / journal / alert_inbox untouched; no secrets.
  - **Auth** (`kudbee_quant/api_auth.py`): `KUDBEE_DASHBOARD_PASSWORD` → HMAC-signed
    HttpOnly/Secure/SameSite session cookie (`KUDBEE_SESSION_SECRET`). Hand-rolled,
    no new deps, fail-closed like `check_token`. `/` + `/dashboard` 302→`/login`
    without a session; gated APIs 401; login 5/min.
  - **Curated runner** (`kudbee_quant/api_runner.py`): fixed-dict whitelist (signal/
    backtest/validate/sweep/bracket-sweep/paper-scan), Pydantic-bounded params,
    async in-memory jobs (2-worker pool, 429 when busy). NOT a code executor;
    **NEVER writes the journal** — paper-scan uses the new `paper_scan(dry_run=True)`
    seam (only change to `paper/paper.py`), guarded by
    `test_paper_scan_dry_run_never_writes_journal`.
  - **New gated reads:** `/api/open-trades`, `/api/trade-history`, `/api/research`.
  - **Tailwind** compiled + committed (`assets/css/app.css` + `static/app.css`);
    `npm run build`; `node_modules/` gitignored. **Strict CSP added on the Render
    host** (had none) → dashboard/login JS externalized to `static/app.js` +
    `static/login.js`. Dashboard redesigned mobile-first.
  - **SEO/deploy:** `noindex` + `X-Robots-Tag` + robots.txt disallow on private
    pages; `render.yaml` adds the 2 env vars; `docs/HOSTING.md` updated.
  - **AUDIT NOTE:** verified LOCALLY only (smoke test passed) — never run on a real
    Render host. Marketing pages keep their CSS; Netlify CSP still has
    `style-src 'unsafe-inline'` (not tightened on purpose).

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/render-deploy-verify` — harness assigns
  the real name; the *scope* below is what binds.
- **Scope (user-chosen 2026-06-15):** **Deploy + verify the dashboard on Render.**
  Stand up the real Render service from `render.yaml`, set the new env vars
  (`KUDBEE_DASHBOARD_PASSWORD`, `KUDBEE_SESSION_SECRET`, plus the existing
  `KUDBEE_API_TOKEN`/`KUDBEE_SITE_ORIGIN`/`KUDBEE_GH_TOKEN`), then smoke-test the
  LIVE login→dashboard→runner flow end-to-end (the whole thing is local-only so far).
  Runbook: `docs/HOSTING.md`. (Likely needs the user to create the Render Blueprint;
  the chat drives the verification + any fixes that surface.)
- **GATE FIRST:** run `/handoff-audit` on **PR #21** (and ideally **PR #20**, which
  was never audited) before new work — merge only on a PASS.
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
  - **Dashboard UNVERIFIED in production (PR #21):** login + session + runner +
    redesign were smoke-tested LOCALLY only — never run on the real Render host
    (no service exists yet). This is the #1 risk the user flagged for next chat.
  - **Runner results are ephemeral** (in-memory; gone on every redeploy — the
    hourly journal commit redeploys often). Surfaced honestly in the UI.
  - **Three CSP sources of truth now** (`netlify.toml`, `_headers`, the FastAPI
    header in `api.py`) — keep in sync; Netlify CSP still has `unsafe-inline`
    (marketing pages). Marketing HTML was NOT redesigned (keeps existing CSS).
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
  branches only with explicit user OK. **PLUS (still in force):** keep the new
  feature flags + filters OFF in the live path until forward-validated, and hold the
  parsimony line (no removed vote — BOS/RSI-div/funding/OB/macro — back as a vote).
  **PLUS (this chat):** preserve the runner's no-journal-write guarantee (paper-scan
  stays `dry_run=True`); the curated runner stays a fixed whitelist (never arbitrary
  code); don't rework the session-cookie scheme casually (real accounts build on it).

## Baton history
- … (prior entries in git) …
- 2026-06-14: PR #20 — new entry signals (taker delta/CVD, volume profile, killzone
  gate), all opt-in/default-OFF, independently validated; honest negative (filters
  fail OOS, meta-feature lift near noise floor); 60% band confirmed net-positive OOS.
  Next scope: Signal #4 (OI + liquidation-cluster levels). [NOTE: not audited — next
  chat jumped to a feature request; #20 still AWAITING_AUDIT.]
- 2026-06-15: PR #21 — gated admin/investor dashboard (shared-password login +
  signed session cookie, mobile-first Tailwind redesign, curated non-RCE test runner
  that never writes the journal, new gated data endpoints). Local-only verification.
  Next scope: deploy + verify on Render.
