"""Phone-settable control state — currently a manual trading pause (/pause /resume).

Lives in a COMMITTED file (``data/control.json``, NOT gitignored) so the GitHub-Actions
cron — a separate machine from the Render webhook — honors a pause set from Telegram once
the change reaches the repo (the webhook commits it via the GitHub contents API; see
``telegram_commands._persist_to_repo``). All reads are fail-open (missing/corrupt file ->
NOT paused), so ``paper_scan`` is byte-identical by default.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = "data/control.json"


def _load(path: str = DEFAULT_PATH) -> dict:
    try:
        d = json.loads(Path(path).read_text())
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001 — missing/corrupt -> no control state
        return {}


def is_paused(path: str = DEFAULT_PATH) -> bool:
    return bool(_load(path).get("manual_pause", False))


def status(path: str = DEFAULT_PATH) -> dict:
    d = _load(path)
    return {"manual_pause": bool(d.get("manual_pause", False)),
            "reason": d.get("reason"), "since": d.get("since")}


def set_paused(value: bool, *, reason: str | None = None, since: str | None = None,
               path: str = DEFAULT_PATH) -> dict:
    """Persist the manual-pause flag. Returns the written dict."""
    d = _load(path)
    d["manual_pause"] = bool(value)
    if value:
        d["reason"] = reason or "manual /pause"
        if since:
            d["since"] = since
    else:
        d.pop("reason", None)
        d.pop("since", None)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, sort_keys=True))
    return d
