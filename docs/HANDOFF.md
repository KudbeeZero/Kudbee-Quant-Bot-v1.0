# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branches:** `claude/homepage-admin-dashboard-redesign-3tdnki` (PR #21) +
  `claude/confluence-r-cycle-backtest-eg45m1` (PR #23).
- **Last PRs:** **#21** (gated admin/investor dashboard) and **#23** (cycle-aware OOS
  backtest) — both **MERGED to `main`** during a user-directed "get the PRs back on
  track" cleanup (2026-06-15).
- **Audit status:** `MERGED — UN-GATED (user-directed)`. ⚠️ Honest flag: #21 and #23
  were merged at the user's explicit instruction **without** the usual independent
  `/handoff-audit` gate. Both had a green CI run + full local suite, but neither got an
  arm's-length audit. **Recommend a post-hoc `/handoff-audit` on #21 and #23** to keep
  the record honest (write `docs/audits/pr-21-audit.md` / `pr-23-audit.md`). They are
  NOT part of the verified gate streak.
- **Gate streak (audited):** #5,#6,#7,#9,#11,#12,#13,#14,#16,#17,#20.
- Prior PRs CLOSED OUT: #14 (post-hoc CONCERNS), **#16** (live order path, PASS),
  **#17** (near-miss autopsy, PASS), **#20** (new entry signals, PASS, `0244ba0`),
  #19 (vector-candle logger) all MERGED to `main`.
- **#15 CLOSED** (stale audit artifact for the already-audited PR #14 — superseded).
- **#18 STILL OPEN — HELD for an explicit user go.** Top-100 universe + 5m re-enable
  on the **LIVE hourly Action**; it changes production *against our own evidence*
  (§37 5m fee-poison, §31 unproven top-100 tail). Defensible as a paper experiment but
  it is a live-automation change — do NOT merge without a clear user decision, and
  rebase it first (its base is stale).
- **#19 audit debt:** merged from the UI without an audit (research-only vector-candle
  logger; new `data/vector_log.json`) — no audit report on disk yet.

## What this cleanup did (for the auditor)

- Resolved PR #21's merge conflict with `main` (it had gone `dirty` after #22's baton
  reconciliation landed), re-ran the suite (**321 passed**), CI green → merged.
- Brought PR #23 current with `main` (resolved the recurring `MEMORY.md` §40 collision:
  §40 = dashboard, **§41 = cycle backtest**; consolidated the baton), re-ran the suite,
  merged.
- Closed #15 as superseded. Left #18 open (held).

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/render-deploy-verify`.
- **Scope (user-chosen 2026-06-15):** **Deploy + verify the dashboard (PR #21) on
  Render.** Stand up the service from `render.yaml`, set env vars
  (`KUDBEE_DASHBOARD_PASSWORD`, `KUDBEE_SESSION_SECRET`, plus the existing
  `KUDBEE_API_TOKEN`/`KUDBEE_SITE_ORIGIN`/`KUDBEE_GH_TOKEN`), then smoke-test the LIVE
  login→dashboard→runner flow (local-only so far). Runbook: `docs/HOSTING.md`.
- **GATE DEBT (do early):** post-hoc `/handoff-audit` on PR #21 and PR #23 (merged
  un-gated); decide #18 (live top-100+5m) yes/no; optionally back-fill a #19 audit note.
- **SETTLED by PR #23 — record the closure:** the `--min-pct 0.6` question is answered
  **NO, keep 0.5** (0.6 lowers net expectancy in every regime OOS and flips the 2022
  chop analog negative; 50% is the best 1h band). Remove it from the pending list — no
  more shadow-test needed. (MEMORY §41.)
- **Also queued:** wire the live executor (PR #16) into a CLI / hourly Action via a
  `BINANCE_TESTNET=true` smoke-test (`docs/LIVE_TRADING_SETUP.md`); Signal #4 (OI +
  liquidation-cluster levels — data-availability risk: OI hist ≈ 30d, liquidation
  history restricted); verify the 5m pause landed in production (§37).
- **Open risks / watch-items:**
  - **Dashboard (PR #21) UNVERIFIED in production** — login/session/runner/redesign
    smoke-tested LOCALLY only; never run on a real Render host (no service exists yet).
  - **Runner results are ephemeral** (in-memory; gone on redeploy).
  - **Three CSP sources of truth** now (`netlify.toml`, `_headers`, the FastAPI header
    in `api.py`) — keep in sync; Netlify CSP still has `unsafe-inline` (marketing
    pages, not redesigned). There is ALSO a Cloudflare Pages deploy on this repo
    (static site) — it deployed the branch fine, but it's a 3rd static host to remember.
  - **#21/#23 merged un-gated** (audit debt, above).
  - **Cycle backtest caveats (PR #23):** the pooled "overall −0.019R" is a 5m artifact
    (71% of trades) — never quote without the 1h context (+0.096/+0.060, n=8,124). The
    chop-analog 1h samples are small (2018 n=450 on 5 coins, 2022 n=951) → "survives
    chop" is positive-but-low-confidence. 1h net-taker cushion is thin (~+0.02–0.06R)
    → size conservatively.
  - **PR #20 signals NOT validated for live use** — keep flags OFF, forward-test.
  - **Live execution EXISTS but UNPROVEN live (PR #16);** **top-100 unproven (§31);**
    **5m pause unverified in prod (§37);** **possible 1h edge decay (§36/§37).**
  - **Branch deletions pending (§32):** handoff-audit-*, hello-*, overnight-*,
    sol-short-*, fable-5-*, zcash-* set (safe via GitHub UI).
  - **§33** replay pct ≠ live-edge pct; **§29/§30** maker-vs-taker fee open item.
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; `data/journal.json`
  (bot-owned — no session commits); `data/alert_inbox/` (host+Action-owned — no manual
  session commits); crypto daily grouping stays calendar-dated; held salvage branches
  only with explicit user OK. Keep PR #20's feature flags + filters OFF until forward-
  validated; hold the parsimony line (no removed vote — BOS/RSI-div/funding/OB/macro —
  back as a vote). Preserve the runner's no-journal-write guarantee (paper-scan stays
  `dry_run=True`); the curated runner stays a fixed whitelist (never arbitrary code);
  don't rework the session-cookie scheme casually (real accounts build on it).

## Baton history
- … (prior entries in git) …
- 2026-06-14: PR #20 — new entry signals (taker delta/CVD, volume profile, killzone
  gate), opt-in/default-OFF, independently validated; honest negative; 60% band
  confirmed net-positive OOS. Audited PASS, merged at `0244ba0`.
- 2026-06-15: PR #21 — gated admin/investor dashboard (shared-password login + signed
  session cookie, mobile-first Tailwind, curated non-RCE runner that never writes the
  journal, new gated endpoints). Local-only verification. Merged un-gated (user-directed).
- 2026-06-15: PR #23 — cycle-aware OOS backtest (137k trades). Live 1h config net-
  positive & full-taker-survived in all 3 regimes; 5m dead, 15m maker-only; `min_pct
  0.6` refuted OOS → keep 0.5. Merged un-gated (user-directed).
- 2026-06-15: cleanup — fixed #21's conflict, brought #23 current, merged both, closed
  stale #15, held #18. Next scope: deploy + verify the dashboard on Render.
