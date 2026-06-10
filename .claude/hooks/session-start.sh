#!/usr/bin/env bash
# SessionStart hook — surface the relay baton so every (ephemeral) session boots
# with continuity. Output goes into the session context. Keep it short.
# See docs/SESSION_PROTOCOL.md.
set -euo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
handoff="$root/docs/HANDOFF.md"

echo "=== Session Relay Protocol (docs/SESSION_PROTOCOL.md) ==="
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
echo "This chat's branch (harness-assigned): $branch"
if [[ -f "$handoff" ]]; then
  # Print the baton up to (not including) the history section.
  awk '/^## Baton history/{exit} {print}' "$handoff"
  status="$(grep -m1 -i 'Audit status:' "$handoff" || true)"
  if echo "$status" | grep -qi 'AWAITING_AUDIT'; then
    echo ""
    echo ">> A previous PR is AWAITING_AUDIT. Run /handoff-audit before new work —"
    echo "   it checks the PR's REAL state (a human may have merged it already)."
  fi
else
  echo "(no docs/HANDOFF.md yet — run /closeout at the end of a chat to start the relay)"
fi
echo "=== Memory: read docs/MEMORY.md first (what we've already learned/tested) ==="
