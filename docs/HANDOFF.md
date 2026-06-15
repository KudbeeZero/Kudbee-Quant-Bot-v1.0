# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE NOW ACTIVE (2026-06-15, user-set):** all implementation work is
  strictly serial — **finish the unit → open ONE PR → audit → merge → only then start
  the next unit**; only one PR open at a time; no new implementation while a PR is open
  or awaiting audit. Purely *observational* background tasks (e.g. the #18 watch loop)
  are exempt. The cross-session orchestration timeline now lives in the new
  **`docs/AGENT_ORCHESTRATION_LEDGER.md`** (complements this baton + `docs/audits/`).
- **This chat = the WEBSITE chat.** Branch `claude/site-trade-demo` (off `main`). It is
  a **front-end-only** session: a new animated "trade story" hero + a site-wide mobile /
  polish / sitemap / font sweep. No `kudbee_quant/`, workflow, or `data/` changes.
- **Last PR:** **#29** — site front-end only. (Opened draft, marked READY at closeout.)
  https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/29
- **Audit status:** `AWAITING_AUDIT` — next chat runs `/handoff-audit` on **#29** (a
  diff/scope/honesty check; there are no engine changes to re-derive).
- **Prior chats' PRs all merged:** **#27** (audit/baton) and **#28** (orchestration
  ledger) are on `main` — the ledger content is live. The stale local
  `claude/agent-orchestration-ledger` branch was superseded by the merged #28; ignore/
  delete it. The leftover agent worktrees from this chat were pruned at closeout.
- **🎯 MILESTONE (paper §43 experiment):** the **first post-#18 hourly run, #50**
  (2026-06-15 18:27Z) **SUCCEEDED** — ~5m32s, no timeout / no Binance rate-limit crash
  (longer than the old ~1–2 min, as expected for ~101 pairs × 5 TF). It logged **+83 new
  setups across the top-100, incl. 27 on 5m**, to `data/journal.json` (`194013b`). The
  §37 5m-fee-drag concern is now under live forward test — **watch #50's setups resolve**
  over the coming hours/days; revert to top-10/no-5m if 5m re-confirms §37.
- **Open PRs now:** only **#29**.

## What this chat did (for the auditor to verify against the diff)

A **front-end-only** session on the static marketing site. Built with two sub-agents in
isolated worktrees (centerpiece + mobile sweep), integrated + verified here. The PR diff
touches **only** `*.html`, `assets/css/*`, `assets/js/*`, `sitemap.xml` — **no
`kudbee_quant/`, workflow, or `data/` changes.**

- **New animated "trade story" hero** — `assets/js/trade-story.js`,
  `assets/css/trade-story.css`, standalone `trade-story.html`. A ~60s `<canvas>` loop of a
  **W double-bottom + liquidity sweep** of a psychological low, **PVSRA vector candles**,
  **daily-open / psych-high / psych-low** levels, and a 5-agent thinking/notes
  choreography (Liquidity → PVSRA → Structure → Reviewer → Risk) ending in a **3R
  bracket**. `prefers-reduced-motion` → one static composed frame; rAF pauses offscreen;
  responsive to ~360px (narrow screens show **one bubble at a time**). **Clearly labelled
  ILLUSTRATIVE — not live data, not a track record.** Replaced the old hero sparkline mock
  in `index.html` (3-line wire-in: css link + mount `<div>` + script).
- **Mobile / polish sweep** — `assets/css/style.css`, the page set, `sitemap.xml`,
  `assets/js/main.js`: responsive fixes 360–768px, mobile nav hamburger (44px targets +
  scroll-lock), fluid headings, compare-table scroll-snap, signals/equity/dash grid
  collapses, `sitemap.xml` `lastmod` refresh, about-page compare-table highlight fix,
  added the missing nav hamburger / CTA / `main.js` include to `lab` / `live-signals` /
  `trade-flow`.
- **Homepage font bug FIXED** — root cause: `lab` / `live-signals` / `trade-flow` loaded
  Google Fonts **without the 400 weight**, poisoning the shared cache key so index body
  text fell back to `system-ui`. Aligned all pages to `wght@400;500;600;700`.
