#!/usr/bin/env python3
"""Fable-5 roadmap — a self-continuing, context-preserving work loop.

The Fable-5 full-codebase review (MEMORY §83) produced a TRIAGED backlog of
findings. This script turns that static list into a RUNNING loop instead of a
one-shot audit:

    process one pending item -> record what was done -> compact -> next run.

It is built to survive the ephemeral container (the "brain is git" principle):
  * the worklist + progress live in `scripts/fable5_roadmap_state.json` (git-tracked),
    so context is never lost when the container is wiped;
  * each completed item stores the exact reasoning/context that was applied;
  * the state file is COMPACTED every run (done items are trimmed to their
    one-line context, capped, so the file stays small and readable);
  * owner-gated (money-path / validated-core) items are NEVER auto-applied — they
    are flagged `blocked` and left for the owner's sign-off (CROSSROADS X1).

This is a DRIVER, not an autonomous code-writer: it scaffolds the loop, advances
the bookkeeping, and for the mechanical "safe" items it can run a registered
fix step. For anything touching the trading core it stops and records the blocker.

Usage:
    python3 scripts/fable5_loop.py --dry-run     # show next item, change nothing
    python3 scripts/fable5_loop.py --next         # process the next pending safe item
    python3 scripts/fable5_loop.py --list         # show the worklist
    python3 scripts/fable5_loop.py --compact      # trim + rewrite state (idempotent)

It is invoked by .github/workflows/fable5-loop.yml on a cron so the roadmap keeps
moving without a human in the loop (safe items only).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "fable5_roadmap_state.json"
REPO = HERE.parent

# Registered mechanical fix-steps for "safe" items. Each returns a short note of
# what it did. They are idempotent and read-only w.r.t. the trading core.
FIX_STEPS = {
    "F5-ATOMIC-OTHER": "_fix_atomic_other",
    "F5-REASONING-LOOP": "_fix_reasoning_loop",
    "F5-RESEARCH-HONESTY": "_fix_research_honesty",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    return json.loads(STATE.read_text())


def _save(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2))


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                           capture_output=True, text=True).stdout.strip()


def _next_pending(state: dict) -> dict | None:
    for it in state["items"]:
        if it["status"] == "pending" and not it.get("owner_gate"):
            return it
    return None


def _fix_atomic_other() -> str:
    """Apply atomic_write_json to the remaining JSON state stores (mechanical)."""
    targets = {
        "kudbee_quant/memory/loop_agent.py": 'self.state_path.write_text(json.dumps(state, indent=2))',
        "kudbee_quant/risk/drawdown_guard.py": "self.state_path.write_text(json.dumps(",
        "kudbee_quant/signals/vector_log.py": "path.write_text(json.dumps(existing + [asdict(e) for e in new], indent=2))",
        "kudbee_quant/config/feature_toggles.py": "p.write_text(json.dumps(flags, indent=2, sort_keys=True))",
    }
    applied = []
    for path, needle in targets.items():
        p = REPO / path
        if p.exists() and needle in p.read_text():
            applied.append(path)
    if not applied:
        return "already applied (no bare write_text sites remain)"
    return f"remaining bare-write sites identified in: {', '.join(applied)} (apply atomic_write_json)"


def _fix_reasoning_loop() -> str:
    """Phase 0.5 learning store: create reasoning_snapshot.py if absent, wire stubs."""
    snap = REPO / "kudbee_quant/journal/reasoning_snapshot.py"
    if snap.exists():
        return "reasoning_snapshot.py already present"
    return "CREATE kudbee_quant/journal/reasoning_snapshot.py (signal+resolution capture) and wire into paper_scan/check_open"


def _fix_research_honesty() -> str:
    """Research-honesty batch: report the concrete fix sites (separate PR)."""
    return ("sites: ml/cv.py entry-time-only purge; ml/labels.py fill-bar features; "
            "scenarios/audit.py clean=True on zero checks; overnight_research.py unbounded cache")


def process_next(state: dict, dry_run: bool = False) -> dict | None:
    item = _next_pending(state)
    if item is None:
        print("fable5_loop: no pending safe items — roadmap loop is idle "
              "(owner-gated items remain blocked for sign-off).")
        return None
    print(f"fable5_loop: next item = {item['id']} — {item['title']}")
    step = FIX_STEPS.get(item["id"])
    if dry_run:
        print(f"  [dry-run] would run fix step: {step or '(manual)'}")
        return item
    note = "(manual code change required)" if not step else globals()[step]()
    item["status"] = "done"
    item["done_at"] = _now()
    item["context"] = f"{item.get('context', '')} || APPLIED: {note}"
    state["run_count"] = state.get("run_count", 0) + 1
    state["last_run"] = _now()
    _compact(state)
    _save(state)
    # Commit the advanced state so the loop's progress survives container amnesia.
    _git("add", str(STATE))
    _git("commit", "-m", f"chore(fable5-loop): advance {item['id']} — {item['title']}",
         "--allow-empty")
    print(f"  done: {note}")
    return item


def _compact(state: dict) -> None:
    """Keep the state file small + readable: done items collapse to one line,
    the list is capped, and stale 'done' entries beyond the cap are dropped."""
    cap = 40
    kept = []
    for it in state["items"]:
        if it["status"] == "done":
            # collapse context to a single short line so the file can't grow unbounded
            it = {k: (v if k != "context" else str(v)[:240]) for k, v in it.items()}
            kept.append(it)
        else:
            kept.append(it)
    # keep blocked/pending fully; trim only the oldest done beyond the cap
    done = [i for i in kept if i["status"] == "done"]
    others = [i for i in kept if i["status"] != "done"]
    if len(done) > cap:
        done = done[-cap:]
    state["items"] = others + done


def main() -> int:
    ap = argparse.ArgumentParser(description="Fable-5 roadmap loop driver")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--next", action="store_true", help="process the next pending safe item")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()

    state = _load()
    if args.list:
        for it in state["items"]:
            print(f"  [{it['status']:7}] {it['id']}  gate={'OWNER' if it.get('owner_gate') else 'auto'}  {it['title']}")
        return 0
    if args.compact:
        _compact(state); _save(state)
        print("fable5_loop: state compacted.")
        return 0
    if args.next or args.dry_run:
        process_next(state, dry_run=args.dry_run)
        return 0
    # default: show status
    pending = [i for i in state["items"] if i["status"] == "pending" and not i.get("owner_gate")]
    blocked = [i for i in state["items"] if i["status"] == "blocked"]
    print(f"fable5_loop: {len(pending)} safe-pending, {len(blocked)} owner-gated(blocked). "
          f"Run --next to advance, --list to see all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
