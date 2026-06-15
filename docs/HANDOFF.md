# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/execution-backtest-maker-market-d96f9x`.
- **Last PR:** **#24** — execution head-to-head (maker-retrace vs market vs hybrid,
  OOS, net of fees). https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/24
- **Audit status:** `AWAITING_AUDIT` — PR #24 (DRAFT) not yet gated. Merged current
  `main` (the #21 dashboard + #23 cycle-backtest); resolved the `MEMORY.md` §41
  collision (#23 kept §41; **this chat is §42**); suite re-run green (**328 passed**).
- **Prior un-gated debt still open:** #21 (dashboard) and #23 (cycle backtest) were
  merged to `main` at the user's instruction **without** an independent
  `/handoff-audit`. Both had green CI + full local suite but no arm's-length audit.
  **Recommend post-hoc `/handoff-audit` on #21 and #23** (`docs/audits/pr-21-audit.md`
  / `pr-23-audit.md`). They are NOT part of the verified gate streak.
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

## What this chat did (for the auditor to verify against the diff)

- **Execution head-to-head (PR #24, OFFLINE research)** — does a MARKET order at the
  signal beat the live 0.25-ATR maker retrace? Tested on the SAME OOS sample, ALL
  timeframes. **Live trading path untouched** — `bracket.py`/`resolver.py` NOT edited.
  - New **isolated** module `kudbee_quant/backtest/execution_modes.py`: market entry =
    fill at OPEN of T+1 (no lookahead); per-leg fees (taker IN + on stop/time-stop,
    maker on resting limit fills + targets); adverse-selection resolver; bootstrap p.
    Reuses the shared `resolve_bracket`. +6 unit tests (`tests/test_execution_modes.py`).
  - `scripts/execution_backtest.py` — fetch 5m + resample to 15m/1h, run A/B/C ×
    {5m,15m,1h} × {2018_chop, 2022_chop, recent}. Results
    `data/execution_backtest_results.json`; writeup `docs/EXECUTION_BACKTEST.md`;
    MEMORY **§42**.
  - **VERDICT:** the CURRENT maker retrace (A) wins net-of-fees on every TF and all 9
    regime cells (1h **+0.1265R**, p=0.000; market is worst everywhere; market makes 5m
    WORSE, not better). Cancelled signals ARE the runners (anti-selection confirmed,
    p=0.000) but blanket market entry can't harvest it (variant B loses) and the figure
    is selection-biased. **No live change recommended.**
  - Suite **328 passed** (+6 new); new files ruff-clean. §1 / `FEE_PCT` / journal /
    `alert_inbox` untouched; no secrets.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/handoff-audit-gate`.
- **Scope (user-chosen 2026-06-15):** **Gate the open PR backlog.** Run
  `/handoff-audit` on **PR #24** first (it's a DRAFT — review diff vs. claims, the
  no-live-change guarantee, the per-leg fee model, the adverse-selection bias caveat;
  merge only on PASS). Then clear the un-gated debt: post-hoc `/handoff-audit` on **#21**
  (dashboard) and **#23** (cycle backtest), writing `docs/audits/pr-{21,23}-audit.md`.
  (#20 is already audited PASS — re-confirm only if desired.)
- **Then queued (prior baton, deferred):** deploy + verify the dashboard on Render
  (`docs/HOSTING.md`); decide #18 (live top-100+5m) yes/no; back-fill a #19 audit note.
- **SETTLED — record the closure (PR #23 §41 + corroborated by PR #24 §42):** the
  `--min-pct 0.6` question is answered **NO, keep 0.5**. No more shadow-test needed.
  ALSO settled (§42): **market/hybrid execution is a DEAD END** — do not re-test blanket
  market or next-bar-open entry; the maker retrace wins on every TF.
- **Also queued:** wire the live executor (PR #16) into a CLI / hourly Action via a
  `BINANCE_TESTNET=true` smoke-test (`docs/LIVE_TRADING_SETUP.md`); Signal #4 (OI +
  liquidation-cluster levels — data-availability risk: OI hist ≈ 30d, liquidation
  history restricted); verify the 5m pause landed in production (§37).
- **Open risks / watch-items:**
  - **PR backlog UN-GATED (the user's flagged risk):** #24 (this, AWAITING_AUDIT),
    plus #21 + #23 merged without an independent audit; #18 still held. Gate before
    new feature work.
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
