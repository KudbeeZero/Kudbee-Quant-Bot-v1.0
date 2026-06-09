#!/usr/bin/env bash
# Overnight research loop — runs the honest hypothesis harness once per hour,
# commits the results, and pushes to the feature branch. Designed to be armed
# as a background Monitor: each cycle prints ONE status line (the harness
# verdicts + commit result) which wakes the session so fresh candidate ideas
# can be queued. Fully autonomous for the queued candidates even if no one is
# watching — the queue drains and results are pushed regardless.
#
# Usage:  bash scripts/overnight_loop.sh [CYCLES] [SLEEP_SECONDS] [BATCH]
# Default: 8 cycles, 3600s apart, 3 candidates per cycle.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
BRANCH="claude/overnight-algo-research-plan-hyqzf6"
CYCLES="${1:-8}"
SLEEP_S="${2:-3600}"
BATCH="${3:-3}"

push_with_backoff() {
  local delay=2
  for _ in 1 2 3 4; do
    git push -u origin "$BRANCH" >/dev/null 2>&1 && return 0
    sleep "$delay"; delay=$((delay * 2))
  done
  return 1
}

for ((i = 1; i <= CYCLES; i++)); do
  ts="$(date -u +'%Y-%m-%d %H:%M UTC')"

  # Test the next batch; capture the verdict lines for the status summary.
  out="$(python scripts/overnight_research.py --batch "$BATCH" 2>&1)"
  verdicts="$(printf '%s\n' "$out" | grep -E '> (WINNER|SUGGESTIVE|NEUTRAL|HURTS|THIN|ERROR)' | sed 's/^[[:space:]]*//' | tr '\n' ' ')"
  winners="$(printf '%s\n' "$out" | grep -c 'WINNER')"
  pending="$(python scripts/overnight_research.py --status 2>/dev/null | grep -oE '[0-9]+ pending' | head -1)"

  # Commit + push whatever changed (journal/results/findings).
  git add data/overnight_queue.json data/overnight_results.json \
          docs/research/overnight_findings.md docs/research/overnight_idea_backlog.md \
          docs/MEMORY.md scripts/overnight_candidates.py >/dev/null 2>&1
  if git diff --cached --quiet; then
    commit_status="no-change"
  elif git commit -q -m "overnight research: hourly cycle $ts" >/dev/null 2>&1 && push_with_backoff; then
    commit_status="pushed"
  else
    commit_status="commit/push FAILED"
  fi

  # ONE status line per cycle -> wakes the session (covers success + failure).
  if [[ -z "$verdicts" ]]; then
    echo "[cycle $i/$CYCLES $ts] queue $pending — nothing tested ($commit_status)"
  else
    echo "[cycle $i/$CYCLES $ts] $winners winner(s); $verdicts| queue $pending ($commit_status)"
  fi

  [[ $i -lt $CYCLES ]] && sleep "$SLEEP_S"
done

echo "[overnight-loop DONE] completed $CYCLES cycles — review docs/research/overnight_findings.md"
