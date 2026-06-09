# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `LIVE` — first working chat under the relay.
- **This chat's branch:** `claude/handoff-audit-fee-scoring-p0yg4n`
- **This chat's PR:** #3 — https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/3
- **Audit status:** `AWAITING_AUDIT` — next chat runs `/handoff-audit` on PR #3, then merges on a PASS.
- **Prior gate:** PR #2 (bootstrap) was audited → CONCERNS (CI red: `ci.yml` didn't
  install pytest) → fixed forward (`ff164c6`) → CI green → **merged** (`48415f33`).
  Report: `docs/audits/claude-sol-short-position-0eytax.md`.

## What this chat did (for the auditor to verify against the diff)

- **Audited + merged PR #2** (see Prior gate above). The audit itself is the proof.
- **Net-of-fee scoring** (closes the §26 follow-up): `journal/fees.py` (venue from
  the symbol spec; `fee_in_r = fee_pct * entry / |entry-stop|`), `scorecard()` gains
  `net_expectancy_r`/`net_total_r`, CLI renders them, new constants
  `CRYPTO_FEE_ROUNDTRIP=0.0008` / `TRADFI_FEE_ROUNDTRIP=0.0` (**`FEE_PCT` untouched**).
  MEMORY §28. +3 tests. **Suite 168 passed.**
- UNSURE / flagged honestly: `0.0008` crypto maker is an ASSUMPTION (2x `FEE_PCT`'s
  0.0004, below §25's measured taker 0.0009) — unconfirmed until a real maker fill.

## NEXT chat

- **Proposed branch:** `claude/net-of-fee-equity-curve`
- **Scope (one priority):** extend net-of-fee to the rest of the scoring surface —
  `resolved_series()` (the forward equity curve) and `source_record()` are still
  GROSS, so the same book reports two different numbers. Make them net too (reuse
  `journal/fees.fee_in_r`) so the curve can't be misread. Keep it consistent with
  the scorecard's per-venue treatment.
- **Open risks / watch-items for next session:**
  - Resolved-trade book is under **censoring bias** (fast stop-outs resolve; 3R
    winners stay open) — do NOT reverse-engineer an "inverse edge" off it. Let open
    winners resolve first.
  - TradFi level logic (`build_levels`) assumes 24/7 — unverified across equity/
    futures session gaps. Watch the `_tradfi` record for level-quality artifacts.
  - The hourly paper-trade Action commits to `main` every hour and owns
    `data/journal.json`; sessions must NOT commit journal refreshes (they race it).
- **Off-limits:** don't touch the validated strategy defaults (§1) or `FEE_PCT`
  without a walk-forward; **don't change `CRYPTO_FEE_ROUNDTRIP=0.0008` without a
  real maker fill** to justify it (frozen until measured); don't delete the stale
  branches without explicit OK.

## Baton history

- `BOOTSTRAP` — relay protocol introduced (PR #2, merged).
- `LIVE` — audited+merged PR #2; shipped net-of-fee scoring (PR #3). → `claude/net-of-fee-equity-curve`.
