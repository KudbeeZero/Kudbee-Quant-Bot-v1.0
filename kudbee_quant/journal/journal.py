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
#   bracket      : entry/stop/target/direction; target-first = win (+target_r R),
#                  stop-first = loss (-1R); time-stop marks to close in R
KINDS = {"touch", "reach_above", "reach_below", "stay_below", "stay_above", "bracket"}

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
    # bracket-only fields:
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    direction: float = 0.0      # +1 long / -1 short
    target_r: float | None = None
    outcome_r: float | None = None  # realized R when resolved

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

    def _evaluate(self, p: Prediction) -> tuple[str, float | None]:
        """Return (status, outcome_r) by checking price since creation.

        status is 'hit'/'miss'/'open'; outcome_r is the realized R for bracket
        predictions (None otherwise).
        """
        now = datetime.now(timezone.utc)
        df = self.client.klines(p.symbol, interval=p.timeframe, limit=1000)
        window = df[pd.to_datetime(df["timestamp"], utc=True) >= datetime.fromisoformat(p.created_at)]
        deadline_passed = now >= p.deadline
        if window.empty:
            return ("miss", None) if deadline_passed else ("open", None)

        if p.kind == "bracket":
            return self._evaluate_bracket(p, window, deadline_passed)

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
                return ("miss", None)
            return ("hit" if deadline_passed else "open", None)
        elif p.kind == "stay_above":
            violated = (low <= p.level).any()
            if violated:
                return ("miss", None)
            return ("hit" if deadline_passed else "open", None)
        else:  # pragma: no cover
            return ("open", None)

        if hit:
            return ("hit", None)
        return ("miss" if deadline_passed else "open", None)

    def _evaluate_bracket(self, p: Prediction, window, deadline_passed: bool) -> tuple[str, float | None]:
        """Resolve a stop/target bracket: which level is hit first, in R."""
        risk = abs(p.entry - p.stop)
        if risk <= 0:
            return ("open", None)
        for _, bar in window.iterrows():
            if p.direction > 0:
                if bar["low"] <= p.stop:            # stop first (conservative)
                    return ("miss", -1.0)
                if bar["high"] >= p.target:
                    return ("hit", float(p.target_r))
            else:
                if bar["high"] >= p.stop:
                    return ("miss", -1.0)
                if bar["low"] <= p.target:
                    return ("hit", float(p.target_r))
        if deadline_passed:                          # time-stop: mark to last close
            r = p.direction * (float(window["close"].iloc[-1]) - p.entry) / risk
            return ("hit" if r > 0 else "miss", float(r))
        return ("open", None)

    def check_open(self) -> list[Prediction]:
        """Re-evaluate every open prediction; persist newly-resolved ones."""
        changed = []
        for p in self.predictions:
            if p.status != "open":
                continue
            status, outcome_r = self._evaluate(p)
            if status in ("hit", "miss"):
                p.status = status
                p.outcome_r = outcome_r
                p.resolved_at = datetime.now(timezone.utc).isoformat()
                changed.append(p)
        if changed:
            self.save()
        return changed

    def scorecard(self) -> pd.DataFrame:
        """Per-setup record over RESOLVED predictions: hit rate + R expectancy."""
        resolved = [p for p in self.predictions if p.status in ("hit", "miss")]
        if not resolved:
            return pd.DataFrame(columns=["setup", "n", "hits", "hit_rate", "expectancy_r", "total_r"])
        df = pd.DataFrame([{"setup": p.setup or "(unlabeled)", "hit": p.status == "hit",
                            "r": p.outcome_r} for p in resolved])
        rows = []
        for setup, g in df.groupby("setup"):
            rs = g["r"].dropna()
            rows.append({"setup": setup, "n": len(g), "hits": int(g["hit"].sum()),
                         "hit_rate": g["hit"].mean(),
                         "expectancy_r": float(rs.mean()) if len(rs) else float("nan"),
                         "total_r": float(rs.sum()) if len(rs) else float("nan")})
        return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)
