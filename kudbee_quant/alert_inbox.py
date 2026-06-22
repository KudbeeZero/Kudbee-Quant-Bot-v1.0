"""TradingView alert inbox — how hosted webhook alerts reach the scored journal.

The journal of record is ``data/journal.json`` IN THE REPO, advanced by the
hourly paper-trade Action. A hosted API (Render) writes only to its own
ephemeral checkout — wiped on every redeploy, and redeploys happen on every
journal commit (hourly). So ``/api/alert`` alone would show alerts on the
dashboard but never score them.

This module closes that loop without ever touching the bot-owned journal from
the host:

  TV alert -> /api/alert (host)
      -> local journal add        (instant dashboard feedback; ephemeral)
      -> push_inbox_entry()       (commits data/alert_inbox/<id>.json to the
                                   repo via the GitHub contents API — create-only
                                   unique paths, so no races with the bot)
  hourly Action -> ``cli ingest-alerts`` -> ingest_inbox()
      -> same Prediction logged in the REPO journal (source="human"),
         inbox file consumed; the normal scan/resolve/commit step scores it.

Idempotency: every alert gets a deterministic inbox id; the id is embedded in
the Prediction note (``inbox=<id>``), so re-delivered files are skipped on
ingest and a retried API PUT lands on the same path.

Security: the host needs ``KUDBEE_GH_TOKEN`` — a fine-grained PAT scoped to
THIS repo, contents read/write only. The token (and the API token) are never
written to inbox files, logs, or responses. No ``KUDBEE_GH_TOKEN`` configured
means alerts stay host-local (response carries ``"inbox": false`` so the
caller can tell).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .journal import Prediction, TradeJournal

INBOX_DIR = Path("data/alert_inbox")
_ALLOWED_TF = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"}
_GH_API = "https://api.github.com"


def inbox_entry(alert: dict) -> dict:
    """Wrap a sanitized alert payload (NO token field) as an inbox entry.

    The id is a hash of the payload + creation minute: deterministic enough
    that an in-request retry reuses the same repo path, unique enough that
    distinct alerts never collide.
    """
    if "token" in alert:
        raise ValueError("inbox entries must not carry the auth token")
    created_at = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(
        json.dumps({**alert, "created_at": created_at[:16]}, sort_keys=True).encode()
    ).hexdigest()[:16]
    return {"id": digest, "created_at": created_at, "alert": alert}


def valid_alert(alert: dict) -> bool:
    """Defensive re-validation at ingest time (inbox files are repo content;
    the API's pydantic model already validated what the host pushed)."""
    try:
        if not (0 < len(str(alert["symbol"])) <= 20):
            return False
        if float(alert["direction"]) == 0:
            return False
        if not all(float(alert[k]) > 0 for k in ("entry", "stop", "target")):
            return False
        if alert.get("tf", "1h") not in _ALLOWED_TF:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def log_alert(j: TradeJournal, alert: dict, inbox_id: str) -> Prediction | None:
    """Log one TV alert into a journal (host-local OR the repo's, at ingest).

    Returns None without logging if the inbox id was already ingested or a
    bracket is already open/pending on that symbol+timeframe — the same
    duplicate rule the bot uses.

    The setup tag defaults to ``tv_alert[_NNpct]`` but an ``alert["setup"]``
    override (set server-side, never from user free-text) lets other webhook
    sources tag their own book — e.g. the Telegram ``/trade`` command tags
    ``tg_manual``. The override travels in the inbox file, so the hourly
    ingest applies the same tag in the repo journal.
    """
    marker = f"inbox={inbox_id}"
    if any(marker in p.note for p in j.predictions):
        return None
    tf = alert.get("tf", "1h")
    open_keys = {(p.symbol, p.timeframe) for p in j.predictions
                 if p.status in ("open", "pending") and p.kind == "bracket"}
    if (alert["symbol"].upper(), tf) in open_keys:
        return None
    conf = alert.get("conf")
    setup = alert.get("setup") or "tv_alert" + (f"_{int(round(conf * 100))}pct" if conf else "")
    return j.add(Prediction(
        symbol=alert["symbol"].upper(), kind="bracket", level=alert["entry"],
        entry=alert["entry"], stop=alert["stop"], target=alert["target"],
        direction=1.0 if float(alert["direction"]) > 0 else -1.0,
        target_r=alert.get("target_r", 3.0), deadline_days=3.0, timeframe=tf,
        pending_limit=True, signal_price=alert["entry"],
        setup=setup,
        note=f"TradingView alert: {alert.get('note', '')}. conf={conf}. {marker}",
        source="human",
    ))


def push_inbox_entry(entry: dict) -> bool:
    """Commit the entry to ``data/alert_inbox/<id>.json`` in the repo via the
    GitHub contents API. Create-only unique path — never touches journal.json,
    so it cannot race the bot. Returns False (alert stays host-local) when no
    token is configured or the push fails; never raises, never logs the token.
    """
    token = os.environ.get("KUDBEE_GH_TOKEN", "")
    if not token:
        return False
    repo = os.environ.get("KUDBEE_GH_REPO", "KudbeeZero/Kudbee-Quant-Bot-v1.0")
    branch = os.environ.get("KUDBEE_GH_BRANCH", "main")
    body = json.dumps(entry, indent=2)
    try:
        import requests
        r = requests.put(
            f"{_GH_API}/repos/{repo}/contents/data/alert_inbox/{entry['id']}.json",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            json={"message": f"tv-alert: inbox {entry['id']} [skip ci]",
                  "branch": branch,
                  "content": base64.b64encode(body.encode()).decode()},
            timeout=8,
        )
        # 201 created; 422 = path already exists (a retry of the same alert) —
        # the entry is in the repo either way.
        return r.status_code in (200, 201, 422)
    except Exception:
        return False


def ingest_inbox(j: TradeJournal, inbox_dir: Path = INBOX_DIR) -> list[Prediction]:
    """Drain ``data/alert_inbox/`` into the journal (the hourly Action's step).

    Valid entries are logged (source="human") and their files deleted —
    the Action's commit step picks up both. Unparseable/invalid files are
    renamed ``*.rejected`` so they stop being retried but stay visible.
    """
    if not inbox_dir.exists():
        return []
    added: list[Prediction] = []
    for f in sorted(inbox_dir.glob("*.json")):
        try:
            entry = json.loads(f.read_text())
            alert = entry["alert"]
            if not valid_alert(alert):
                raise ValueError("invalid alert payload")
        except (ValueError, KeyError, TypeError):
            f.rename(f.with_suffix(".rejected"))
            print(f"alert-inbox: rejected {f.name} (malformed)")
            continue
        p = log_alert(j, alert, entry.get("id", f.stem))
        if p is not None:
            added.append(p)
            print(f"alert-inbox: ingested {f.name} -> {p.id} {p.symbol} ({p.status})")
        else:
            print(f"alert-inbox: skipped {f.name} (duplicate)")
        f.unlink()
    return added
