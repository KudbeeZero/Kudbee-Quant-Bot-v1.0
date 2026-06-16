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
- **This chat = the TRADE-SETUP chat.** Branch `claude/trade-setup-entry-vfkn7m` (off
  `main`). It did a **confluence-engine change + manual trade tickets**: flipped the VWAP
  vote to rotation/mean-reversion and logged 5 discretionary tickets to a new manual
  board. See "What this chat did" below.
- **Last PR:** **#31** — `claude/trade-setup-entry-vfkn7m`, **MERGED by the user**
  2026-06-16 (4-file diff). https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/31
- **Audit status:** `MERGED (post-hoc PASS)` — #31 was merged from DRAFT by the user
  without a pre-merge gate, so it was **audited post-hoc this session** (independent
  subagent; report `docs/audits/claude-trade-setup-entry-vfkn7m.md`). Verdict **PASS**:
  all claims back-checked against the real base→head diff, **341 tests pass**, no scope
  creep, no sneaked-in change to the §1 defaults (only the single VWAP sign moved), A/B
  script read-only/clean, and §44/baton honestly flag the live-but-unvalidated risk. The
  open risk in §44 stands as the documented fix-forward (OOS-validate or revert the flip).
- **Prior chat's PR also merged:** **#29** (WEBSITE, front-end only) merged 2026-06-15 by
  the user — the baton had it `AWAITING_AUDIT`, but it is on `main`; no audit was recorded
  (low-risk front-end-only; optional post-hoc back-fill). **#27/#28** ledger/audit PRs also
  live.
- **🎯 MILESTONE (paper §43 experiment):** the first post-#18 hourly run **#50**
  (2026-06-15) succeeded (~5m32s, +83 setups incl. 27 on 5m). The §37 5m-fee-drag concern
  is under live forward test — watch the resolving setups; revert to top-10/no-5m if 5m
  re-confirms §37. **NOTE:** the merge of #31 put the **VWAP rotation flip (§44) LIVE** in
  this same hourly bot — its setups are now generated with the flipped sign.
- **Open PRs now:** the **closeout/baton PR for this chat** (just opened — baton + MEMORY
  §44 only, no engine change). Nothing else open.

## What this chat did (for the auditor to verify against the diff)

A small **confluence-engine change + manual trade-tracking**, plus this closeout. The
merged #31 diff is 4 files: `kudbee_quant/confluence/stack.py`, `docs/MEMORY.md`,
`scripts/compare_vwap_rotation.py`, `docs/OPEN_SETUPS.md`. The closeout PR on top adds
only `docs/MEMORY.md` (§44) + `docs/HANDOFF.md`.

- **VWAP vote flipped to ROTATION (mean-reversion)** — `kudbee_quant/confluence/stack.py`:
  `v_vwap = −sign(close − vwap)` (was `+sign`). Above VWAP now votes short, below votes
  long. Polarity flip of an existing default vote, not a new factor. In-code NOTE flags it
  for OOS re-validation. **MEMORY §44.**
  - ⚠️ **Honesty / open risk:** this is an **unvalidated change to a §1-validated default**,
    now LIVE in the hourly paper bot (user merged the draft). The A/B screen
    (`scripts/compare_vwap_rotation.py`) showed the blanket flip **HURTS on majors**
    (momentum +197% gross / rotation −51% gross, per-bar zero-fee). The narrower idea the
    user actually described (daily-open read AND below-VWAP → 2× long size) was NOT tested.
- **`scripts/compare_vwap_rotation.py`** — one-off offline A/B (real `load_ohlcv` +
  `build_levels` + `factor_votes` + `run_backtest`); recovers both momentum and rotation
  nets from one vote pass. Run: `PYTHONPATH=. python scripts/compare_vwap_rotation.py`.
