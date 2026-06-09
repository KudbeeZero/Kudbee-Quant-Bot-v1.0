---
name: closeout
description: Run the end-of-chat closeout + handoff protocol — ask the user the handoff questions, update memory, open exactly ONE PR for this chat's branch into main, and set the baton (docs/HANDOFF.md) for the next chat. Use when the user is wrapping up a session ("close this out", "let's wrap up", "closeout", "hand off"). See docs/SESSION_PROTOCOL.md.
---

# /closeout — end this chat as one reviewed PR + set the baton

You are ending a session under the Session Relay Protocol
(`docs/SESSION_PROTOCOL.md`). Do these steps **in order**. Do not skip the
questions — the baton is the user's call, not yours.

## 1. Land the work cleanly
- Make sure the working tree is committed to **this chat's branch** (never push
  straight to `main` under this protocol). If anything is uncommitted, commit it
  with a clear message.
- Run the test suite (`python -m pytest -q`). If it is red, STOP and tell the
  user — a closeout PR must be green so the next chat's audit can PASS.
- Push the branch: `git push -u origin <branch>` (retry with backoff on network
  errors).

## 2. Ask the handoff questions (AskUserQuestion)
Ask these four (adapt wording to context; offer a recommended default as the
first option where you can infer one):
1. **Accomplished** — "In one line, what did this session actually ship?"
2. **Next priority + branch** — "What's the single priority for the next chat,
   and what should its branch be named?" (propose `claude/<slug>`).
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
- Current branch + the new PR number/URL, `Audit status: AWAITING_AUDIT`.
- "What this chat did (for the auditor)" — bullet the real changes, honestly,
  including anything you are unsure about.
- NEXT chat: proposed branch (from the user's answer), the one-line scope, open
  risks, and off-limits.
- Append a one-line entry to **Baton history**.
- Commit (`closeout: hand off to <next-branch> [skip ci]`) and push the branch.

## 6. Tell the user
State: the PR URL, that it is AWAITING_AUDIT, and that the **next chat should run
`/handoff-audit` first** — it will review this PR, and merge it only on a PASS.
