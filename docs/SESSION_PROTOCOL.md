# Session Relay Protocol — one chat, one PR, audited handoff

> The container is ephemeral; continuity lives in git. This protocol turns each
> Claude Code chat into **one reviewed unit of work** and makes the handoff
> between sessions a durable, *audited* artifact instead of trust. It sits on top
> of the memory layer (`docs/MEMORY.md`) — memory is *what we learned*, this is
> *how we hand the baton*.

## The loop (human-triggered, auditor-gated)

```
  ┌─ new chat ─────────────────────────────────────────────────┐
  │ 1. SessionStart hook surfaces the BATON (docs/HANDOFF.md)   │
  │ 2. /handoff-audit  → auditor SUBAGENT reviews the PREVIOUS  │
  │      PR's diff vs. what MEMORY/PR claims; writes a report   │
  │      to docs/audits/<branch>.md; verdict PASS/CONCERNS/FAIL │
  │ 3. If PASS → merge the previous PR (the GATE) → sync main   │
  │ 4. Create THIS chat's branch (name from the baton)          │
  │ 5. ... do the work ...                                      │
  │ 6. /closeout → ask handoff Qs, update memory, open ONE PR,  │
  │      set the baton for the NEXT chat → status AWAITING_AUDIT│
  └────────────────────────────────────────────────────────────┘
```

The merge of chat N's PR is **gated by chat N+1's audit**. Nothing lands on
`main` unreviewed, and no session has to trust the previous one's self-report.

## Invariants (the rules that keep it from tangling)

1. **One open PR at a time.** A chat does not start its branch until the previous
   PR is merged (audit PASS) and `main` is synced. This prevents a stack of
   dependent, conflicting branches.
2. **The baton is the single source of truth for "what's next."** `docs/HANDOFF.md`
   holds: previous branch + PR, audit status, the NEXT branch name + scope, and
   open risks. Whoever reads it can continue with zero extra context.
3. **Audit is independent.** The auditor is a *subagent* with a fresh read — it
   compares the diff to the claims, it does not take the PR description on faith.
4. **CI is the floor, the audit is the ceiling.** `ci.yml` (tests) must be green
   for a PASS to even be possible; the audit then judges correctness, scope, and
   honesty (over-claiming, untested assertions, security).
5. **Memory before code.** Every session reads `docs/MEMORY.md` first (the
   SessionStart hook points at it) so we never re-derive or re-break settled work.

## Verdicts

| Verdict | Meaning | Action |
|---|---|---|
| **PASS** | Diff matches claims, tests green, scope respected | Merge prior PR, proceed |
| **CONCERNS** | Works but has issues (over-claim, gap, risk) | Report to user; fix-forward or merge-with-notes per user |
| **FAIL** | Broken, untested, or claims ≠ diff | Do NOT merge; report; fix on the prior branch |

## Files

- `docs/HANDOFF.md` — the baton (current state, machine + human readable).
- `docs/audits/<branch>.md` — one audit report per audited PR.
- `.claude/skills/closeout/SKILL.md` — the `/closeout` protocol.
- `.claude/skills/handoff-audit/SKILL.md` — the `/handoff-audit` protocol.
- `.claude/hooks/session-start.sh` — surfaces the baton at every session start.

## Why this is worth the ceremony

This project's whole thesis is *honesty over self-deception* — the significance
gate and multiple-testing ledger exist so we never mistake luck for edge. This
protocol applies the same instinct to the **development process**: an independent
auditor on every handoff is the significance gate for *code*, not just trades.
