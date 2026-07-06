"""The scheduled emitters must say WHY they sent nothing (§86 Telegram audit).

Every telegram-scheduled.yml job runs `... || true`, so a green run with
"0 update(s)" / "skipped" was indistinguishable from a working feature with
nothing to report — the whole scheduled suite sat silently disabled for weeks.
These pin the diagnosable log line: when the feature flag is OFF, the CLI entry
points must name the flag and how to enable it.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def _flags_off(monkeypatch, tmp_path):
    """Force every toggle source off: no env switches, empty flags file, tmp cwd."""
    for env in (
        "TELEGRAM_LIVE_TRACKER_ENABLED",
        "TELEGRAM_SESSION_BRIEF_ENABLED",
        "TELEGRAM_DAILY_RECAP_ENABLED",
        "TELEGRAM_WEEKLY_RECAP_ENABLED",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.chdir(tmp_path)  # no data/feature_flags.json here -> hard default False


def test_trade_tracker_zero_names_the_flag(_flags_off, capsys):
    from kudbee_quant.notifications.trade_tracker import _main
    assert _main([]) == 0
    out = capsys.readouterr().out
    assert "live_tracker" in out and "OFF" in out
    assert "TELEGRAM_LIVE_TRACKER_ENABLED" in out


def test_session_brief_skip_names_the_flag(_flags_off, capsys):
    from kudbee_quant.notifications.session_brief import _main
    assert _main(["--session", "london"]) == 0
    out = capsys.readouterr().out
    assert "session_brief" in out and "OFF" in out


def test_recap_skips_name_their_flags(_flags_off, capsys):
    from kudbee_quant.notifications.recap import _main
    assert _main(["--daily", "--weekly"]) == 0
    out = capsys.readouterr().out
    assert "daily_recap" in out and "weekly_recap" in out and "OFF" in out


def test_dry_run_still_prints_plain_line(_flags_off, capsys):
    """--dry-run forces emission, so the OFF hint must NOT appear."""
    from kudbee_quant.notifications.trade_tracker import _main
    assert _main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "OFF" not in out
