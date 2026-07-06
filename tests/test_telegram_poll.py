"""Tests for the no-server Telegram command poller (§86).

All Telegram HTTP is faked at the module's ``requests`` seam; the dispatch
handler is injected. Pins the three behaviors the design leans on: webhook
stand-down, gate+dispatch reuse, and the server-side ack that makes the
workflow stateless.
"""
from __future__ import annotations

import kudbee_quant.telegram_poll as tp


class _FakeResp:
    def __init__(self, payload):
        self.ok = True
        self._payload = payload

    def json(self):
        return self._payload


def _fake_api(monkeypatch, *, webhook_url="", updates=None):
    """Fake requests.get for getWebhookInfo/getUpdates; returns the call log."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url.rsplit("/", 1)[-1], dict(params or {})))
        if url.endswith("getWebhookInfo"):
            return _FakeResp({"ok": True, "result": {"url": webhook_url}})
        if url.endswith("getUpdates"):
            if "offset" in (params or {}):
                return _FakeResp({"ok": True, "result": []})   # the ack call
            return _FakeResp({"ok": True, "result": updates or []})
        raise AssertionError(f"unexpected call {url}")

    monkeypatch.setattr(tp.requests, "get", fake_get)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "999:TESTTOK")
    return calls


def test_no_token_is_a_clean_noop(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert tp.poll_once(handler=lambda u: "x") == 0
    assert "not set" in capsys.readouterr().out


def test_stands_down_when_webhook_registered(monkeypatch, capsys):
    calls = _fake_api(monkeypatch, webhook_url="https://app.fly.dev/api/telegram")
    assert tp.poll_once(handler=lambda u: "x") == 0
    assert "stands down" in capsys.readouterr().out
    assert [c[0] for c in calls] == ["getWebhookInfo"]   # never fetched updates


def test_dispatches_updates_and_acks_offset(monkeypatch):
    ups = [{"update_id": 7, "message": {"chat": {"id": 1}, "text": "/summary"}},
           {"update_id": 8, "message": {"chat": {"id": 1}, "text": "hi"}}]
    calls = _fake_api(monkeypatch, updates=ups)
    seen = []

    def handler(u):
        seen.append(u["update_id"])
        return "reply" if u["update_id"] == 7 else None   # non-command → None

    assert tp.poll_once(handler=handler) == 1
    assert seen == [7, 8]
    # The ack call confirms past the LAST update id, commands or not.
    ack = [p for m, p in calls if m == "getUpdates" and "offset" in p]
    assert ack and ack[0]["offset"] == 9


def test_one_bad_update_does_not_block_the_rest(monkeypatch):
    ups = [{"update_id": 1, "message": {"chat": {"id": 1}, "text": "/boom"}},
           {"update_id": 2, "message": {"chat": {"id": 1}, "text": "/ok"}}]
    _fake_api(monkeypatch, updates=ups)

    def handler(u):
        if u["update_id"] == 1:
            raise RuntimeError("boom")
        return "ok"

    assert tp.poll_once(handler=handler) == 1


def test_fill_event_fires_on_pending_to_open():
    """§86 addition: the pending→open edge pings once (the fill alert)."""
    from kudbee_quant.notifications import events as ev
    prev = {"trades": {"a": {"symbol": "SOLUSDT", "ur": None, "health": "healthy",
                             "tp1_touched": False, "tp1_filled": False,
                             "stop_touched": False, "dl_soon": False,
                             "status": "pending"}},
            "agg": {"n": 1, "winners": 0, "losers": 0, "unrealized_r": 0.0}}
    curr = {"trades": {"a": {**prev["trades"]["a"], "status": "open", "ur": 0.05}},
            "agg": prev["agg"]}
    evs = ev.diff_events(prev, curr)
    assert [e["type"] for e in evs] == ["filled"]
    assert "filled" in ev.format_event(evs[0]).lower()
    # And it latches: open→open must not re-fire.
    assert ev.diff_events(curr, curr) == []
