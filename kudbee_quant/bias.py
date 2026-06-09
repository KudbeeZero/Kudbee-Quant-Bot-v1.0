"""Directional bias layer — the human read drives direction, the bot scalps it.

The model: a skilled discretionary read (Tino-style, or the trader's own) sets
the HIGH-PROBABILITY DIRECTION for a symbol ("SOL going down to ~62"). The bot
then takes only confluence-R scalps THAT AGREE with that bias — trading WITH the
identified momentum, never against it. Biases expire, so a stale read can't keep
driving trades. Persisted to data/biases.json (git-versioned memory).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PATH = Path("data/biases.json")


@dataclass
class Bias:
    symbol: str
    direction: float            # +1 long / -1 short
    target: float | None = None  # optional price target (the read's destination)
    note: str = ""              # the reasoning / confluences seen
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""        # ISO; empty -> default 1 day from creation

    def __post_init__(self):
        self.direction = 1.0 if float(self.direction) > 0 else -1.0
        if not self.expires_at:
            self.expires_at = (datetime.fromisoformat(self.created_at) + timedelta(days=1)).isoformat()

    @property
    def side(self) -> str:
        return "long" if self.direction > 0 else "short"

    @property
    def active(self) -> bool:
        return datetime.now(timezone.utc) < datetime.fromisoformat(self.expires_at)


class BiasBook:
    """Persistent store of directional biases (one active per symbol)."""

    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)
        self.biases: list[Bias] = []
        if self.path.exists():
            self.biases = [Bias(**d) for d in json.loads(self.path.read_text())]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(b) for b in self.biases], indent=2))

    def set(self, symbol: str, side: str, target: float | None = None,
            days: float = 1.0, note: str = "") -> Bias:
        symbol = symbol.upper()
        direction = 1.0 if side.lower() in ("long", "buy", "up", "+1", "1") else -1.0
        created = datetime.now(timezone.utc)
        b = Bias(symbol=symbol, direction=direction, target=target, note=note,
                 created_at=created.isoformat(),
                 expires_at=(created + timedelta(days=days)).isoformat())
        self.biases = [x for x in self.biases if x.symbol != symbol]  # replace
        self.biases.append(b)
        self.save()
        return b

    def get(self, symbol: str) -> Bias | None:
        for b in self.biases:
            if b.symbol == symbol.upper() and b.active:
                return b
        return None

    def active(self) -> list[Bias]:
        return [b for b in self.biases if b.active]

    def clear(self, symbol: str) -> bool:
        before = len(self.biases)
        self.biases = [b for b in self.biases if b.symbol != symbol.upper()]
        if len(self.biases) != before:
            self.save()
            return True
        return False
