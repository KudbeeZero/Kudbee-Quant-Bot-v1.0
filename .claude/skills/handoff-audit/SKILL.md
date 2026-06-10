---
name: handoff-audit
description: Start-of-chat audit gate for the Session Relay Protocol. Reads the memory + baton, checks the previous chat's PR state, spawns an INDEPENDENT auditor subagent to review it (diff vs. claims, tests, scope, honesty), writes docs/audits/<branch>.md, applies the merge gate (or a post-hoc record if it's already merged), and reconciles the baton. Use at the start of a new session, or when the user says "audit the handoff", "review the last PR", "start the next chat". See docs/SESSION_PROTOCOL.md.
---

# /handoff-audit — independent review gate before this chat starts work

You are starting a session under the Session Relay Protocol
(`docs/SESSION_PROTOCOL.md`). The previous chat opened a PR; your job is to audit
it independently, apply the merge gate to its *real* state, reconcile the baton,
and confirm this chat's scope before work begins.

> **You are already on this chat's branch.** The harness assigned it at session
> start — do NOT `git checkout -b` a new one. Discover it with
> `git rev-parse --abbrev-ref HEAD` and commit your audit report there.

## 1. Load context + check the PR's REAL state
- Read `docs/HANDOFF.md` (the baton) and the latest sections of `docs/MEMORY.md`.
- Identify the previous chat's **branch** and **PR** from the baton.
- `git fetch origin --prune`, then run `mcp__github__pull_request_read` (`method: get`)
  to read the PR's **actual** state — `open`, `merged`, or `closed`. This drives
  the gate in step 4; never assume the baton's `Audit status` is current (a human
  may have merged from the UI). Also pull CI via `get_check_runs` / `get_status` —
  CI green is required for a PASS.
- **Branch hygiene (opt-in):** list branches already merged into `main`
  (`git branch -r --merged origin/main`); if stale/divergent `claude/*` branches
  exist, surface them — delete only with the user's explicit OK.

## 2. Spawn an INDEPENDENT auditor subagent
Use the `Agent` tool (`subagent_type: general-purpose`) with a prompt that makes
it review with fresh eyes — it must NOT take the PR description on faith:

> Audit PR `<n>` (branch `<branch>`) for the Kudbee quant project. Do NOT trust
> the PR/commit/memory claims — verify them against the actual diff.
> 1. `git fetch` then read the diff between the PR's **base and head SHAs**
>    (from the GitHub API — `base.sha`/`head.sha`): `git diff <base_sha>..<head_sha>`.
>    Use the SHAs, not `origin/main...origin/<branch>` — once the PR is merged the
>    three-dot range against `main` collapses to an empty diff.
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
  PR link + state, findings with evidence, test result). Commit it on THIS chat's
  branch (the one the harness gave you) — the report always lands, regardless of
  the gate outcome.

## 4. Apply the gate — to the PR's REAL state (from step 1)

**If the PR is still OPEN:**
- **PASS** → merge it (`mcp__github__merge_pull_request`), then
  `git fetch && git checkout main && git pull` to sync. Tell the user.
- **CONCERNS** → do NOT auto-merge. Summarize and use `AskUserQuestion` to ask
  whether to (a) fix-forward on the prior branch, (b) merge-with-notes, or (c) hold.
- **FAIL** → do NOT merge. Report the blocking issues; offer to fix on the prior
  branch and re-audit.

**If the PR is ALREADY MERGED** (a human merged it from the UI — the gate didn't
hold): the audit is a **post-hoc record**, not a merge decision.
- **PASS** → just record it; nothing to merge.
- **CONCERNS / FAIL** → you can't un-merge. Report the issue to the user and
  offer a **fix-forward**: a follow-up on a new branch (or a GitHub issue). Do not
  silently let a non-PASS merged change pass unflagged.

**If the PR is CLOSED unmerged** → record it and skip; note it for the user.

## 5. Reconcile the baton + confirm this chat's scope
- Update `docs/HANDOFF.md` "Audit status" to a **terminal** value reflecting what
  actually happened — e.g. `MERGED (audit PASS)`, `MERGED (post-hoc PASS)`,
  `MERGED (post-hoc CONCERNS — fix-forward: <ref>)`, or `FAILED`. Never leave it
  at `AWAITING_AUDIT` once you've audited.
- You are **already on this chat's branch** (harness-assigned) — do NOT create a
  new one. Restate the baton's NEXT-chat scope + open risks so the user can
  confirm or redirect before work begins. If the harness branch name doesn't match
  the baton's slug hint, that's expected — the scope is what binds, not the name.

Never skip the audit because the PR "looks small" — a one-line change that
contradicts a MEMORY claim is exactly what this gate is for.
