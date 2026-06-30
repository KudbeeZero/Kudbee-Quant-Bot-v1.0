"""Tests for the skip reporter (F5): reasons, create-only write, read-back, silent ping."""
import kudbee_quant.notifications.skip_reporter as sr
from kudbee_quant.notifications.skip_reporter import (
    count_by_gate, format_skip, read_skips, reason_for, record_skip,
)


def test_reason_for_each_gate():
    assert "ADR 80%" in reason_for("_adr", {"value": 0.80, "threshold": 0.75})
    assert "longs" in reason_for("_dxy", {"direction": 1})
    assert "shorts" in reason_for("_dxy", {"direction": -1})
    assert "win on 7" in reason_for("_fp", {"bucket": "b", "value": 0.3, "n": 7})
    assert "correlation" in reason_for("_cg", {"peer": "ETHUSDT", "value": 0.9})
    assert "Circuit breaker" in reason_for("_dcb", {"value": -4.0})


def test_record_and_read_round_trip(tmp_path):
    d = str(tmp_path / "skips")
    rec = record_skip("BTCUSDT", 1.0, "_adr", {"value": 0.8, "threshold": 0.75},
                      bracket={"entry": 100, "stop": 99}, skips_dir=d, notify=False,
                      ts="2026-06-30T12:00:00+00:00")
    assert rec["symbol"] == "BTCUSDT" and rec["direction"] == "LONG"
    assert rec["bracket_entry"] == 100
    back = read_skips(skips_dir=d)
    assert len(back) == 1 and back[0]["blocking_gate"] == "_adr"
    assert count_by_gate(back) == {"_adr": 1}


def test_read_skips_since_filter(tmp_path):
    d = str(tmp_path / "skips")
    record_skip("A", 1.0, "_dxy", {"direction": 1}, skips_dir=d, notify=False, ts="2026-06-01T00:00:00+00:00")
    record_skip("B", 1.0, "_fp", {"value": 0.2, "n": 6}, skips_dir=d, notify=False, ts="2026-06-29T00:00:00+00:00")
    recent = read_skips("2026-06-15T00:00:00+00:00", skips_dir=d)
    assert len(recent) == 1 and recent[0]["symbol"] == "B"


def test_record_skip_sends_silent_ping(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(sr, "telegram_enabled", lambda: True)
    monkeypatch.setattr(sr, "send_telegram",
                        lambda t, **k: captured.update(text=t, silent=k.get("disable_notification")) or True)
    record_skip("ETHUSDT", -1.0, "_cg", {"peer": "BTCUSDT", "value": 0.9},
                skips_dir=str(tmp_path / "skips"))
    assert captured["silent"] is True
    assert "SIGNAL SKIPPED — ETHUSDT SHORT" in captured["text"]


def test_format_skip_includes_value_threshold():
    out = format_skip({"symbol": "BTCUSDT", "direction": 1, "blocking_gate": "_adr",
                       "skip_reason": "ADR 80% consumed", "gate_value": 0.8, "gate_threshold": 0.75})
    assert "Value: 0.8 (threshold: 0.75)" in out


def test_read_skips_missing_dir_is_empty(tmp_path):
    assert read_skips(skips_dir=str(tmp_path / "nope")) == []
