# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/confluence-r-cycle-backtest-eg45m1`
- **Last PR:** #23 — https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/23
  (cycle-aware OOS backtest; offline only, no live change).
- **Audit status:** `AWAITING_AUDIT`.
- **NOTE — two PRs awaiting audit:** **PR #20** (new entry signals) is ALSO still
  `AWAITING_AUDIT` (not yet merged). The next chat should `/handoff-audit` **both,
  oldest first (#20 then #23)**. #23 merged `origin/main` (incl. #20's work) for a
  current base, so its diff is cycle-backtest-only.
- Prior PRs CLOSED OUT: #14 (post-hoc CONCERNS), **#16**, **#17**, #19 all MERGED
  to `main`. Gate streak: #5,#6,#7,#9,#11,#12,#13,#14,#16,#17.

## What this chat did (for the auditor to verify against the diff)

- **Cycle-aware OOS backtest of the live confluence-R rules (PR #23)** — scored the
  EXACT live config (`confluence_position(min_pct=0.5, trend_align=True)` +
  `BRACKET_KW`: stop_atr=1.5, target_r=3.0, limit_retrace_atr=0.25, max_bars=24)
  over two prior-cycle CHOP analogs (2018-07/10, 2022-05/08 — the ~786-day-post-
  halving phase we are in) + a recent span (2024-06→now), at 5m/15m/1h. Params
  frozen (never refit) → all three regimes OOS. Fees modeled gross→full-taker.
  **Offline only; §1/`FEE_PCT`/journal/alert_inbox untouched.**
  - **137,326 resolved OOS trades** (8,124 on the validated 1h TF alone).
  - **1h: +0.096R net-maker / +0.060R net-FULL-taker, n=8,124, p<0.001** — positive
    & taker-survived. 15m maker-only (dies at taker). 5m net-dead in every regime
    (vindicates the §37 pause). The pooled "overall −0.019R" is 71% 5m — context-only.
  - **Survives the current regime** (recent 1h strongest, +0.102/+0.064); **survives
    the chop analogs but thinner & LOW-CONFIDENCE** (2018 n=450, 2022 n=951).
  - **`min_pct 0.5→0.6` REFUTED OOS in every regime** (50% band is the best 1h band;
    0.6 flips the 2022 chop analog negative) — closes the pending autopsy tweak.
  - NEW `BinanceClient.klines_range()` (forward-paging date-window fetch, disk-cached;
    additive). `scripts/cycle_backtest.py` + `scripts/cycle_backtest_matrix.py`;
    report `docs/research/cycle_backtest.md`; MEMORY §40. 305 passed; ruff clean.

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/close-min-pct-decision` — harness assigns
  the real name; the *scope* below is what binds.
- **Scope (user-chosen 2026-06-15):** **Formally CLOSE the `--min-pct 0.6` decision —
  keep 0.5.** PR #23 gives the OOS answer: raising the floor 0.5→0.6 LOWERS net-of-
  fees expectancy in every regime and flips the 2022 chop analog negative; the 50%
  band is the best 1h band. So the long-pending tweak is settled: **do NOT raise the
  gate, do NOT shadow-test it — keep `MIN_PCT=0.50`.** Record the closure (MEMORY +
  remove it from the pending list); no live-config change. Lightweight chat.
- **AUDIT FIRST:** `/handoff-audit` PR #20 then PR #23 before any new work.
- **Also queued (unchanged):** Signal #4 (OI + liquidation-cluster levels — data-
  availability risk: OI hist ≈ 30d, liquidation history restricted); wire the live
  executor (PR #16) into a CLI / hourly Action via `BINANCE_TESTNET=true` smoke-test;
  top-100 universe flip decision; verify the 5m pause landed in production (§37);
  live deploy walkthrough once the Render service exists (`docs/HOSTING.md`).
- **Open risks / watch-items:**
  - **2018 cycle-analog universe limited to 5 coins** (BTC/ETH/BNB/ADA/XRP — the
    others weren't listed yet); 2022 + recent use all 10. 15 cells had a single
    1-candle 2018 gap (negligible). The chop-analog 1h samples are SMALL (450/951)
    and not individually significant — "survives chop" is positive-but-low-confidence.
  - **Don't quote the pooled "overall" net-negative without the 1h context** — it's
    a 5m artifact (71% of trades), not a verdict on the live book.
  - **PR #20 signals NOT validated for live use** (delta_align & killzone FAIL OOS;
    volume-profile inconclusive; meta-lift near noise) — keep flags OFF, forward-test.
  - **PR #20 still AWAITING_AUDIT** alongside #23 — audit both.
  - **Live execution EXISTS but UNPROVEN live (PR #16):** maker-only, double-gated,
    never placed a real order. Paper still default. Start testnet.
  - **Top-100 membership UNPROVEN forward (§31);** **5m pause UNVERIFIED in prod (§37);**
    **deployment UNPROVEN** (render.yaml + inbox local-only); **possible 1h edge decay
    (§36/§37)** — re-check as data accrues.
  - **Branch deletions pending (§32):** handoff-audit-*, hello-*, overnight-*,
    sol-short-*, fable-5-*, zcash-* set (safe via GitHub UI).
  - **§33** replay pct ≠ live-edge pct; **§29/§30** maker-vs-taker fee open item
    (one real LIMIT fill settles it).
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`; `data/journal.json`
  (bot-owned — no session commits); `data/alert_inbox/` (host+Action-owned — no
  manual session commits); crypto daily grouping stays calendar-dated; held salvage
  branches only with explicit user OK. Keep PR #20's feature flags + filters OFF
  until forward-validated; hold the parsimony line (no removed vote back as a vote).

## Baton history
- … (prior entries in git) …
- 2026-06-14: PR #20 — new entry signals (taker delta/CVD, volume profile, killzone
  gate), opt-in/default-OFF, independently validated; honest negative; 60% band
  confirmed net-positive OOS. Next scope: Signal #4 (OI + liquidation levels).
- 2026-06-15: PR #23 — cycle-aware OOS backtest (137k trades). Live 1h config is
  net-positive & full-taker-survived in all 3 regimes; 5m dead, 15m maker-only;
  `min_pct 0.6` refuted OOS. Affirm live config, no change. Next scope: formally
  close the `--min-pct 0.6` decision (keep 0.5).
