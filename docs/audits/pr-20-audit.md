# Audit — PR #20 (new entry signals: taker delta / volume profile / killzone)

- **Verdict:** `PASS`
- **Date:** 2026-06-14 (gated start-of-chat by `claude/handoff-audit-h90pmc`)
- **PR:** [#20](https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/20) — "New entry signals (opt-in, default OFF): taker delta/CVD, volume profile, killzone gate — independently validated"
- **State at audit:** OPEN
- **Branch:** `claude/confluence-new-signals-audit-a6gxt6`
- **Diff audited:** `ada8345..8858ba8` (two-dot, base→head SHAs)
- **Method:** independent arm's-length subagent in an isolated git worktree (no authoring-chat context); diff-vs-claims, local test + ruff re-run, hand-verified default-OFF invariance.

## Test & lint (reproduced by the auditor)
- `python -m pytest` → **304 passed, 0 failed, 0 skipped** (matches the claim exactly; new suites use synthetic frames / a fake row — nothing skipped for network).
- Ruff on the new/changed modules (`levels/delta.py`, `levels/volume_profile.py`, `config/features.py`, `confluence/stack.py`) → **clean**.
- Only ruff errors in the changed set are **3 pre-existing** `E702`/`F841` in `ml/labels.py:106-128` — byte-identical at base, outside this PR's hunks, and disclosed in the PR body. Not introduced here.

## Claims verified against the diff
1. **Three opt-in signals, default OFF, validated on real 1h data** — CONFIRMED. `config/features.py:36-44` defaults both flags False; `levels/builder.py:182-191` gates delta/VP behind flag AND source-column presence; `confluence/stack.py:115-116` adds `delta_align=False`, `killzone_gate=False`.
2. **Default-OFF byte-identical invariance** (safety-critical) — CONFIRMED, independently re-run: `build_levels` env-default == explicit-off (`assert_frame_equal`); `confluence_position` default-param invariance (`assert_series_equal`); `make_features` emits no delta/vp columns by default. `OPTIONAL_LEVEL_COLUMNS` split lets the scorer skip absent columns.
3. **Parsimony — no new vote** — CONFIRMED. `factor_votes()` (`confluence/stack.py:25`) not in the diff; new signals are filters/features only.
4. **Plumbing retains taker columns** — CONFIRMED. `ingest/binance.py:115-120` keeps `taker_buy_base/quote`; `resample.py:24-26` sums them, guarded `if c in s.columns` (no-op when absent).
5. **No-lookahead causal tests** — CONFIRMED. `test_taker_delta.py` and `test_volume_profile.py` `test_causal_truncation_invariance` assert earlier-row equality (`np.allclose`, atol 1e-9) full-vs-truncated.
6. **Validation honesty (honest negative)** — CONFIRMED, exemplary. `signal-1`: delta_align filter "FAILS OOS (discard)"; `signal-3`: killzone "FAILS — discard"; `signal-2`: "mixed-positive but not conclusive… Keep OFF." IS vs OOS tabulated separately; the killzone doc reports a contradicting `walk_forward()` engine result and resolves it transparently rather than burying it.
7. **60% confluence band** — CONFIRMED (docs): stale −31R does not reproduce; OOS ~0.60 band +0.25R, corroborating merged PR #17.
8. **Tests 304 (+20 new) / ruff-clean modules** — CONFIRMED (above).
9. **Scope/off-limits** — CONFIRMED. `validated_defaults.py` NOT in diff; no `FEE_PCT`/`TAKER_FEE_PCT` constant changes (only doc/script reads); no `data/journal.json` or `data/alert_inbox/**` edits.

## Other checks
- `ml/labels.py` change is benign — adds 9 opt-in feature names to the existing skip-if-absent loop (`labels.py:60-65`); no scope creep.
- **`docs/HANDOFF.md` rewrite (242 lines)** — a proper protocol baton advance (records this branch as last, summarizes work, sets next scope = Signal #4 OI/liquidations). Does NOT clobber protocol state.
- **Security/SSRF** — `validate_*` scripts use a hardcoded `SYMBOLS` whitelist; no symbol injection via `input`/`argv`/`environ`; research tooling, not the live path. No secret handling, no write endpoints.

## Gate note (CI)
The PR carried **no CI check runs** at audit time (none triggered on the branch). The auditor reproduced the full suite green locally (304/304) and ruff clean, so the *substance* of a CI-green PASS is satisfied; the absence of a GitHub-side green check is a process gap flagged to the user before merge.

## Self-audit caveat
This gate was run inside an authoring session under the relay protocol; the auditor subagent ran arm's-length in an isolated worktree with no authoring context, but the orchestration was not a fully separate human review.
