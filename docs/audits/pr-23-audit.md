# PR #23 audit — Cycle-aware OOS backtest (affirm the live 1h config; min_pct 0.6 refuted OOS)

- **Verdict:** **PASS** (post-hoc — PR was merged from the UI before this gate ran)
- **Date:** 2026-06-15
- **Auditor:** independent `general-purpose` subagent (arm's-length; verified the diff + the result JSONs, not the claims)
- **PR:** [#23](https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/23) — **MERGED** by KudbeeZero at `d40886e`
- **Range audited:** `605d594..d40886e` (base.sha..head.sha; the PR merged `origin/main`/PR #20 into itself, so the audit focused on the net new work)
- **Tests:** `python -m pytest -q` → **322 passed**, 0 failed (1 warning).

## Why this is a post-hoc record
Like PR #21, PR #23 was merged from the UI during the user-directed cleanup, without the
independent gate. This is the owed arm's-length review. Verdict is PASS, so nothing to
fix-forward — but the statistical caveats below MUST travel with any quote of the result.

## Findings (each with diff / data evidence)

### Engine fidelity — VERIFIED (critical)
- `scripts/cycle_backtest.py:47-57` imports `STOP_ATR, TARGET_R, MAX_BARS, RETRACE_ATR, ENTRY_WINDOW, MIN_PCT, TREND_FILTER` from `config/validated_defaults.py`, passes them via `LIVE_BRACKET` into `bracket_backtest(...)` (line 95); signal is `confluence_position(min_pct=MIN_PCT, trend_align=TREND_FILTER)` (190-191).
- `validated_defaults.py:12-23` confirms these resolve to `min_pct=0.50, stop_atr=1.5, target_r=3.0, limit_retrace_atr=0.25, max_bars=24, entry_window=6` — the canonical live rules, NOT engine defaults. The persisted `config` block in `data/cycle_backtest_results.json` matches.
- The report (`cycle_backtest.md:195-199`) honestly self-distinguishes from the prior `near_miss_oos.py`, which used the bad default market-entry/1.0-stop path.

### Headline numbers — VERIFIED, not fabricated
- Read directly from JSON: overall maker exp `−0.018626R` (→ −0.019), n=137,326, boot_p=1.000; **1h maker `+0.09583R` (+0.096), n=8,124, boot_p=0.0; 1h taker `+0.06012R` (+0.060)**.
- 5m share = 70.9% (`97417/137326`) — supports "71% 5m-dominated". All match `cycle_backtest.md:29-34,77-79,120-135`.

### min_pct 0.6 REFUTED OOS — VERIFIED
- `data/cycle_backtest_matrix.json` gate_1h: 0.5→0.6→0.7 maker = +0.096→+0.040→+0.005 (monotone down); every scope worse at 0.6; **w2022 flips negative** at 0.6 (+0.043→−0.020 maker, +0.019→−0.045 taker). Matches report §5c / verdict §6–7.2.

### No live-config change — VERIFIED
- Diff touches only 9 files (2 data JSONs, 3 docs, `binance.py`, 2 scripts, 1 test). No `validated_defaults.py`, `paper.py`, `api.py`, `data/journal.json`, `data/alert_inbox/`.
- `klines_range()` in `binance.py:115-164` is purely additive (zero `-` lines on existing code; existing `klines()` untouched), reuses `_get_klines`/`_MAX_LIMIT`/`validate_ohlcv`, and has a no-network unit test (`tests/test_ingest.py:49-105`) covering forward-paging, dedup, gap-free, cache reuse.

### Statistical honesty — VERIFIED
- Bootstrap p computed in code, not asserted: `cycle_backtest.py:126-133` (5000-iter one-sided, seeded) + `cycle_backtest_matrix.py:66`. p-values are real resampled outputs.
- Fee modeling correct: maker `0.0004`=0.04%, taker `0.0009`=0.09% round-trip (`cycle_backtest.py:57`), converted to R per-trade by the engine via `fee_pct` (tiny 5m stops correctly cost more R). Consistent with MEMORY §25.
- Caveats present, no over-claim: 2018 universe limit (BTC/ETH/BNB/ADA/XRP) at `cycle_backtest.md:22,320-321`; chop-analog 1h small-n (450/951) flagged low-confidence (§6 142-149, §7.5); verdict says "regime-dampened, not regime-broken." 15 gappy 2018 cells honestly reported. No favorable number quoted without its caveat.

### MEMORY numbering — NO collision
- On disk: §40 = dashboard (PR #21), §41 = cycle backtest (`MEMORY.md:1260`). The commit said "§40" but the closeout correctly renumbered to §41 after the #20 merge; matches the baton reconciliation and disk exactly.

### Scope — CLEAN
All changes serve the OOS backtest + the additive date-range ingest it requires.

## Caveats carried forward (must travel with any quote of this result)
- The pooled **"overall −0.019R" is a 5m artifact** (71% of trades) — never quote without the 1h context (+0.096 maker / +0.060 taker, n=8,124).
- **Chop-analog 1h samples are small** (2018 n=450, 2022 n=951) → "survives chop" is positive-but-low-confidence, not proven.
- **1h net-taker cushion is thin** (~+0.02–0.06R) → size conservatively.
- Result JSONs were not regenerated during the audit (the run hits the live Binance public API), but the persisted `config`, n-counts, and exp/boot_p are internally consistent with the script + report, with no flattering rounding.

## Settled question (record the closure)
- `--min-pct 0.6` is answered **NO — keep 0.5**. 0.6 lowers net expectancy in every regime OOS and flips the 2022 chop analog negative; 50% is the best 1h band. Remove from the pending list (MEMORY §41). No further shadow-test needed.
