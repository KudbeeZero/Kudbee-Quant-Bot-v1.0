"""End-to-end tests for scripts/commit_journal.sh — the robust journal push.

These reproduce the concurrent-writer race that was firing FALSE "hourly
paper-trade run FAILED" Telegram pings: two hourly Action runs land close
together, the second rebases onto the first's commit, and the per-run telemetry
files (data/heartbeat.json, data/notify_state.json — rewritten wholesale each
run) conflict. The old inline `git pull --rebase` died on that conflict under
`bash -e`. The script must instead:

  * auto-resolve ONLY the regenerable telemetry files in favour of this run,
  * still push the journal of record, and
  * fail loudly (and clean) on a GENUINE conflict outside telemetry
    (e.g. data/journal.json) — never fabricating a journal merge.

The tests build real throwaway git repos in a temp dir (no network, no creds);
they're skipped if git isn't on PATH.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "commit_journal.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="git and bash are required for the commit-journal race tests",
)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


def _init_identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "test-bot")
    _git(repo, "config", "user.email", "test@example.com")


def _write_data(repo: Path, *, journal: str, heartbeat: list[str], snapshot: dict) -> None:
    (repo / "data").mkdir(exist_ok=True)
    (repo / "data" / "journal.json").write_text(journal)
    (repo / "data" / "heartbeat.json").write_text(
        json.dumps({"history": heartbeat}, indent=1)
    )
    (repo / "data" / "notify_state.json").write_text(json.dumps(snapshot, indent=2))


def _setup_origin(tmp_path: Path) -> tuple[Path, Path]:
    """Create a bare origin with an initial main commit; return (origin, seed clone)."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))

    seed = tmp_path / "seed"
    _git(tmp_path, "clone", str(origin), str(seed))
    _init_identity(seed)
    _write_data(
        seed,
        journal='{"trades": ["t0"]}\n',
        heartbeat=["2026-01-01T00:00:00+00:00"],
        snapshot={"agg": {"n": 0}},
    )
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "seed")
    _git(seed, "push", "origin", "HEAD:main")
    return origin, seed


def _clone(origin: Path, dest: Path) -> Path:
    _git(dest.parent, "clone", str(origin), str(dest))
    _init_identity(dest)
    return dest


def _run_script(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        env={"PATH": __import__("os").environ["PATH"], "COMMIT_JOURNAL_ATTEMPTS": "5"},
    )


def test_telemetry_conflict_auto_resolves_and_pushes(tmp_path: Path) -> None:
    """The core race: a sibling run advanced origin's telemetry; our run must
    rebase past the conflict and still push its journal update."""
    origin, _ = _setup_origin(tmp_path)

    # Our run clones at C0, then a concurrent run advances origin (C1) by
    # rewriting BOTH telemetry files — exactly what every run does.
    ours = _clone(origin, tmp_path / "ours")
    other = _clone(origin, tmp_path / "other")

    _write_data(
        other,
        journal='{"trades": ["t0"]}\n',  # journal unchanged (the common case)
        heartbeat=["2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00"],
        snapshot={"agg": {"n": 1}},
    )
    _git(other, "add", "-A")
    _git(other, "commit", "-m", "other run")
    _git(other, "push", "origin", "HEAD:main")

    # Our run (still at C0) writes its OWN telemetry + a real journal update.
    _write_data(
        ours,
        journal='{"trades": ["t0", "t1-ours"]}\n',
        heartbeat=["2026-01-01T00:00:00+00:00", "2026-01-01T02:00:00+00:00"],
        snapshot={"agg": {"n": 2, "mine": True}},
    )

    result = _run_script(ours)
    assert result.returncode == 0, f"script failed:\nSTDOUT{result.stdout}\nSTDERR{result.stderr}"

    # Verify origin now carries OUR journal update (nothing lost), fetched fresh.
    verify = _clone(origin, tmp_path / "verify")
    pushed_journal = json.loads((verify / "data" / "journal.json").read_text())
    assert pushed_journal["trades"] == ["t0", "t1-ours"]
    # Our telemetry won the auto-resolution (--theirs == this run during rebase).
    pushed_snapshot = json.loads((verify / "data" / "notify_state.json").read_text())
    assert pushed_snapshot["agg"].get("mine") is True

    # The sibling's commit is still in history — we rebased on top, not over it.
    log = _git(verify, "log", "--oneline").stdout
    assert "other run" in log

    # No rebase left dangling in our working repo.
    assert not (ours / ".git" / "rebase-merge").exists()
    assert not (ours / ".git" / "rebase-apply").exists()


def test_genuine_journal_conflict_fails_loudly_and_cleanly(tmp_path: Path) -> None:
    """A real conflict OUTSIDE telemetry (journal.json) must NOT be silently
    merged: the script aborts the rebase cleanly and exits non-zero so the run's
    failure ping is a TRUE alarm."""
    origin, _ = _setup_origin(tmp_path)

    ours = _clone(origin, tmp_path / "ours")
    other = _clone(origin, tmp_path / "other")

    # Concurrent run changes the journal one way...
    _write_data(
        other,
        journal='{"trades": ["t0", "OTHER"]}\n',
        heartbeat=["2026-01-01T00:00:00+00:00", "x"],
        snapshot={"agg": {"n": 1}},
    )
    _git(other, "add", "-A")
    _git(other, "commit", "-m", "other journal")
    _git(other, "push", "origin", "HEAD:main")

    # ...our run changes the SAME journal line a different way -> true conflict.
    _write_data(
        ours,
        journal='{"trades": ["t0", "OURS"]}\n',
        heartbeat=["2026-01-01T00:00:00+00:00", "y"],
        snapshot={"agg": {"n": 2}},
    )

    result = _run_script(ours)
    assert result.returncode != 0, "a genuine journal conflict must fail loudly"
    assert "journal.json" in (result.stderr + result.stdout)

    # The rebase must be cleanly aborted — no dangling state, no corrupt tree.
    assert not (ours / ".git" / "rebase-merge").exists()
    assert not (ours / ".git" / "rebase-apply").exists()
    status = _git(ours, "status", "--porcelain").stdout
    assert "UU" not in status  # no unmerged paths left behind


def test_no_changes_is_a_clean_noop(tmp_path: Path) -> None:
    """When nothing changed, the script must exit 0 and push nothing."""
    origin, _ = _setup_origin(tmp_path)
    ours = _clone(origin, tmp_path / "ours")

    result = _run_script(ours)
    assert result.returncode == 0
    assert "No journal changes" in result.stdout
