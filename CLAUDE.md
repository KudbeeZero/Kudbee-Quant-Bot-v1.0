# CLAUDE.md — standing instructions for this repo

> Read this first, every session. It is short on purpose. The deep context lives
> in `docs/MEMORY.md` (what we've learned/tested), `docs/SESSION_PROTOCOL.md`
> (how we hand off between chats), and `docs/BRAIN.md` (the full cognitive map —
> every route to every memory layer, organized by brain region).

## Required reading at session start
1. `docs/HANDOFF.md` — the baton: what the last chat did, the audit status, and
   THIS chat's branch + scope. (The SessionStart hook prints it for you.)
2. `docs/MEMORY.md` — never re-derive or re-break settled work; honor its caveats.
3. `docs/BRAIN.md` — the memory/cognitive architecture; when you add a capability
   or a lesson, file it under the region it belongs to so the map never drifts.
4. `docs/CROSSROADS.md` — the decision board: every open fork with its evidence,
   options, and recommended default. Move a row the SAME turn a decision is made or
   deferred — the board is only useful if it's current.

## Workflow: streaming, actionable (updated 2026-07-02, owner-set)
The old strict "one chat = one PR, never push to `main`" rule is RETIRED. Default to
the fastest safe path that keeps momentum:
- **Commit directly to `main`** for docs/memory updates, small verified fixes, and
  anything low-risk — the streaming, actionable workflow. Keep commits focused and
  the message honest; run the suite when code changed.
- **Open a PR** when it genuinely helps: a large or risky change, anything touching
  the **live-execution / money path** (still owner-sign-off only), a change worth a
  Cloudflare **preview** (website/visual), or when the owner asks to review first.
- **Owner may authorize merge-on-green**; when he does, merge it. Otherwise a PR is
  handed off "ready for review." Closing/withdrawing a PR is fine with permission.
- `/handoff-audit` (wake) and `/closeout` (sleep) still frame a session, but no
  longer force a single-PR bottleneck.

## Branch & Commit Machine (owner-set 2026-07-06, Fable 5 execution contract)
Enforceable rules, followed literally, one focused unit of work at a time:
1. **Default: direct commit to `main`** for small verified fixes, docs, and memory
   updates (the streaming workflow above).
2. **PR required:** large change, risky change, anything touching the
   **live-execution / money path** (explicit owner approval, NEVER merge-on-green),
   or website/visual work worth a Cloudflare Pages preview.
3. **Verification-first:** run the relevant tests (`pytest`, CLI smoke, paper-scan
   checks) BEFORE commit/PR when code changed. Targeted diffs only — never full-file
   rewrites unless the file is new or tiny; no broad refactors.
4. **Memory the same turn:** any commit/PR that changes facts updates the matching
   layer (`docs/MEMORY.md` under its `docs/BRAIN.md` region, `docs/CROSSROADS.md`,
   the Branch Execution Ledger in `docs/AGENT_ORCHESTRATION_LEDGER.md`) in the SAME
   turn. Honor existing per-branch audits in `docs/audits/`.
5. **Live/money = hard owner gate**, surfaced as an `AskUserQuestion` with concrete
   options, recommended default first. Same for anything altering the
   honesty/measurement thesis.
6. **Branch hygiene:** the Branch Execution Ledger is the single source of truth for
   branch state; deletions only with owner approval (CROSSROADS X5). Agent containers
   clone shallow — `git fetch --unshallow` before any branch archaeology (§84).
7. **Every working turn ends with Summary + Next** (see below) — honest over
   optimistic, always an actionable result.

## Standing rule: SELF-UPDATING MEMORY (owner-set 2026-07-02)
The memory file should, over time, stop looking like documentation and start looking
like the team. So **write memory as you go, not just at closeout**:
- **Repeat an instruction → save it.** If the owner says a thing twice, it's a
  convention: put it in `CLAUDE.md` (how we work) or `docs/MEMORY.md` (what's true).
- **Agree on a new convention → save it immediately**, so it's honored next session.
- **Make the same mistake twice → save it** as a hard-negative + a guard/test so the
  lesion can't recur (e.g. §75 VWAP sign-pin test, §77 forming-candle test).
File each under the right region in `docs/BRAIN.md`. A capability added without being
filed is a blind spot.

## Standing preference: how every working reply ENDS
When you finish a task or a unit of work, ALWAYS close the reply with two clearly
labelled parts:
1. **Summary** — what you actually did this turn (concise, honest; include test
   results / what's committed/pushed; flag anything skipped or uncertain).
2. **Next** — *exactly* what you recommend the user do next, as a concrete,
   specific action (not vague options). If a decision is genuinely theirs, state
   your recommended default first. **There is ALWAYS an actionable result.**
   "Stand by / wait and see" is NOT an acceptable Next unless waiting is itself
   the deliberately chosen action event (e.g. "let CI finish, nothing to do"
   stated as the action) — otherwise the Next is something *you do* or something
   *concrete the owner does*.

Keep it honest over optimistic: if something failed or is unverified, say so in
the Summary rather than burying it.

## Standing preference: be proactive — fix, don't just report (owner = the user)
The user is the **owner**. He reviews; you execute. Operating rules:
- **Fix, don't just report.** If you find an issue (a bug, a CI failure, a review
  comment, a broken assumption), the response is to **fix it** and report the fix —
  not to surface the problem and stop. Every issue resolves to an actionable result.
  Only pause to ask first when the fix is genuinely ambiguous or architecturally
  significant (then ask via `AskUserQuestion`, recommended option first).
- **Tell the owner when a PR is READY.** When a PR's CI is green and it's in good
  shape, say so explicitly and plainly: "PR #N is ready for your review." Don't
  bury readiness or make him hunt for it.
- **Merging (updated 2026-07-02):** the owner may pre-authorize **merge-on-green** —
  when he has, merge it yourself once CI is green and report the result. Absent that
  authorization, prep the PR fully and hand it off for his merge. Anything touching
  the **live-execution / money path** is always his explicit call, never merge-on-green.

## Standing preference: surface decisions as one-tap choices
When the **Next** step (or any fork) is genuinely the user's call, present it with
the `AskUserQuestion` tool so he can approve with a button instead of typing — put
your recommended option first, labelled. Frame the choice around **concrete actions**
(e.g. "ship it" vs. "revise X first"), not a passive "stand by." Proactively offer
to **wrap up the chat and start a fresh one** when context/token budget is getting
tight or a unit of work is complete (this protocol is built around one-chat-one-PR
handoffs, so a clean stopping point is cheap to take).

## Project norms (the thesis)
- The edge is honesty + execution, not more signals. Don't over-claim. A result
  isn't "validated" unless a test or the significance-gated harness backs it.
- The hourly paper-trade Action owns `data/journal.json` — don't commit manual
  journal refreshes (they race the bot).
