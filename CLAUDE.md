# CLAUDE.md — standing instructions for this repo

> Read this first, every session. It is short on purpose. The deep context lives
> in `docs/MEMORY.md` (what we've learned/tested) and `docs/SESSION_PROTOCOL.md`
> (how we hand off between chats).

## Required reading at session start
1. `docs/HANDOFF.md` — the baton: what the last chat did, the audit status, and
   THIS chat's branch + scope. (The SessionStart hook prints it for you.)
2. `docs/MEMORY.md` — never re-derive or re-break settled work; honor its caveats.

## Session Relay Protocol (how we work — see docs/SESSION_PROTOCOL.md)
- **One chat = one PR.** Don't push straight to `main`. Don't start the next
  branch until the previous PR is merged and `main` is synced.
- **Start a chat** with `/handoff-audit` — it independently audits the previous
  PR (diff vs. claims, tests, scope, honesty) and merges it only on a PASS.
- **End a chat** with `/closeout` — it asks the handoff questions, updates memory,
  opens the single PR, and sets the baton for the next chat.

## Standing preference: how every working reply ENDS
When you finish a task or a unit of work, ALWAYS close the reply with two clearly
labelled parts:
1. **Summary** — what you actually did this turn (concise, honest; include test
   results / what's committed/pushed; flag anything skipped or uncertain).
2. **Next** — *exactly* what you recommend the user do next, as a concrete,
   specific action (not vague options). If a decision is genuinely theirs, state
   your recommended default first.

Keep it honest over optimistic: if something failed or is unverified, say so in
the Summary rather than burying it.

## Project norms (the thesis)
- The edge is honesty + execution, not more signals. Don't over-claim. A result
  isn't "validated" unless a test or the significance-gated harness backs it.
- The hourly paper-trade Action owns `data/journal.json` — don't commit manual
  journal refreshes (they race the bot).
