---
name: closeout
description: Run the end-of-chat closeout + handoff protocol — ask the user the handoff questions, update memory, open exactly ONE PR for this chat's branch into main, and set the baton (docs/HANDOFF.md) for the next chat. Use when the user is wrapping up a session ("close this out", "let's wrap up", "closeout", "hand off"). See docs/SESSION_PROTOCOL.md.
---

# /closeout — end this chat as one reviewed PR + set the baton

You are ending a session under the Session Relay Protocol
(`docs/SESSION_PROTOCOL.md`). Do these steps **in order**. Do not skip the
questions — the baton is the user's call, not yours.

## 1. Land the work cleanly
- Discover this chat's branch (`git rev-parse --abbrev-ref HEAD`) — it's the one
  the harness assigned at session start; you do NOT rename it. Never push straight
  to `main` under this protocol.
- Make sure the working tree is committed to that branch. If anything is
  uncommitted, commit it with a clear message.
- Merge the latest `main` into the branch (`git fetch origin && git merge origin/main`)
  so the PR has a current base and the next chat's audit diff is clean. Resolve any
  conflicts before opening the PR.
- Run the test suite (`python -m pytest -q`). If it is red, STOP and tell the
  user — a closeout PR must be green so the next chat's audit can PASS. (If a red
  test is a known *environment* defect unrelated to your diff, note it explicitly
  in the PR body rather than claiming a clean run.)
- Push the branch: `git push -u origin <branch>` (retry with backoff on network
  errors).

## 2. Ask the handoff questions (AskUserQuestion)
Ask these four (adapt wording to context; offer a recommended default as the
first option where you can infer one):
1. **Accomplished** — "In one line, what did this session actually ship?"
2. **Next priority** — "What's the single priority for the next chat?" (Capture
   the *scope*, not a branch name — the next chat's branch is harness-assigned, so
   the baton can only carry an advisory `claude/<slug>` hint.)
3. **Open risks** — "Any half-finished threads, risks, or decisions the next
   session must know?"
4. **Off-limits** — "Anything the next session must NOT touch?"

## 3. Update memory (only if durable)
- If this session produced a *tested lesson* or a market/system fact worth
  keeping, add a numbered section to `docs/MEMORY.md` (L1). Do NOT log routine
  churn — memory is for what we learned, not a diary.

## 4. Open exactly ONE PR (branch → main)
- Confirm there is not already an open PR for this branch
  (`mcp__github__list_pull_requests`). If there is, update it instead of opening
  a second — the protocol allows only one open PR per chat.
- Create the PR (`mcp__github__create_pull_request`) into `main`. Body must
  include: a concise summary of the diff, the MEMORY sections touched, the test
  result, and an **"Audit checklist"** of specific things the next chat's auditor
  should verify (claims that need diff-confirmation, anything risky).
- Do NOT merge it yourself. The next chat's audit is the merge gate.

## 5. Set the baton (docs/HANDOFF.md)
Rewrite the **Current baton** and **NEXT chat** sections:
- Current branch (the ACTUAL harness-assigned name from step 1) + the new PR
  number/URL, `Audit status: AWAITING_AUDIT`.
- "What this chat did (for the auditor)" — bullet the real changes, honestly,
  including anything you are unsure about.
- NEXT chat: the one-line **scope** (from the user's answer), open risks, and
  off-limits. Add an optional `slug hint: claude/<slug>` — clearly marked
  ADVISORY, since the next chat's branch name is assigned by the harness, not this.
- Append a one-line entry to **Baton history**.
- Commit (`closeout: hand off — <scope> [skip ci]`) and push the branch.

## 6. Tell the user (the standing end-of-reply format — see CLAUDE.md)
Close with two labelled parts:
- **Summary** — what this session shipped (honest; PR URL; status AWAITING_AUDIT;
  test result; anything skipped/uncertain).
- **Next** — exactly what to do next: the next chat should run `/handoff-audit`
  first (it reviews this PR and merges only on a PASS), then work the baton scope.
