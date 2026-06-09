"""Prediction journal storage + verification (see package docstring)."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ..ingest import BinanceClient

# Prediction kinds and how each is verified against OHLCV over the window:
#   touch        : a bar's [low, high] contains the level             -> hit
#   reach_above  : any high >= level                                  -> hit
#   reach_below  : any low  <= level                                  -> hit
#   stay_below   : all highs < level for the whole window             -> hit
#   stay_above   : all lows  > level for the whole window             -> hit
KINDS = {"touch", "reach_above", "reach_below", "stay_below", "stay_above"}

DEFAULT_PATH = Path("data/journal.json")


@dataclass
class Prediction:
    symbol: str                 # Binance symbol, e.g. ZECUSDT
    kind: str                   # one of KINDS
    level: float
    deadline_days: float
    setup: str = ""             # free label, e.g. "vector_at_daily_open_recovery"
    timeframe: str = "1h"
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "open"        # open | hit | miss
    resolved_at: str | None = None

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")

    @property
    def deadline(self) -> datetime:
        return datetime.fromisoformat(self.created_at) + timedelta(days=self.deadline_days)


class TradeJournal:
    def __init__(self, path: Path | str = DEFAULT_PATH, client: BinanceClient | None = None):
        self.path = Path(path)
        self.client = client or BinanceClient()
        self.predictions: list[Prediction] = []
        self._load()

    def _load(self):
        if self.path.exists():
            self.predictions = [Prediction(**d) for d in json.loads(self.path.read_text())]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(p) for p in self.predictions], indent=2))

    def add(self, prediction: Prediction) -> Prediction:
        self.predictions.append(prediction)
        self.save()
        return prediction

    def _evaluate(self, p: Prediction) -> str:
        """Return 'hit', 'miss', or 'open' by checking price since creation."""
        now = datetime.now(timezone.utc)
        df = self.client.klines(p.symbol, interval=p.timeframe, limit=1000)
        window = df[pd.to_datetime(df["timestamp"], utc=True) >= datetime.fromisoformat(p.created_at)]
        deadline_passed = now >= p.deadline
        if window.empty:
            return "miss" if deadline_passed else "open"

        high, low = window["high"], window["low"]
        if p.kind == "touch":
            hit = ((low <= p.level) & (high >= p.level)).any()
        elif p.kind == "reach_above":
            hit = (high >= p.level).any()
        elif p.kind == "reach_below":
            hit = (low <= p.level).any()
        elif p.kind == "stay_below":
            violated = (high >= p.level).any()
            if violated:
                return "miss"
            return "hit" if deadline_passed else "open"
        elif p.kind == "stay_above":
            violated = (low <= p.level).any()
            if violated:
                return "miss"
            return "hit" if deadline_passed else "open"
        else:  # pragma: no cover
            return "open"

        if hit:
            return "hit"
        return "miss" if deadline_passed else "open"

    def check_open(self) -> list[Prediction]:
        """Re-evaluate every open prediction; persist newly-resolved ones."""
        changed = []
        for p in self.predictions:
            if p.status != "open":
                continue
            result = self._evaluate(p)
            if result in ("hit", "miss"):
                p.status = result
                p.resolved_at = datetime.now(timezone.utc).isoformat()
                changed.append(p)
        if changed:
            self.save()
        return changed

    def scorecard(self) -> pd.DataFrame:
        """Hit rate by setup label over RESOLVED predictions only (honest)."""
        resolved = [p for p in self.predictions if p.status in ("hit", "miss")]
        if not resolved:
            return pd.DataFrame(columns=["setup", "n", "hits", "hit_rate"])
        df = pd.DataFrame([{"setup": p.setup or "(unlabeled)", "hit": p.status == "hit"} for p in resolved])
        g = df.groupby("setup")["hit"].agg(["count", "sum"]).reset_index()
        g.columns = ["setup", "n", "hits"]
        g["hit_rate"] = g["hits"] / g["n"]
        return g.sort_values("n", ascending=False).reset_index(drop=True)
