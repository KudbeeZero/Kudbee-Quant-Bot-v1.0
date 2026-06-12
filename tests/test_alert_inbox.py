"""Alert inbox: hosted TV alerts -> repo -> scored journal (no network)."""
import json

import pytest

from kudbee_quant import alert_inbox
from kudbee_quant.alert_inbox import (
    ingest_inbox, inbox_entry, log_alert, push_inbox_entry, valid_alert,
)
from kudbee_quant.journal import TradeJournal


def _alert(**kw):
    base = {"symbol": "ETHUSDT", "direction": 1.0, "entry": 2500.0, "stop": 2450.0,
            "target": 2650.0, "target_r": 3.0, "conf": 0.6, "tf": "1h", "note": "tv"}
    base.update(kw)
    return base


def test_inbox_entry_refuses_token_and_has_stable_id():
    with pytest.raises(ValueError):
        inbox_entry({**_alert(), "token": "secret"})
    e = inbox_entry(_alert())
    assert len(e["id"]) == 16 and e["alert"]["symbol"] == "ETHUSDT"
    assert "token" not in json.dumps(e)


def test_log_alert_human_provenance_and_inbox_dedupe(tmp_path):
    j = TradeJournal(path=tmp_path / "j.json")
    p = log_alert(j, _alert(), "abc123")
    assert p is not None and p.source == "human" and p.status == "pending"
    assert "inbox=abc123" in p.note
    # Same inbox id re-delivered -> skipped (idempotent ingest).
    assert log_alert(j, _alert(symbol="SOLUSDT"), "abc123") is None
    # Different id but same symbol+tf already pending -> bot's duplicate rule.
    assert log_alert(j, _alert(), "def456") is None


def test_ingest_inbox_consumes_valid_and_quarantines_malformed(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    e = inbox_entry(_alert())
    (inbox / f"{e['id']}.json").write_text(json.dumps(e))
    (inbox / "broken.json").write_text("{not json")
    bad = inbox_entry(_alert(symbol="BTCUSDT", direction=0.0))  # invalid: dir 0
    (inbox / f"{bad['id']}.json").write_text(json.dumps(bad))

    j = TradeJournal(path=tmp_path / "j.json")
    added = ingest_inbox(j, inbox_dir=inbox)
    assert [p.symbol for p in added] == ["ETHUSDT"]
    assert not (inbox / f"{e['id']}.json").exists()          # consumed
    assert (inbox / "broken.rejected").exists()              # quarantined
    assert (inbox / f"{bad['id']}.rejected").exists()
    # Re-delivery of the same entry is skipped but still consumed.
    (inbox / f"{e['id']}.json").write_text(json.dumps(e))
    assert ingest_inbox(j, inbox_dir=inbox) == []
    assert not (inbox / f"{e['id']}.json").exists()
    assert len([p for p in j.predictions if p.symbol == "ETHUSDT"]) == 1


def test_ingest_inbox_missing_dir_is_noop(tmp_path):
    j = TradeJournal(path=tmp_path / "j.json")
    assert ingest_inbox(j, inbox_dir=tmp_path / "nope") == []


def test_valid_alert_rejects_garbage():
    assert valid_alert(_alert())
    assert not valid_alert({})
    assert not valid_alert(_alert(direction=0))
    assert not valid_alert(_alert(entry=-1))
    assert not valid_alert(_alert(tf="9h"))


def test_push_without_gh_token_is_local_only_no_network(monkeypatch):
    monkeypatch.delenv("KUDBEE_GH_TOKEN", raising=False)
    monkeypatch.setattr("requests.put",
                        lambda *a, **k: pytest.fail("network call without token"))
    assert push_inbox_entry(inbox_entry(_alert())) is False


def test_push_commits_to_repo_inbox_path(monkeypatch):
    monkeypatch.setenv("KUDBEE_GH_TOKEN", "ghtok")
    monkeypatch.setenv("KUDBEE_GH_REPO", "Owner/Repo")
    calls = {}

    class _Resp:
        status_code = 201

    def fake_put(url, headers=None, json=None, timeout=None):
        calls.update(url=url, headers=headers, payload=json)
        return _Resp()

    monkeypatch.setattr("requests.put", fake_put)
    e = inbox_entry(_alert())
    assert push_inbox_entry(e) is True
    assert calls["url"].endswith(f"/repos/Owner/Repo/contents/data/alert_inbox/{e['id']}.json")
    assert "[skip ci]" in calls["payload"]["message"]
    # Neither the GH token nor any API token leaks into the committed content.
    assert "ghtok" not in json.dumps(calls["payload"])


def test_push_failure_is_swallowed(monkeypatch):
    monkeypatch.setenv("KUDBEE_GH_TOKEN", "ghtok")

    def boom(*a, **k):
        raise OSError("github down")

    monkeypatch.setattr("requests.put", boom)
    assert push_inbox_entry(inbox_entry(_alert())) is False


def test_alert_endpoint_reports_inbox_flag(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    import kudbee_quant.api as api
    from kudbee_quant.api_security import _reset_rate_limits

    monkeypatch.setattr(api, "TradeJournal", lambda: TradeJournal(path=tmp_path / "j.json"))
    monkeypatch.setenv("KUDBEE_API_TOKEN", "testtoken")
    monkeypatch.delenv("KUDBEE_GH_TOKEN", raising=False)
    _reset_rate_limits()
    client = TestClient(api.app)
    payload = {**_alert(), "token": "testtoken"}
    r = client.post("/api/alert", json=payload)
    assert r.status_code == 200 and r.json()["logged"]
    assert r.json()["inbox"] is False          # no GH token -> host-local only

    monkeypatch.setattr(api, "push_inbox_entry", lambda entry: True)
    _reset_rate_limits()
    r2 = client.post("/api/alert", json={**payload, "symbol": "SOLUSDT"})
    assert r2.status_code == 200 and r2.json()["inbox"] is True
