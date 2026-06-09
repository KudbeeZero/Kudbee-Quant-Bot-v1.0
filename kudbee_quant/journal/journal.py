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
    # pending limit-order (retrace entry) lifecycle:
    pending_limit: bool = False     # True = limit at `entry` not yet filled
    signal_price: float | None = None  # close at signal time (for reference)
    fill_deadline_days: float = 0.5    # cancel the limit if unfilled in this window
    filled_at: str | None = None
    # partial profit-taking (TARGET ONE / TARGET TWO):
    tp1: float | None = None        # TARGET ONE price; `target` is TARGET TWO
    tp1_frac: float = 0.5           # fraction banked at TP1 (rest rides to TP2)
    be_after_tp1: bool = True       # move stop to breakeven once TP1 banks
    tp1_filled_at: str | None = None  # when TP1 banked (trade still open on rest)

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        if self.pending_limit and self.status == "open":
            self.status = "pending"   # limit orders start unfilled

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
        """Lifecycle of a (possibly pending limit) stop/target bracket, in R.

        For a pending limit order, first find the FILL (price reaches the limit
        within the fill window; else 'cancelled'/'pending'), then resolve which
        of stop/target hits first from the fill bar onward.
        """
        risk = abs(p.entry - p.stop)
        if risk <= 0:
            return ("cancelled" if p.pending_limit else "open", None)
        rows = window.reset_index(drop=True)
        ts = pd.to_datetime(rows["timestamp"], utc=True)

        # 1) FILL phase. Market orders fill at the first bar; limits wait.
        if p.pending_limit:
            fill_deadline = datetime.fromisoformat(p.created_at) + timedelta(days=p.fill_deadline_days)
            fill_i = None
            for i in range(len(rows)):
                if ts.iloc[i] >= fill_deadline:   # window closed before any fill
                    break
                bar = rows.iloc[i]
                if (p.direction > 0 and bar["low"] <= p.entry) or \
                   (p.direction < 0 and bar["high"] >= p.entry):
                    fill_i = i
                    break
            if fill_i is None:
                if datetime.now(timezone.utc) >= fill_deadline:
                    return ("cancelled", None)   # limit never filled -> no trade
                return ("pending", None)
        else:
            fill_i = -1   # resolve from the start

        # 2) RESOLVE phase from the bar after fill.
        if p.tp1 is not None:
            return self._resolve_partial(p, rows, fill_i, risk, deadline_passed)
        for i in range(fill_i + 1, len(rows)):
            bar = rows.iloc[i]
            if p.direction > 0:
                if bar["low"] <= p.stop:
                    return ("miss", -1.0)
                if bar["high"] >= p.target:
                    return ("hit", float(p.target_r))
            else:
                if bar["high"] >= p.stop:
                    return ("miss", -1.0)
                if bar["low"] <= p.target:
                    return ("hit", float(p.target_r))
        if deadline_passed:                          # time-stop: mark to last close
            r = p.direction * (float(rows["close"].iloc[-1]) - p.entry) / risk
            return ("hit" if r > 0 else "miss", float(r))
        return ("open", None)   # filled, not yet resolved

    def _resolve_partial(self, p, rows, fill_i, risk, deadline_passed) -> tuple[str, float | None]:
        """Scale-out resolution: bank ``tp1_frac`` at TARGET ONE, ride the rest to
        TARGET TWO; optionally move the stop to breakeven after TP1. Stateless
        recompute (like the rest of the journal) — returns the BLENDED R.
        """
        d = p.direction
        tp1_r = d * (p.tp1 - p.entry) / risk          # R of TARGET ONE from price
        target_r = float(p.target_r) if p.target_r is not None else d * (p.target - p.entry) / risk
        realized = 0.0
        remaining = 1.0
        tp1_done = False
        cur_stop = p.stop
        for i in range(fill_i + 1, len(rows)):
            bar = rows.iloc[i]
            hit_stop = (bar["low"] <= cur_stop) if d > 0 else (bar["high"] >= cur_stop)
            if hit_stop:
                stop_r = d * (cur_stop - p.entry) / risk   # -1R pre-TP1, ~0 at BE
                total = realized + remaining * stop_r
                return ("hit" if total > 0 else "miss", float(total))
            if not tp1_done:
                hit_tp1 = (bar["high"] >= p.tp1) if d > 0 else (bar["low"] <= p.tp1)
                if hit_tp1:
                    realized += p.tp1_frac * tp1_r
                    remaining -= p.tp1_frac
                    tp1_done = True
                    if p.be_after_tp1:
                        cur_stop = p.entry
                    if p.tp1_filled_at is None:        # record the partial bank
                        p.tp1_filled_at = str(bar["timestamp"])
                    continue
            else:
                hit_tgt = (bar["high"] >= p.target) if d > 0 else (bar["low"] <= p.target)
                if hit_tgt:
                    total = realized + remaining * target_r
                    return ("hit", float(total))
        if deadline_passed:                            # time-stop: mark remainder to close
            mark = d * (float(rows["close"].iloc[-1]) - p.entry) / risk
            total = realized + remaining * mark
            return ("hit" if total > 0 else "miss", float(total))
        return ("open", None)   # filled, TP1 may be banked, rest still running

    def check_open(self) -> list[Prediction]:
        """Re-evaluate open/pending predictions; persist state transitions."""
        changed = []
        for p in self.predictions:
            if p.status not in ("open", "pending"):
                continue
            tp1_before = p.tp1_filled_at
            status, outcome_r = self._evaluate(p)   # may bank TP1 as a side-effect
            if status == p.status:
                if p.tp1_filled_at != tp1_before:   # TP1 just banked; trade still open
                    changed.append(p)
                continue
            prev, p.status = p.status, status
            now = datetime.now(timezone.utc).isoformat()
            if status in ("hit", "miss"):
                p.outcome_r = outcome_r
                p.resolved_at = now
            elif status == "open" and prev == "pending":
                p.filled_at = now          # limit just filled; trade is live
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