- **`docs/OPEN_SETUPS.md`** — new **manual** discretionary tracking board (GOOGL / HYPE /
  COMP / DEGEN / ETH longs; $100 = 1R; TP1 1.5R / TP2 2.8926R). **NOT read by the bot**;
  separate from `data/journal.json`.
- **`docs/MEMORY.md`** — added two STANDING USER PREFERENCES (trade the zero-fee venue /
  stop re-raising fees on positive results; don't over-caution on the research sandbox)
  and §44 (the VWAP flip + the assessment of the shared Crawlee/latency/cluster PDF).
- **Verification:** `python -m pytest -q` → **green (exit 0)** at closeout. No test
  asserts the VWAP vote's direction, so the flip moved nothing else mechanically.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/cluster-analyzer`.
- **AUDITS ALREADY DONE this session** (no `/handoff-audit` needed at next start): **#31
  post-hoc PASS** (`docs/audits/claude-trade-setup-entry-vfkn7m.md`); the closeout/baton
  PR **#32** was the vehicle. #29 (website) is merged — optional low-risk back-fill only.
  So the next chat can go **straight to the priority scope below.** (Still worth a glance:
  whether #32 actually merged to `main` — if not, sync it first.)
- **PRIORITY SCOPE (user-chosen this session): build the losing-cluster analyzer.** A new
  analysis unit that reads the live `data/journal.json` and tests whether **losing trades
  cluster** by **time-of-day**, **confluence strength/score at entry**, and **ATR/volatility
  regime** — i.e. is a losing streak a *regime mismatch* or just normal variance? Reuse the
  existing significance-gated study harness (`kudbee_quant/events/study.py`
  `conditional_table`, Wilson CIs + FDR — same machinery as `confluence_directional_study`
  in `confluence/stack.py`). This is the ONE applicable idea from the Crawlee/latency PDF
  the user shared (§44); the latency/Crawlee/data-feed-benchmark parts do **NOT** apply to
  this bar-close price-action bot — do not build them. Output should be a report (a CLI
  sub-command or `scripts/` analysis), read-only over the journal; **must not write
  `data/journal.json`**. Frame findings honestly (significance-gated; small-n caveats).
- **Watch (paper §43):** the hourly run resolving setups — incl. now the VWAP-rotation
  ones (§44); check next runs for timeouts / Binance rate-limits and whether 5m setups
  resolve net-negative (fee drag, §37) → revert top-100/5m if so.
- **Scope (deferred, still open):** **Deploy + verify the dashboard (PR #21) on
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
  - **🚩 VWAP ROTATION FLIP IS LIVE & UNVALIDATED (§44, PR #31):** the VWAP vote was
    flipped momentum→rotation and merged into `main`, so it's now shaping the hourly paper
    bot's setups. The A/B screen says the blanket flip HURTS majors. It is NOT OOS-validated
    and is an unvalidated change to a §1 default. Either validate it on the bracket harness
    or test the narrower conditional (daily-open + below-VWAP → 2× long) the user actually
    described; be ready to revert the sign if the live/OOS read confirms it hurts.
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
  screenshots; suite green. **Merged by the user 2026-06-15 (no audit recorded).**
- 2026-06-16: PR #31 (`claude/trade-setup-entry-vfkn7m`) — TRADE-SETUP chat. Flipped the
  VWAP confluence vote momentum→ROTATION (mean-reversion); added an offline A/B screen
  (blanket flip HURTS majors per-bar) + a manual `docs/OPEN_SETUPS.md` board (5 longs) +
  MEMORY standing prefs & §44. **Merged from DRAFT by the user (serial audit gate skipped)
  → rotation sign is now LIVE in the hourly paper bot, UNVALIDATED (open risk, §44).** Also
  assessed a shared Crawlee/latency/cluster PDF: only the losing-cluster idea applies here.
  Closeout opened a docs-only baton PR. Next scope: **build the losing-cluster analyzer**
  (read `data/journal.json`; regime vs variance) — post-hoc audit #31 first.
