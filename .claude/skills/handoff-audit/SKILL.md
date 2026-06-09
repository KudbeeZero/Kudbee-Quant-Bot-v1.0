---
name: handoff-audit
description: Start-of-chat audit gate for the Session Relay Protocol. Reads the memory + baton, spawns an INDEPENDENT auditor subagent to review the previous chat's PR (diff vs. claims, tests, scope, honesty), writes docs/audits/<branch>.md, and — only on a PASS — merges the previous PR before the new chat starts work. Use at the start of a new session, or when the user says "audit the handoff", "review the last PR", "start the next chat". See docs/SESSION_PROTOCOL.md.
---

# /handoff-audit — independent review gate before this chat starts work

You are starting a session under the Session Relay Protocol
(`docs/SESSION_PROTOCOL.md`). The previous chat opened a PR; your job is to audit
it independently and, only if it passes, merge it and set up this chat's branch.

## 1. Load context
- Read `docs/HANDOFF.md` (the baton) and the latest sections of `docs/MEMORY.md`.
- Identify the previous chat's **branch** and **PR** from the baton. Confirm the
  PR with `mcp__github__pull_request_read` and check CI via
  `mcp__github__pull_request_read` (status/checks). CI green is required for PASS.

## 2. Spawn an INDEPENDENT auditor subagent
Use the `Agent` tool (`subagent_type: general-purpose`) with a prompt that makes
it review with fresh eyes — it must NOT take the PR description on faith:

> Audit PR `<n>` (branch `<branch>`) for the Kudbee quant project. Do NOT trust
> the PR/commit/memory claims — verify them against the actual diff.
> 1. `git fetch` then read the diff: `git diff origin/main...origin/<branch>`.
> 2. For EACH claim in the PR body / the baton's "What this chat did" / any new
>    `docs/MEMORY.md` section, find the diff evidence (`file:line`) that supports
>    it — or flag it as UNSUPPORTED / OVER-CLAIMED.
> 3. Run the tests (`python -m pytest -q`). Report pass/fail counts.
> 4. Check: scope creep (changes unrelated to the stated goal), untested new
>    behavior, security (esp. anything touching network/SSRF, write endpoints,
>    secrets), and whether any "validated/tested" claim is actually backed by a
>    test or a harness run.
> 5. Output a verdict — **PASS / CONCERNS / FAIL** — with a short bulleted
>    findings list, each with `file:line` evidence, and a one-line rationale.

## 3. Write the audit report
- Save the subagent's report to `docs/audits/<branch>.md` (verdict header, date,
  PR link, findings with evidence, test result). Commit it on THIS chat's branch
  later (step 5) — or on a tiny `audit/<branch>` commit if you prefer it landed
  immediately; keep it out of `main` until merge.

## 4. Apply the gate
- **PASS** → merge the previous PR (`mcp__github__merge_pull_request`), then
  `git fetch && git checkout main && git pull` to sync. Tell the user it passed
  and was merged.
- **CONCERNS** → do NOT auto-merge. Summarize the concerns and use
  `AskUserQuestion` to ask whether to (a) fix-forward on the prior branch,
  (b) merge-with-notes, or (c) hold.
- **FAIL** → do NOT merge. Report the blocking issues; offer to fix them on the
  prior branch and re-audit.

## 5. Start this chat's branch
- After a PASS-merge (and only then), create this chat's branch from fresh `main`
  using the **NEXT branch** name in the baton: `git checkout -b <next-branch>`.
- Briefly restate the baton's scope + open risks so the user can confirm or
  redirect before work begins.

Never skip the audit because the PR "looks small" — a one-line change that
contradicts a MEMORY claim is exactly what this gate is for.
