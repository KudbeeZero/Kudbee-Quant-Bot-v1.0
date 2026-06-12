"""deploy/journal_sync.py — the hosted API's journal reconciler.

Real git fixtures (a bare ``origin`` + a host clone), no network: the invariants
under test are exactly the ones the two-writer design depends on (origin wins
per id, host appends new ids, failed pushes self-heal on the next tick).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "journal_sync", Path(__file__).resolve().parents[1] / "deploy" / "journal_sync.py")
journal_sync = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(journal_sync)  # type: ignore[union-attr]


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _write_journal(repo: Path, entries: list[dict]) -> None:
    p = repo / "data" / "journal.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, indent=2))


@pytest.fixture()
def repos(tmp_path):
    """bare ``origin`` + ``writer`` (stands in for the GitHub Action) + ``host``."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)],
                   check=True, capture_output=True)
    writer = tmp_path / "writer"
    subprocess.run(["git", "clone", str(origin), str(writer)], check=True, capture_output=True)
    for who in ("writer",):
        _run(tmp_path / who, "config", "user.name", "test-bot")
        _run(tmp_path / who, "config", "user.email", "t@e.st")
    _write_journal(writer, [{"id": "aaa", "status": "pending"}])
    _run(writer, "add", "-A")
    _run(writer, "commit", "-m", "seed")
    _run(writer, "push", "origin", "main")
    host = tmp_path / "host"
    subprocess.run(["git", "clone", str(origin), str(host)], check=True, capture_output=True)
    _run(host, "config", "user.name", "test-host")
    _run(host, "config", "user.email", "h@o.st")
    return origin, writer, host


def _origin_journal(origin: Path, tmp_path: Path) -> list[dict]:
    out = subprocess.run(["git", "-C", str(origin), "show", "main:data/journal.json"],
                         check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def test_merge_origin_wins_per_id_and_appends_local_only():
    origin = [{"id": "aaa", "status": "hit"}, {"id": "bbb", "status": "pending"}]
    local = [{"id": "aaa", "status": "pending"},  # stale host copy — origin resolved it
             {"id": "ccc", "status": "pending"}]  # new TV alert, host-only
    merged, n = journal_sync.merge_journals(origin, local)
    assert n == 1
    assert merged[:2] == origin                   # origin order + records intact
    assert merged[2]["id"] == "ccc"


def test_noop_when_host_has_nothing_new(repos, tmp_path):
    origin, _writer, host = repos
    assert journal_sync.sync_once(host, "main") == "up-to-date"
    assert _origin_journal(origin, tmp_path) == [{"id": "aaa", "status": "pending"}]


def test_host_alert_reaches_origin(repos, tmp_path):
    origin, _writer, host = repos
    # /api/alert appends to the host's working-tree journal (uncommitted)
    _write_journal(host, [{"id": "aaa", "status": "pending"},
                          {"id": "tv1", "status": "pending", "source": "human"}])
    assert journal_sync.sync_once(host, "main") == "pushed 1"
    assert [p["id"] for p in _origin_journal(origin, tmp_path)] == ["aaa", "tv1"]


def test_bot_resolution_wins_over_stale_host_copy(repos, tmp_path):
    origin, writer, host = repos
    # bot resolves aaa + logs bbb and pushes (the hourly Action)
    _run(writer, "pull", "origin", "main")
    _write_journal(writer, [{"id": "aaa", "status": "hit", "outcome_r": 3.0},
                            {"id": "bbb", "status": "pending"}])
    _run(writer, "commit", "-am", "paper-trade: update journal")
    _run(writer, "push", "origin", "main")
    # meanwhile the host has a stale aaa + a new TV alert
    _write_journal(host, [{"id": "aaa", "status": "pending"},
                          {"id": "tv1", "status": "pending"}])
    assert journal_sync.sync_once(host, "main") == "pushed 1"
    merged = _origin_journal(origin, tmp_path)
    assert merged[0] == {"id": "aaa", "status": "hit", "outcome_r": 3.0}  # bot wins
    assert [p["id"] for p in merged] == ["aaa", "bbb", "tv1"]


def test_failed_push_state_self_heals_next_tick(repos, tmp_path):
    """A tick that committed locally but lost the push race must be absorbed
    cleanly by the next tick (reset to origin, re-merge, push)."""
    origin, writer, host = repos
    # simulate the stranded state: host committed tv1 locally, push never landed,
    # and origin moved on (bot pushed bbb)
    _write_journal(host, [{"id": "aaa", "status": "pending"},
                          {"id": "tv1", "status": "pending"}])
    _run(host, "commit", "-am", "tv-alert: stranded local commit")
    _run(writer, "pull", "origin", "main")
    _write_journal(writer, [{"id": "aaa", "status": "pending"},
                            {"id": "bbb", "status": "pending"}])
    _run(writer, "commit", "-am", "paper-trade: update journal")
    _run(writer, "push", "origin", "main")
    assert journal_sync.sync_once(host, "main") == "pushed 1"
    assert [p["id"] for p in _origin_journal(origin, tmp_path)] == ["aaa", "bbb", "tv1"]


def test_torn_local_read_skips_tick_without_reset(repos, tmp_path):
    origin, _writer, host = repos
    (host / "data" / "journal.json").write_text('[{"id": "tv1", ')   # mid-write
    assert journal_sync.sync_once(host, "main") == "local-unreadable (skipped)"
    # the partial write was NOT wiped by a reset — the in-flight writer owns it
    assert (host / "data" / "journal.json").read_text() == '[{"id": "tv1", '


def test_journal_path_env_override(tmp_path, monkeypatch):
    """KUDBEE_JOURNAL_PATH points TradeJournal at the volume clone when hosted."""
    from kudbee_quant.journal import TradeJournal
    target = tmp_path / "elsewhere" / "journal.json"
    monkeypatch.setenv("KUDBEE_JOURNAL_PATH", str(target))
    assert TradeJournal().path == target
    monkeypatch.delenv("KUDBEE_JOURNAL_PATH")
    assert TradeJournal().path == Path("data/journal.json")
