# Audits

One report per audited PR, written by the `/handoff-audit` auditor subagent at
the start of the chat that follows the PR. Filename: `<branch>.md` (the audited
chat's branch). See `docs/SESSION_PROTOCOL.md`.

Each report records: the verdict (PASS / CONCERNS / FAIL), claim-vs-diff checks
with `file:line` evidence, CI/test state, and any over-claiming, scope creep,
untested assertions, or security concerns. The merge of the audited PR is gated
on the verdict.
