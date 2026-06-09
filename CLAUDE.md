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
SHORT. Two short paragraphs, a couple of bullets total — not a full report. He
wants the bottom line, not every detail.
1. **Summary** — does it work or not? One or two bullets. If it failed or is
   unverified, say so plainly (honest over optimistic) — don't bury it.
2. **Next** — does he need to test it himself? If yes, the one thing to test.
   If no, the single next action you recommend. State the recommended default
   first; skip the menu of alternatives.

## Project norms (the thesis)
- The edge is honesty + execution, not more signals. Don't over-claim. A result
  isn't "validated" unless a test or the significance-gated harness backs it.
- The hourly paper-trade Action owns `data/journal.json` — don't commit manual
  journal refreshes (they race the bot).
