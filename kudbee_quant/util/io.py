"""Crash-safe file IO used by the lightweight JSON data stores.

Several stores (biases, reflection, loop-agent state, drawdown guard, heartbeat,
vector log) were writing with a bare ``Path.write_text`` — a crash mid-write could
leave a truncated file that the next run loads as corrupt/empty. This mirrors the
atomic tmp+replace pattern already used by :class:`TradeJournal.save` so every store
is safe by default.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def atomic_write_json(path: str | Path, obj: Any, *, indent: int = 2) -> None:
    """Write ``obj`` as JSON atomically: temp file + ``replace`` (never in place).

    Missing parent dirs are created. A write error leaves the previous good file
    untouched (we only ``replace`` after a clean write).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, default=str))
    tmp.replace(path)


def load_json(path: str | Path, *, default: Any = None) -> Any:
    """Tolerant load: missing/corrupt JSON returns ``default`` (never raises)."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("load_json: could not read %s (%s) — using default", path, e)
        return default
