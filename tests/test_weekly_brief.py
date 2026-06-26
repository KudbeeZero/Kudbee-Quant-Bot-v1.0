"""Tests for the read-only weekly macro brief (kudbee_quant.notifications.weekly_brief).

CI-safe: format_weekly_brief is pure (no network). Guards:
  (a) the crypto-observation + 800-EMA candidate blocks import and are inert;
  (b) the brief renders, pulls real macro fields, and carries the HONEST status
      (both studies negative/inconclusive) + the not-wired/unverified caveats;
  (c) notify_weekly_brief no-ops (returns False) when Telegram is unconfigured.
"""
from __future__ import annotations

from kudbee_quant.intelligence.macro_context import (
    EMA_800_STUDY_CANDIDATE,
    TINO_CRYPTO_OBSERVATIONS,
)
from kudbee_quant.notifications import format_weekly_brief, notify_weekly_brief


def test_crypto_observations_are_inert_and_labelled():
    assert TINO_CRYPTO_OBSERVATIONS["instrument"] == "SOLUSDT Perp 42x"
    assert TINO_CRYPTO_OBSERVATIONS["verified"] is False
    assert TINO_CRYPTO_OBSERVATIONS["applies_to_live_book"] is False
    assert EMA_800_STUDY_CANDIDATE["status"] == "proposed_not_started"
    assert "pre_registration" in EMA_800_STUDY_CANDIDATE["requires"]


def test_brief_renders_with_real_fields_and_honest_status():
    text = format_weekly_brief()
    # pulls real macro fields
    assert "WEEKLY MACRO BRIEF" in text
    assert "CPI" in text and "DXY" in text
    # the SOL context is present and labelled crypto-only
    assert "SOL CRYPTO CONTEXT" in text
    # HONEST research status — both studies reported as negative/inconclusive
    assert "INCONCLUSIVE" in text  # DXY
    assert "REJECT" in text         # VAH
    assert "INERT" in text
    # explicit not-wired / unverified caveats
    assert "not wired" in text.lower()
    assert "unverified" in text.lower()


def test_brief_makes_no_edge_claim():
    text = format_weekly_brief().lower()
    # the brief must not assert a live edge; it states the opposite
    assert "nothing auto-executes" in text
    assert "not the bot's universe" in text  # FX bias disclaimed


def test_notify_weekly_brief_noop_without_creds(monkeypatch):
    # force "telegram not configured" and assert a clean False (no raise, no send)
    monkeypatch.setattr(
        "kudbee_quant.notifications.weekly_brief.telegram_enabled", lambda: False
    )
    assert notify_weekly_brief() is False