- **Public dev-message leak FIXED** — `live-signals.js` + `trade-flow.js` no longer print
  visitors *"Backend unavailable … uvicorn kudbee_quant.api:app"*; graceful offline copy,
  dev hint moved to `console.warn`. NB: the public static site has **no `/api` backend**,
  so the 404 is expected — if a live backend is ever intended on the deployed marketing
  site, that's a separate Render/Netlify-proxy task (NOT done here).
- **Verification:** headless Chromium (Playwright) screenshots of desktop + mobile (360/
  390px) + the wired homepage hero confirm candles, levels, vector colours, agent
  bubbles/notes, and the 3R bracket all render. Suite green at closeout (pytest exit 0,
  ~324 tests; the diff touches no Python).

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/handoff-audit` → then `claude/render-deploy-verify`.
- **FIRST: run `/handoff-audit` on PR #29** (this chat's WEBSITE PR), merge on PASS so
  `main` is current. It's front-end only — the audit is a diff/scope/honesty check (assert
  no `kudbee_quant/`/workflow/`data/` changes; the trade-story stays labelled illustrative;
  the font/leak fixes are real). Then start the next branch.
- **Also worth a glance:** the §43 paper experiment — run **#50** (first post-#18) ran
  clean and opened 83 setups incl. 27 on 5m; check the next runs for timeouts and whether
  the 5m setups resolve net-negative (fee drag, §37) → revert top-100/5m if so.
- **Scope (deferred, now unblocked):** **Deploy + verify the dashboard (PR #21) on
  Render.** Stand up the service from `render.yaml`, set env vars
  (`KUDBEE_DASHBOARD_PASSWORD`, `KUDBEE_SESSION_SECRET`, plus existing
  `KUDBEE_API_TOKEN`/`KUDBEE_SITE_ORIGIN`/`KUDBEE_GH_TOKEN`), then smoke-test the LIVE
  login→dashboard→runner flow (local-only so far; #25 added `psutil` for the System
  panel). Runbook: `docs/HOSTING.md`.
- **Watch after #18 merged:** the hourly Action now scans ~101 pairs × 5 TF incl. 5m —
  check the **first few runs** for timeout / Binance rate-limits and journal growth;
  REVERT to top-10/no-5m if it times out or 5m re-confirms §37 (§43).
- **Optional debt back-fill:** post-hoc audit notes for #25 / #26 / #19 (all low-risk).
- **SETTLED — record the closure (PR #23 §41 + corroborated by PR #24 §42):** the
  `--min-pct 0.6` question is answered **NO, keep 0.5**. No more shadow-test needed.
  ALSO settled (§42): **market/hybrid execution is a DEAD END** — do not re-test blanket
  market or next-bar-open entry; the maker retrace wins on every TF.
- **Also queued:** wire the live executor (PR #16) into a CLI / hourly Action via a
  `BINANCE_TESTNET=true` smoke-test (`docs/LIVE_TRADING_SETUP.md`); Signal #4 (OI +
  liquidation-cluster levels — data-availability risk: OI hist ≈ 30d, liquidation
  history restricted); verify the 5m pause landed in production (§37).
- **Open risks / watch-items:**
  - **PR backlog GATED (was the user's flagged risk):** #24 audited PASS + merged;
    #21 + #23 post-hoc PASS; #18 merged (user-directed paper experiment). Residual
    low-risk debt: #25/#26/#19 un-audited (optional back-fill). No open backlog.
  - **§42 maker fee is an ASSUMPTION:** the maker side (0.0002/side) is unconfirmed
    pending one real LIMIT fill (§25). The 15m/1h verdict margins are fee-sensitive —
    a higher maker rate narrows (does not flip) the maker-vs-market gap.
  - **§42 adverse-selection number is BIASED:** the +1.1R "cancels as market" figure is
    upward-biased by selection conditioning — a DIAGNOSTIC that cancels lean to runners,
    NOT harvestable edge. Do not act on it as a market-entry signal.
  - **Dashboard (PR #21) UNVERIFIED in production** — login/session/runner/redesign
    smoke-tested LOCALLY only; never run on a real Render host (no service exists yet).
  - **Runner results are ephemeral** (in-memory; gone on redeploy).
  - **Three CSP sources of truth** now (`netlify.toml`, `_headers`, the FastAPI header
    in `api.py`) — keep in sync; Netlify CSP still has `unsafe-inline` (marketing
    pages, not redesigned). There is ALSO a Cloudflare Pages deploy on this repo
    (static site) — it deployed the branch fine, but it's a 3rd static host to remember.
  - **#21/#23 audited post-hoc PASS** (`docs/audits/pr-21-audit.md` / `pr-23-audit.md`).
  - **Cycle backtest caveats (PR #23):** the pooled "overall −0.019R" is a 5m artifact
    (71% of trades) — never quote without the 1h context (+0.096/+0.060, n=8,124). The
    chop-analog 1h samples are small (2018 n=450 on 5 coins, 2022 n=951) → "survives
    chop" is positive-but-low-confidence. 1h net-taker cushion is thin (~+0.02–0.06R)
    → size conservatively.
  - **PR #20 signals NOT validated for live use** — keep flags OFF, forward-test.
  - **Live execution EXISTS but UNPROVEN live (PR #16);** **top-100 unproven (§31);**
    **possible 1h edge decay (§36/§37).** NOTE: the §37 5m pause was REVERSED in prod by
    PR #18 (§43) at user direction — 5m is now scanning live on the paper Action as an
    experiment; the §37 fee-drag finding is unchanged, so watch the new 5m data confirm/
    refute it and revert if needed.
  - **Branch deletions pending (§32):** handoff-audit-*, hello-*, overnight-*,
    sol-short-*, fable-5-*, zcash-* set (safe via GitHub UI).
  - **§33** replay pct ≠ live-edge pct; **§29/§30** maker-vs-taker fee open item.
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`, and the live
  execution path (`bracket.py`/`resolver.py`) — do NOT change entry on the strength of
  this research. **No market/hybrid execution flip (§42): proven worse on every TF;
  keep the maker retrace, 5m paused, `min_pct` 0.5.** `data/journal.json` (bot-owned —
  no session commits); `data/alert_inbox/` (host+Action-owned — no manual session
  commits); crypto daily grouping stays calendar-dated; held salvage branches only with
  explicit user OK. Keep PR #20's feature flags + filters OFF until forward-validated;
  hold the parsimony line (no removed vote — BOS/RSI-div/funding/OB/macro — back as a
  vote). Preserve the runner's no-journal-write guarantee (paper-scan stays
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
- 2026-06-15: PR #24 — execution head-to-head (maker-retrace vs market vs hybrid, OOS,
  net of fees; offline, live path untouched). Maker retrace wins on every TF/regime;
  market never wins; cancels are runners but not harvestable. MEMORY §42. Market/hybrid
  entry logged as a DEAD END. AWAITING_AUDIT. Next scope: gate the open PR backlog.
- 2026-06-15: PR #27 (`claude/handoff-audit-3dgde4`) — `/handoff-audit` gate-the-backlog
  chat. Independent audits: #24 PASS→merged; #21 + #23 post-hoc PASS; merged user-directed
  #18 (top-100+5m, §43) after a rebase. Flagged #25/#26/#19 as residual low-risk un-gated
  debt. Reports: `docs/audits/pr-{21,23,24}-audit.md`. Next scope: deploy + verify the
  dashboard on Render.
- 2026-06-15: PR #29 (`claude/site-trade-demo`) — WEBSITE chat (front-end only). New
  animated "trade story" hero (W-sweep, PVSRA vector candles, daily-open/psych levels,
  5-agent thinking/notes → 3R bracket; illustrative, reduced-motion + mobile aware) +
  mobile/sitemap/font sweep + homepage font-cache-poisoning fix + removed the public
  "uvicorn …" dev-message leak on live-signals/trade-flow. Verified via headless
  screenshots; suite green. AWAITING_AUDIT. Also observed: first post-#18 paper run #50
  succeeded (+83 setups, 27 on 5m). Next scope: audit #29, then resume Render deploy+verify.
