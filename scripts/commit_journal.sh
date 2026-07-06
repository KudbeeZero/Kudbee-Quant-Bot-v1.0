#!/usr/bin/env bash
# Robustly commit the bot-owned data files and push to main, surviving the
# concurrent-writer race that was firing FALSE "run FAILED" Telegram alerts.
#
# Why this exists
# ---------------
# The hourly paper-trade Action runs up to 4x/hour (the 5/20/35/50 crons, plus
# the :35 status job and manual dispatches). When two runs land close together,
# the second one rebases its commit onto the first's and hits a CONTENT conflict
# on the per-run telemetry files — every run rewrites data/heartbeat.json and
# data/notify_state.json wholesale, so their lines always differ.
#
# The old inline step was:
#     git pull --rebase origin main
#     git push || (git pull --rebase origin main && git push)
# That first standalone `git pull --rebase` runs under `bash -e`, so the moment
# the rebase hit a telemetry conflict the whole step died with exit 1 — leaving a
# half-finished rebase and firing the "hourly paper-trade run FAILED" ping. The
# clever `git push || (...)` retry only ever guarded a bounced PUSH, never a
# rebase CONFLICT, so it never even ran. (Observed live: 2026-06-26 runs at
# 18:18:51 and 17:49:35 — each ~35s behind a successful run.)
#
# What this does
# --------------
# Commit our changes, then push with a small retry loop. On a rebase conflict we
# auto-resolve ONLY the regenerable telemetry files in favour of THIS run, retry
# on a moving target (origin advancing mid-rebase), and still surface a genuine
# conflict OUTSIDE the telemetry files (e.g. data/journal.json) loudly — that is
# a real event worth a failure ping, and we never fabricate a journal merge.
# journal.json does not conflict in practice: concurrent runs scan the same
# candles and dedup per (symbol, timeframe, book), so they produce the same
# journal; only the timestamp/snapshot telemetry differs.
#
# Usage:  bash scripts/commit_journal.sh
# Env:    COMMIT_JOURNAL_ATTEMPTS (default 5) — push/rebase retry budget.
set -uo pipefail

# The bot-owned paths this run stages. -A on commit so consumed inbox files
# (create-only; renames/deletions) are staged too.
DATA_PATHS=(data/journal.json data/alert_inbox data/heartbeat.json data/notify_state.json)
# Regenerable telemetry — safe to auto-resolve to THIS run's version on conflict
# (heartbeat is bounded pure observability; notify_state is a last-read snapshot).
REGEN_PATHS=(data/heartbeat.json data/notify_state.json)
MAX_ATTEMPTS="${COMMIT_JOURNAL_ATTEMPTS:-5}"

_is_regen() {
  local p="$1" r
  for r in "${REGEN_PATHS[@]}"; do
    [ "$p" = "$r" ] && return 0
  done
  return 1
}

# Refuse to commit a corrupt journal. A mid-write kill (the failure mode N4
# hardens against) can leave data/journal.json truncated; committing that
# would make every later run load it and silently no-op forever.
if [ -e data/journal.json ] && ! python3 -c "import json; json.load(open('data/journal.json'))" 2>/dev/null; then
  echo "data/journal.json failed JSON validation — refusing to commit a corrupt journal." >&2
  exit 1
fi

# Stage only the paths that exist (a non-matching pathspec would abort the whole
# `git add`, silently staging nothing). data/alert_inbox may be absent on a fresh
# checkout; the others are always present once the bot has run.
to_add=()
for p in "${DATA_PATHS[@]}"; do
  [ -e "$p" ] && to_add+=("$p")
done
if [ "${#to_add[@]}" -gt 0 ]; then
  git add -A "${to_add[@]}"
fi
if git diff --cached --quiet; then
  echo "No journal changes this run."
  exit 0
fi
git commit -m "paper-trade: update journal [skip ci]"

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  if ! git fetch origin main; then
    echo "fetch failed (attempt $attempt) — retrying" >&2
    sleep "$((attempt * 2))"; attempt="$((attempt + 1))"; continue
  fi

  if ! git rebase FETCH_HEAD; then
    # A conflict. Resolve ONLY the regenerable telemetry files (during a rebase
    # --theirs == the commit being replayed == THIS run's version).
    conflicts="$(git diff --name-only --diff-filter=U)"
    unresolved=""
    while IFS= read -r path; do
      [ -z "$path" ] && continue
      if _is_regen "$path"; then
        git checkout --theirs -- "$path" && git add -- "$path"
      else
        unresolved="${unresolved}${path} "
      fi
    done <<< "$conflicts"

    if [ -n "$unresolved" ]; then
      # Genuine conflict outside telemetry (e.g. journal.json) — do NOT fabricate
      # a merge. Abort cleanly and fail loudly (a real, alert-worthy event).
      git rebase --abort || true
      echo "Unresolvable conflict outside regenerable telemetry: ${unresolved}" >&2
      exit 1
    fi

    if ! GIT_EDITOR=true git rebase --continue; then
      # The rebase still couldn't finish (e.g. origin moved again). Abort and
      # retry from a fresh fetch.
      git rebase --abort || true
      echo "rebase --continue failed (attempt $attempt) — retrying" >&2
      sleep "$((attempt * 2))"; attempt="$((attempt + 1))"; continue
    fi
  fi

  if git push origin HEAD:main; then
    echo "Pushed journal update (attempt $attempt)."
    exit 0
  fi

  echo "push bounced (attempt $attempt) — origin moved, retrying" >&2
  sleep "$((attempt * 2))"; attempt="$((attempt + 1))"
done

echo "Push failed after ${MAX_ATTEMPTS} attempts." >&2
exit 1
