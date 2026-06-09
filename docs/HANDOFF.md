# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `BOOTSTRAP` — this is the chat that introduced the relay.
- **This chat's branch:** `claude/sol-short-position-0eytax`
- **This chat's PR:** _(set by /closeout when the PR is opened)_
- **Audit status:** `AWAITING_AUDIT`
- **Prior work note:** everything before this PR (SOL short logging, MEMORY §24–§26,
  zero-fee TradFi forward-scan) was merged **direct to `main` pre-protocol**. From
  this PR forward, the one-PR-per-chat + audit-gate rules apply.

## What this chat did (for the auditor to verify against the diff)

- Resolved the discretionary SOL short HIT (+1.16R) in the journal.
- MEMORY §25: real-execution + measured taker fee (0.045%/side).
- MEMORY §26 + build: zero-fee TradFi forward-scan (`RouterClient`, `_tradfi`
  tagging, hourly Action TradFi step, 2 tests). Full suite 166 passed.
- This PR: the **session relay protocol** itself (this file + the two skills +
  SessionStart hook + `docs/SESSION_PROTOCOL.md` + MEMORY §27).

## NEXT chat

- **Proposed branch:** `claude/net-of-fee-scoring`
- **Scope (one priority):** make the zero-fee edge *measurable* — add per-venue
  net-of-fee scoring to the journal scorecard (crypto −0.09%/trade taker, TradFi
  0). This is the open follow-up flagged in MEMORY §26.
- **Open risks / watch-items for next session:**
  - Resolved-trade scorecard is under **censoring bias** (fast stop-outs resolve;
    3R winners stay open) — do NOT reverse-engineer an "inverse edge" off it
    (discussed at length; it's the data-mining trap the significance gate exists
    to stop). Let open winners resolve first.
  - TradFi level logic (`build_levels`) assumes 24/7 — unverified across equity/
    futures session gaps. Watch the `_tradfi` record for level-quality artifacts.
  - The hourly paper-trade Action commits to `main` every hour. It owns
    `data/journal.json`; sessions should NOT commit journal refreshes from manual
    status checks (they race the bot).
- **Off-limits:** don't touch the validated strategy defaults (§1) or `FEE_PCT`
  value without a walk-forward; don't delete the 4 redundant stale branches
  without explicit OK.

## Baton history

- `BOOTSTRAP` — relay protocol introduced.
