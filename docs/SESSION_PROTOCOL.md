# Session Relay Protocol — one chat, one PR, audited handoff

> The container is ephemeral; continuity lives in git. This protocol turns each
> Claude Code chat into **one reviewed unit of work** and makes the handoff
> between sessions a durable, *audited* artifact instead of trust. It sits on top
> of the memory layer (`docs/MEMORY.md`) — memory is *what we learned*, this is
> *how we hand the baton*.

## The loop (human-triggered, auditor-gated)

```
  ┌─ new chat (the harness drops you on a fresh claude/* branch) ──┐
  │ 1. SessionStart hook surfaces the BATON (docs/HANDOFF.md)      │
  │ 2. /handoff-audit → find the PREVIOUS chat's PR and check its  │
  │      ACTUAL state on GitHub (open / merged / closed)           │
  │ 3. An auditor SUBAGENT reviews that PR's diff vs. what the     │
  │      PR/MEMORY claims; writes docs/audits/<branch>.md;         │
  │      verdict PASS / CONCERNS / FAIL                            │
  │ 4. Apply the gate to the PR's REAL state:                     │
  │      • OPEN + PASS     → merge (the gate) → sync main          │
  │      • MERGED already  → audit is a POST-HOC record; if it's   │
  │                           not PASS, file a fix-forward follow-up│
  │      • CLOSED unmerged → record + skip                         │
  │ 5. Reconcile the baton's audit status to the real outcome     │
  │ 6. Confirm THIS chat's branch + scope with the user, work it  │
  │ 7. /closeout → ask handoff Qs, update memory, open ONE PR,     │
  │      record the REAL branch, set the baton → AWAITING_AUDIT    │
  └────────────────────────────────────────────────────────────────┘
```

The merge of chat N's PR is **gated by chat N+1's audit** — *when the gate can
hold*. Nothing should land on `main` unreviewed; but because a human can merge a
PR from the GitHub UI at any time, the audit must check the PR's real state and
fall back to a **post-hoc** review (see below) rather than assume it still owns
the merge. No session has to trust the previous one's self-report either way.

> **Branch names are harness-assigned.** On Claude Code on the web, the session
> branch (e.g. `claude/handoff-audit-xtn2bz`) is created *for* you when the chat
> starts — you do not pick it and the baton cannot dictate it. So the baton hands
> off **scope**, not a branch name; both skills DISCOVER the current branch with
> `git rev-parse --abbrev-ref HEAD` and use whatever they're on.

## Invariants (the rules that keep it from tangling)

1. **Each chat owns exactly one branch + one PR — its own.** The harness assigns
   the branch name at session start; you don't pick it and the baton can't dictate
   it. `main` is the only integration point. Parallel chats *can* exist (the web UI
   lets you start several), so keep them from tangling by: (a) merging/rebasing the
   latest `main` into your branch before `/closeout` so the PR has a current base,
   and (b) reconciling or closing divergent/stale branches at audit time — only
   with the user's explicit OK (see "Branch hygiene" below).
2. **The baton hands off SCOPE, not a branch name.** `docs/HANDOFF.md` "NEXT chat"
   holds the one-line priority, open risks, off-limits, and an *optional* slug hint
   (advisory only). Its "Current" section records the chat's **actual** branch + PR
   + audit status. Whoever reads it can continue with zero extra context.
3. **Audit is independent and reconciles state.** The auditor is a *subagent* with
   a fresh read — it compares the diff to the claims, never taking the PR
   description on faith. It checks the PR's *real* GitHub state and updates the
   baton's audit status to a terminal value. A PR merged before its audit still
   gets a written post-hoc report.
4. **CI is the floor, the audit is the ceiling.** `ci.yml` (tests) must be green
   for a PASS to even be possible; the audit then judges correctness, scope, and
   honesty (over-claiming, untested assertions, security).
5. **Memory before code.** Every session reads `docs/MEMORY.md` first (the
   SessionStart hook points at it) so we never re-derive or re-break settled work.

## Verdicts

| Verdict | Meaning | Action if PR still OPEN | Action if PR ALREADY MERGED |
|---|---|---|---|
| **PASS** | Diff matches claims, tests green, scope respected | Merge prior PR, sync `main`, proceed | Record report; reconcile baton to `MERGED (post-hoc PASS)` |
| **CONCERNS** | Works but has issues (over-claim, gap, risk) | Report to user; fix-forward or merge-with-notes per user | Report; raise the concern with the user; fix-forward as a follow-up |
| **FAIL** | Broken, untested, or claims ≠ diff | Do NOT merge; report; fix on the prior branch | Can't un-merge — report; open a fix-forward branch/issue; flag in baton |

## When the gate can't hold (already-merged PRs & parallel branches)

The audit-gated merge is the happy path, but the environment doesn't guarantee
it, so the protocol degrades honestly instead of pretending:

- **Already merged.** A human can merge from the GitHub UI before the next chat
  audits. `/handoff-audit` therefore checks the PR's real state *first*. If it's
  already merged, the audit is still run and written as a **post-hoc record**; a
  non-PASS becomes a fix-forward follow-up (you cannot un-merge). The baton's
  audit status is reconciled to the truth — never left stale at `AWAITING_AUDIT`.
- **Parallel branches.** Several `claude/*` branches can coexist. That's fine as
  long as each integrates through `main`. The baton names the single *canonical*
  next thread; other live branches are reconciled at audit time.

### Branch hygiene (audit-time, opt-in)

At the start of `/handoff-audit`, list branches already merged into `main`
(`git branch -r --merged origin/main`) and surface any stale/divergent ones to
the user. Delete only with explicit OK — pruning branches is never automatic.

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
