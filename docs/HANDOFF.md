# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **⚙️ SERIAL RULE (2026-06-15, user-set):** all implementation work is strictly serial
  — **finish the unit → open ONE PR → audit → merge → only then start the next unit**;
  only one PR open at a time; no new implementation while a PR is open or awaiting audit.
  Purely *observational* background tasks are exempt. (This chat added more units onto the
  one open PR #35 at explicit user direction — noted honestly for the auditor.)
- **This chat = the RESEARCH + REPORT chat.** Branch `claude/trade-data-pull-9ympy0`
  (off `main`). All **read-only / additive**: two journal-research units, a paper-forward-
  test framework, and a hosted investor report. **No engine / journal / live-path change.**
- **Last PRs:** **#35** (research + report) **and #36** (Tier-2 entry-fill, §47) — both on
  `claude/trade-data-pull-9ympy0`, **both MERGED to `main` this session** (user-directed
  direct merges, like #29/#31). #35 https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/35
  · #36 https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/36
- **Audit status:** `MERGED — POST-HOC AUDIT PENDING`. Next chat's `/handoff-audit` should
  post-hoc review **#35 + #36** (already on `main`; both carry an audit checklist in their
  PR body). All read-only/additive (studies + static report + one backward-compat lib add);
  scope was checked clean pre-merge (no §1/`FEE_PCT`/`bracket.py`/`resolver.py`/journal edits).
- **Prior:** #31 merged (post-hoc PASS, §44 VWAP rotation flip is LIVE & unvalidated —
  still an open risk below). #27/#29 also merged. No other open PRs.
- **🎯 Paper §43 experiment still running** (hourly Action, top-100 + 5m, VWAP-rotation
  sign live). `main` advanced this session via the bot's `data/journal.json` (merged in).

## What this chat did (for the auditor to verify against the diff)

PR #35 = **13 files** (plus the merged-in `data/journal.json` from `main`). Test suite
**green (363 passed)** at closeout. Two read-only research units + forward-test + report:

- **Losing-cluster analyzer** — `kudbee_quant/cluster.py` (+ `losing-clusters` CLI in
  `cli.py`, `tests/test_cluster.py`). Read-only over the journal; "do losers cluster by
  context or is it variance?" via the significance-gated `conditional_table` (Wilson + FDR).
  **Null = the book's own win rate, not 0.5** — added backward-compatible `null_rate` to
  `StudyConfig` (default 0.5 ⇒ existing `confluence_directional_study` unchanged; verify).
  `vol_regime` is a labelled ATR-proxy (stays offline). **MEMORY §45.**
- **Leverage / break-even viability study** — `scripts/leverage_be_study.py` +
  `docs/research/leverage_be_study.md` + per-trade `leverage_be_trades.csv` (497 rows).
  Read-only; re-fetches each trade's post-fill bar path. **Verdict: 50x = ruin (55% liq);
  edge only marginal at `lock+0.1R@first_green`, ≤10x, zero-fee/maker. MEMORY §46.**
- **Paper-forward-test framework** — `docs/research/leverage_be_forward_test.md` (design,
  two gated tiers) + **Tier-1 shadow overlay** `scripts/leverage_be_shadow.py` (read-only;
  reuses the study engine; writes ONLY to gitignored `data/shadow/`, never the journal;
  pre-registered PASS/INCONCLUSIVE/KILL). `.gitignore` += `data/shadow/`.
- **Hosted investor report** — `leverage-report.html` (CSS-only, CSP-safe; real figures;
  no live-edge claim), featured from `lab.html`, added to `sitemap.xml`. Canonical + OG
  set to **report.kudbeequant.com**; indexable. Deploys via the existing Cloudflare Pages
  pipeline (preview live now; production needs a `main` merge + a custom-domain attach).
