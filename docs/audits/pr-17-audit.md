# PR #17 audit — near-miss autopsy + OOS scenario re-sim (research)

- **Verdict:** `PASS` (independent, arm's-length subagent — same-session self-audit,
  user-invoked via `/handoff-audit`; caveat below).
- **Date:** 2026-06-14
- **PR:** [#17](https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/17) —
  "research: near-miss autopsy + OOS scenario re-sim (live config untouched)"
- **PR state at audit:** `OPEN`, `mergeable_state: clean`. Head
  `claude/near-miss-autopsy`, base `main`. 4 new files.
- **Auditor:** `general-purpose` subagent in an isolated worktree; **re-ran the autopsy
  script with live network** and reproduced the results.

## Findings (all PASS)

- **No live-config change.** Diff touches only 4 new files; no `.yml`/`.yaml`, no
  `validated_defaults.py`. The `--min-pct 0.6` change appears ONLY as a proposed fenced
  diff in `docs/research/near_miss_autopsy.md` — applied nowhere. (Live `paper-trade.yml`
  has no `--min-pct` flag and already runs `--trend-filter`.)
- **Forbidden paths clean.** No edit to `data/journal.json` or `data/alert_inbox/`; the
  new `data/excursion_audit.json` is an allowed analysis artifact.
- **Replay fidelity ≥ claimed.** `near_miss_autopsy.py:96` reuses the shared
  `backtest.resolver.resolve_bracket` (not a re-implementation). Auditor's live run:
  `replayed OK: 118`, **reconcile @3R 118/118 (100%)** — the doc conservatively says
  99/100 (under-claim). Artifact byte-identical / deterministic.
- **IS vs OOS separated; OVERFIT driven by OOS.** §2 (in-sample) and §3 (out-of-sample
  walk-forward) are distinct; the OVERFIT verdict comes from the OOS table via the real
  engine (`confluence_position` + `walkforward_bracket`, scoring only sufficient folds).
- **Numbers spot-check.** Band parsing `confluence_r_(\d+)pct`; artifact has 118 rows
  with `mfe_r`/`mae_r` + `swept_gross_r`; every doc near-miss row matches the data; the
  in-sample tables (drop-60% −16.0 vs −54.4 baseline; adaptive −40.9) reproduced.
- **Ruff** clean on both scripts. **Overclaim check:** recommendation honestly caveated
  ("55% supportive but not overwhelming … shadow-test before committing … NOT applied").

## Note acted on
- The auditor flagged that §1's near-miss table was filtered to 60%-band rows while the
  single largest-MFE near-miss overall is a 70%-band BNB 5m (+9.67R). Real data, but
  selectively presented → a clarifying line was added to §1 (and this artifact pointer)
  so the filtering is explicit. Non-blocking; honesty improved.

## Caveat (independence)
Same-session self-audit (authoring chat, user-invoked gate); independence via the
arm's-length subagent that re-ran the analysis in an isolated worktree. Research PR with
no live-trading impact, so blast radius is low regardless.
