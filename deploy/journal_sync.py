"""Host-side journal sync — keeps the repo as the journal's single source of truth.

The hourly paper-trade GitHub Action OWNS ``data/journal.json``: it logs the
bot's setups and is the only thing that RESOLVES trades (statuses/outcomes).
A hosted API (docs/DEPLOY.md) is a second writer: ``POST /api/alert`` appends
TradingView alerts to the host's local copy. Those alerts must reach the repo
or they never get resolved/scored — and the host must keep pulling the repo or
the dashboard goes stale. This daemon reconciles both directions on a loop:

  1. ``git fetch origin <branch>``.
  2. Read the LOCAL journal (captures uncommitted ``/api/alert`` appends and
     anything committed-but-unpushed by a previous failed tick).
  3. ``git reset --hard origin/<branch>`` — origin is canonical.
  4. Union-merge: keep origin's record for every id it knows (only the bot
     mutates existing trades), append local-only ids (the new alerts).
  5. If that added anything: commit + push. A lost push race just means the
     next tick redoes the merge from a fresher origin — the algorithm is
     idempotent, there is nothing to conflict on.

No rebase, no merge conflicts by construction. Known (documented) gap: an
``/api/alert`` write landing in the few ms between step 2's read and step 3's
reset is lost; the journal file has no cross-process lock today.

Stdlib only. Usage:  python deploy/journal_sync.py --repo /data/repo
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

JOURNAL_REL = "data/journal.json"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120)


def _load(path: Path) -> list[dict] | None:
    """None = unreadable (torn read from a concurrent /api/alert write) —
    callers must NOT reset/merge on None or the in-flight write gets wiped."""
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def merge_journals(origin: list[dict], local: list[dict]) -> tuple[list[dict], int]:
    """Origin's record wins for every id it has; local-only ids are appended
    in their local order. Returns (merged, n_added)."""
    origin_ids = {p["id"] for p in origin}
    added = [p for p in local if p["id"] not in origin_ids]
    return origin + added, len(added)


def sync_once(repo: Path, branch: str = "main") -> str:
    """One reconcile tick. Returns a short status string (for logs/tests)."""
    jpath = repo / JOURNAL_REL
    if _git(repo, "fetch", "origin", branch).returncode != 0:
        return "fetch-failed"
    local = _load(jpath)
    if local is None:
        return "local-unreadable (skipped)"
    if _git(repo, "reset", "--hard", f"origin/{branch}").returncode != 0:
        return "reset-failed"
    origin_journal = _load(jpath)
    if origin_journal is None:                  # can't happen post-reset, but be safe
        return "origin-unreadable (skipped)"
    merged, n_added = merge_journals(origin_journal, local)
    if n_added == 0:
        return "up-to-date"
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(merged, indent=2))
    _git(repo, "add", JOURNAL_REL)
    msg = f"tv-alert: sync {n_added} host-logged trade(s) [skip ci]"
    if _git(repo, "commit", "-m", msg).returncode != 0:
        return "commit-failed"
    if _git(repo, "push", "origin", f"HEAD:{branch}").returncode != 0:
        # Push race (the hourly Action got there first). Local commit survives;
        # the next tick re-reads it as "local", resets to origin, re-merges.
        return f"push-failed ({n_added} pending)"
    return f"pushed {n_added}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--interval", type=float, default=60.0,
                    help="seconds between ticks (0 = run once and exit)")
    args = ap.parse_args()
    while True:
        try:
            status = sync_once(args.repo, args.branch)
        except Exception as e:                                # noqa: BLE001
            status = f"error: {e}"
        print(f"[journal-sync] {status}", flush=True)
        if args.interval <= 0:
            return 0 if ("failed" not in status and "error" not in status) else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