- **Honesty flags:** Tier-1's *positive* lane (crypto, n=314, PASS) **assumes maker fills
  we have NOT proven**; the genuinely zero-fee lane is n=25 → INCONCLUSIVE. The whole
  positive case hinges on Tier-2 maker-fill feasibility (§42). Report states this plainly.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/leverage-tier2`.
- **AUDIT FIRST (post-hoc):** run `/handoff-audit` to review **#35 + #36** (already on
  `main`). Confirm against the diff: no change to §1 defaults / `FEE_PCT` / `bracket.py` /
  `resolver.py`; `data/journal.json` not hand-edited (only the `main` merge); read-only
  scripts write nothing outside gitignored `data/shadow/`; `StudyConfig.null_rate` default
  preserves the old study; tests green.
- **Tier-2 entry leg DONE (§47):** maker ENTRY fill rate **86.6%** (read-only from the
  journal's filled-vs-cancelled record) — clears the <60% kill. **REMAINING Tier-2 work:**
  (a) **re-rate the candidate net with maker-ENTRY + taker-EXIT** (the BE/stop exit is taker
  on crypto; the study's "low/maker" model assumed both-maker, so it under-charges crypto) —
  a quick read-only re-run of `leverage_be_study`'s friction with an asymmetric model; (b) a
  live **`BINANCE_TESTNET` micro-stake** confirmation that paper fills hold on a real venue.
  Only THEN can the `lock+0.1R/≤10x/maker` candidate graduate — and even then micro-stake only.
- **GO-LIVE (user-side, the ONLY remaining manual step):** report is MERGED + live at the
  production URL `https://kudbee-quant-bot-v1-0.pages.dev/leverage-report.html`. To use the
  custom domain: Cloudflare → Workers & Pages → `kudbee-quant-bot-v1-0` → Custom domains →
  add `report.kudbeequant.com` (canonical already set). No code step left.
- **Open risks / watch-items (still live):**
  - **🚩 VWAP ROTATION FLIP IS LIVE & UNVALIDATED (§44, PR #31):** shaping the hourly bot's
    setups; A/B says the blanket flip HURTS majors. Validate on the bracket harness or test
    the narrower conditional (daily-open + below-VWAP → 2× long); be ready to revert.
  - **Paper §43 watch:** hourly run resolving setups (top-100 + 5m incl. rotation sign) —
    check timeouts / Binance limits / whether 5m resolves net-negative (§37) → revert if so.
  - **§42 maker fee is an ASSUMPTION** (0.0002/side, unconfirmed pending a real LIMIT fill)
    — and it is exactly what Tier 2 must settle before the leverage rule can graduate.
  - **Dashboard (PR #21) UNVERIFIED in production** (Render deploy still deferred).
  - **lock+0.1R rule is a PAPER CANDIDATE, not validated** — do not enable live; micro
    stake only even after Tier 2, never full-account risk.
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; the live execution path
  (`bracket.py`/`resolver.py`) — do NOT change entry on the strength of this research.
  `data/journal.json` (bot-owned — no session commits); `data/shadow/` (overlay output —
  gitignored, don't commit); `data/alert_inbox/` (host/Action-owned). Keep PR #20 flags OFF;
  hold the parsimony line; paper-scan stays `dry_run=True`; curated runner stays a fixed
  whitelist; don't casually rework the session-cookie scheme. **No market/hybrid execution
  flip (§42 dead end); keep maker retrace, 5m paper-only, `min_pct` 0.5.** Keep the report's
  honesty — **no live-edge / returns claims** on the public page.

## Baton history
- … (prior entries in git) …
- 2026-06-15: PR #21 — gated admin/investor dashboard (local-only verification). Merged.
- 2026-06-15: PR #23 — cycle-aware OOS backtest (137k trades); `min_pct 0.6` refuted → keep
  0.5; 5m dead, 15m maker-only. Merged.
- 2026-06-15: PR #24 — execution head-to-head; maker retrace wins every TF; market a dead
  end (§42). Merged.
- 2026-06-15: PR #27 — handoff-audit gate-the-backlog (#24 PASS→merged; #21/#23 post-hoc).
- 2026-06-15: PR #29 — WEBSITE chat (front-end trade-story hero + sweeps). Merged.
- 2026-06-16: PR #31 — TRADE-SETUP chat; VWAP momentum→ROTATION flip (LIVE, unvalidated,
  §44) + manual `OPEN_SETUPS.md` board. Merged from DRAFT by the user.
- 2026-06-19: PR #35 (`claude/trade-data-pull-9ympy0`) — RESEARCH + REPORT chat. Losing-
  cluster analyzer (§45) + leverage/BE viability study (§46) + paper-forward-test framework
  (Tier-1 shadow overlay, pre-registered) + a hosted investor report (`leverage-report.html`
  → report.kudbeequant.com, indexable, linked from the Lab). All read-only/additive; 363
  tests green. **Merged to `main`** (user-directed).
- 2026-06-19: PR #36 (same branch) — Tier-2 maker ENTRY fill feasibility (read-only, §47):
  86.6% fill rate from the journal's filled-vs-cancelled record → PASS the <60% kill; added
  report Finding 4. Merged. **Both #35 + #36 post-hoc-audit pending.** Next scope: finish
  Tier-2 (taker-exit re-rate + testnet micro-stake); user-side: attach `report.kudbeequant.com`.
