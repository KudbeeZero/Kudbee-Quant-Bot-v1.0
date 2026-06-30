"""Skip reporter (F5) — record + (silently) announce a signal a gate blocked.

Two side effects, both default-off/fail-open:
  1. A create-only JSONL file ``data/skips/<UTC-ts>-<id>.jsonl`` (one record). Create-only
     mirrors ``data/alert_inbox`` — the race-safe pattern for the 4×/hour cron, so an
     append-only log never conflicts. The weekly digest (F6) and session brief (F3) read these.
  2. A SILENT Telegram ping (``disable_notification=True``) so it lands in the chat without buzzing.

``reason_for(gate, ctx)`` centralises the human-readable per-gate strings. Writing is gated by
``TELEGRAM_SKIP_REPORTER_ENABLED`` (or the ``skip_reporter`` toggle). The session sizer never
blocks, so it has no skip reason.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .telegram import send_telegram, telegram_enabled

SKIPS_DIR = "data/skips"


def reason_for(gate: str, ctx: dict) -> str:
    """Human-readable reason for a skip by ``gate`` given its in-scope ``ctx`` values."""
    g = gate.lstrip("_")
    try:
        if g == "adr":
            return (f"ADR {ctx.get('value', 0) * 100:.0f}% consumed — "
                    f"exceeds {ctx.get('threshold', 0) * 100:.0f}% threshold")
        if g == "dxy":
            d = ctx.get("direction", 0)
            if d > 0:
                return "DXY RISK_OFF (dollar uptrend) — blocking crypto longs"
            return "DXY RISK_ON (dollar downtrend) — blocking crypto shorts"
        if g == "fp":
            return (f"Fingerprint bucket {ctx.get('bucket', '?')}: "
                    f"{ctx.get('value', 0) * 100:.0f}% win on {ctx.get('n', 0)} trades — below floor")
        if g == "cg":
            return (f"{ctx.get('peer', '?')} already open same-direction "
                    f"({ctx.get('value', 0):.2f} correlation)")
        if g == "dcb":
            return f"Circuit breaker ACTIVE — rolling {ctx.get('value', 0):+.2f}R"
    except Exception:  # noqa: BLE001
        pass
    return f"Blocked by {gate}"


def skip_reporter_enabled() -> bool:
    from ..config.feature_toggles import is_enabled
    return is_enabled("skip_reporter")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_skip(rec: dict) -> str:
    d = rec.get("direction")
    side = d if isinstance(d, str) else ("LONG" if (d or 0) > 0 else "SHORT")
    val, thr = rec.get("gate_value"), rec.get("gate_threshold")
    vt = ""
    if val is not None:
        vt = f"\nValue: {val} (threshold: {thr})" if thr is not None else f"\nValue: {val}"
    return (f"⛔ SIGNAL SKIPPED — {rec.get('symbol', '?')} {side}\n"
            f"Gate: {rec.get('blocking_gate', '?')}\n"
            f"Reason: {rec.get('skip_reason', '')}{vt}")


def record_skip(symbol: str, direction: float, gate: str, ctx: dict | None = None,
                *, bracket: dict | None = None, skips_dir: str = SKIPS_DIR,
                ts: str | None = None, write: bool = True, notify: bool = True) -> dict:
    """Build a skip record, persist it (create-only) and send a silent ping. Returns the
    record. Never raises — a reporting failure must never affect the scan."""
    ctx = ctx or {}
    rec = {
        "ts": ts or _now_iso(),
        "symbol": symbol,
        "direction": "LONG" if (direction or 0) > 0 else "SHORT",
        "blocking_gate": gate,
        "skip_reason": reason_for(gate, ctx),
        "gate_value": ctx.get("value"),
        "gate_threshold": ctx.get("threshold"),
    }
    if bracket:
        rec.update({f"bracket_{k}": v for k, v in bracket.items()})
    try:
        if write:
            d = Path(skips_dir)
            d.mkdir(parents=True, exist_ok=True)
            fn = f"{rec['ts'].replace(':', '').replace('+00:00', 'Z')}-{uuid.uuid4().hex[:6]}.jsonl"
            (d / fn).write_text(json.dumps(rec) + "\n")
        if notify and telegram_enabled():
            send_telegram(format_skip(rec), disable_notification=True)
    except Exception:  # noqa: BLE001
        pass
    return rec


def read_skips(since_iso: str | None = None, *, skips_dir: str = SKIPS_DIR) -> list[dict]:
    """All skip records (optionally since ``since_iso``). Fail-open to []."""
    out: list[dict] = []
    try:
        d = Path(skips_dir)
        if not d.exists():
            return out
        for f in d.glob("*.jsonl"):
            try:
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if since_iso is None or str(rec.get("ts", "")) >= since_iso:
                        out.append(rec)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        return out
    return out


def count_by_gate(records: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for r in records:
        g = r.get("blocking_gate", "?")
        counts[g] = counts.get(g, 0) + 1
    return counts
