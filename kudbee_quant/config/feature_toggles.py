"""Telegram feature toggles — read an opt-in flag from the env OR a small JSON file.

Precedence (highest first):
  1. The env var (e.g. ``TELEGRAM_SIGNAL_CARDS_ENABLED``) — the deploy-level switch set
     in GitHub Actions secrets / the Render dashboard. If set, it WINS (so ops can force
     a feature on/off regardless of the file).
  2. ``data/feature_flags.json`` — a `{logical_name: bool}` map. This is what the Telegram
     ``/enable`` / ``/disable`` admin commands write, so the owner can flip a feature from
     their phone without touching a dashboard.
  3. The hard default (``False`` — everything is opt-in).

CROSS-ENVIRONMENT NOTE (honest): the Render webhook (where ``/enable`` runs) and the
GitHub-Actions cron (where the alerts fire) are SEPARATE machines. A flag written to the
file on one is only seen by the other once the file is committed to the repo. So env vars
remain the authoritative cross-env switch; the file toggle is authoritative within whatever
environment reads it (and for the cron once the file is committed). Never raises.
"""
from __future__ import annotations

import json
from pathlib import Path

KNOWN_FLAGS = {
    "signal_cards": "TELEGRAM_SIGNAL_CARDS_ENABLED",
    "live_tracker": "TELEGRAM_LIVE_TRACKER_ENABLED",
    "session_brief": "TELEGRAM_SESSION_BRIEF_ENABLED",
    "skip_reporter": "TELEGRAM_SKIP_REPORTER_ENABLED",
    "weekly_digest": "TELEGRAM_WEEKLY_DIGEST_ENABLED",
}

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
DEFAULT_PATH = "data/feature_flags.json"


def _env_value(env_name: str) -> str | None:
    from .secrets import get_secret
    s = get_secret(env_name, required=False)
    return s.reveal().strip().lower() if s else None


def _file_flags(path: str = DEFAULT_PATH) -> dict:
    try:
        data = json.loads(Path(path).read_text())
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 — missing/corrupt file -> no file flags
        return {}


def is_enabled(name: str, *, path: str = DEFAULT_PATH, default: bool = False) -> bool:
    """Effective on/off for a logical flag (``"signal_cards"`` …): env wins, then file."""
    env_name = KNOWN_FLAGS.get(name, name)
    v = _env_value(env_name)
    if v is not None:
        return v in _TRUE
    flags = _file_flags(path)
    if name in flags:
        return bool(flags[name])
    return default


def set_flag(name: str, value: bool, *, path: str = DEFAULT_PATH) -> dict:
    """Write ``name -> value`` into the JSON file (creating it). Returns the full map.
    Raises ``KeyError`` for an unknown flag so a typo'd ``/enable`` is reported, not silently
    swallowed."""
    if name not in KNOWN_FLAGS:
        raise KeyError(name)
    flags = _file_flags(path)
    flags[name] = bool(value)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(flags, indent=2, sort_keys=True))
    return flags


def all_flags(*, path: str = DEFAULT_PATH) -> dict:
    """Effective state of every known flag (for ``/gates`` / ``/status``)."""
    return {name: is_enabled(name, path=path) for name in KNOWN_FLAGS}
