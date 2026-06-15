# Audit — PR #18 (top-100 universe + 5m re-enabled on the hourly Action)

- **Verdict:** `CONCERNS` (change is safe + honest, but (1) does not merge cleanly — MEMORY §39 collision; (2) runs against §37/§31 — needs explicit user go)
- **Date:** 2026-06-14 (gated by `claude/handoff-audit-h90pmc`)
- **PR:** [#18](https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/18) — "feat(scan): top-100 universe + 5m re-enabled on the hourly Action (user-directed §39)"
- **State at audit:** OPEN (not merged)
- **Branch:** `claude/scan-top100-5m`
- **Diff audited:** `376be66..5717a8d` (base→head); base predates current `main` (`0244ba0`).

## What it changes
- `.github/workflows/paper-trade.yml` — crypto scan switches from the 10 hard-coded majors to `universe_specs()` (~101 pairs from `config/crypto_universe.yaml`) and adds `5m` back to `--intervals` (now `5m 15m 1h 2h 4h --trend-filter`). TradFi book unchanged (1h only).
- `docs/MEMORY.md` — adds a §39 entry describing the flip.

## Findings
- **Scope clean** — only the workflow + MEMORY; **no** `validated_defaults.py` (§1), **no** `FEE_PCT`/`TAKER_FEE_PCT`, **no** `data/journal.json` / `data/alert_inbox/`, no library code. ✅
- **Loader resolves** — `universe_specs()` returns **101** valid string specs (`BTCUSDT…`); the command substitution is sound. ✅
- **Honesty** — the workflow comment and the MEMORY entry explicitly state this runs **against our own evidence** (§37 5m fee drag, §31 unproven top-100 tail) and is a **paper forward experiment**, not a validated config. No over-claim. ✅
- **BLOCKER — MEMORY §39 numbering collision** — current `main` already has `## 39. New-signals audit` (from merged PR #20). #18 adds a second `## 39. Hourly scan flipped to TOP-100…`. `git merge-tree` confirms **MEMORY.md conflicts** on merge. #18 must be **renumbered to §40** and the conflict resolved before it can land. ❌
- **Judgment concern (not a code defect)** — §37 (5m net-negative purely on fees) has now been **re-confirmed three times** (PR #17 near-miss autopsy, PR #19 vector-candle study, PR #20's 60%-band/OOS work). Re-enabling 5m + flipping to the unproven top-100 tail is defensible *only* as a paper data-gathering experiment. Operational load: ~100 symbols × 5 TF/hour ≈ ~50× the prior API/`build_levels` load — watch Action runtime/timeout, Binance rate limits, and bot-journal growth. User-directed, so this is the user's call to confirm.

## Recommendation
Do **not** auto-merge. The change itself is safe (paper, scoped, honest), but (a) it can't merge cleanly until its MEMORY entry is renumbered §39→§40 and the conflict resolved, and (b) it knowingly contradicts repeatedly-confirmed evidence, so it needs the user's explicit go. If the user confirms: renumber to §40, resolve the MEMORY conflict, merge; add a revert note to watch the next hourly run for timeout/fee drag.

## Self-audit caveat
Audited in-session (not a fully independent worktree subagent, given the one-file workflow diff); diff, scope, loader, and merge-conflict checks were run directly against the real SHAs.
