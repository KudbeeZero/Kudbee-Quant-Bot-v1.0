"""Prediction journal storage + verification (see package docstring)."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ..backtest.resolver import resolve_bracket
from ..config.validated_defaults import VENUE_FEE_PCT
from ..ingest import RouterClient, parse_spec

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
    # provenance: "bot" (engine/paper auto signal) vs "human" (your own read).
    # Lets us score the discretionary track record SEPARATELY from the machine.
    source: str = "bot"
    # execution-record fields (live-trading foundation; all optional + back-compat,
    # so existing journal entries load unchanged). `mode` defaults to "paper" — the
    # only mode that exists today; a live order would stamp "live" + an order id.
    mode: str = "paper"                 # "paper" | "live"
    strategy_version: str | None = None
    position_size_usd: float | None = None
    exchange_order_id: str | None = None   # set only for real (live) fills
    reason_closed: str | None = None       # human-readable exit reason

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        if self.pending_limit and self.status == "open":
            self.status = "pending"   # limit orders start unfilled

    @property
    def deadline(self) -> datetime:
        return datetime.fromisoformat(self.created_at) + timedelta(days=self.deadline_days)


def venue_of(p: Prediction) -> str:
    """Which fee venue a trade executes on, from its symbol SPEC. ``yahoo:``
    specs are the zero-fee TradFi promo venue (§26); everything else (bare /
    ``binance:`` crypto) is the fee-paying crypto book (§25 taker)."""
    source, _ = parse_spec(p.symbol)
    return "tradfi" if source == "yahoo" else "crypto"


def fee_pct_of(p: Prediction) -> float:
    """Round-trip cost (fraction of price) for this trade's venue (§26)."""
    return VENUE_FEE_PCT[venue_of(p)]


def fee_r_of(p: Prediction) -> float:
    """The trade's round-trip fee expressed in R, so it's subtractable from
    ``outcome_r``. Mirrors the backtest cost model (backtest/bracket.py): a
    price-fraction fee becomes R via the stop size, ``fee_pct * entry / risk``,
    plus a half round-trip on the scaled-out fraction if TP1 banked. Non-bracket
    predictions carry no R, so their fee is 0."""
    if p.kind != "bracket" or p.entry is None or p.stop is None:
        return 0.0
    risk = abs(p.entry - p.stop)
    if risk <= 0:
        return 0.0
    extra_exit = p.tp1_frac if p.tp1_filled_at is not None else 0.0
    return fee_pct_of(p) * p.entry / risk * (1 + 0.5 * extra_exit)


def net_outcome_r(p: Prediction) -> float | None:
    """``outcome_r`` net of the venue's round-trip fee (None if unresolved)."""
    if p.outcome_r is None:
        return None
    return float(p.outcome_r) - fee_r_of(p)


class TradeJournal:
    def __init__(self, path: Path | str = DEFAULT_PATH, client: RouterClient | None = None):
        self.path = Path(path)
        # RouterClient so a mixed crypto + TradFi (yahoo:) journal resolves each
        # trade against the RIGHT source. Bare crypto symbols still hit Binance.
        self.client = client or RouterClient()
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
            # No completed bar since creation. An unfilled limit CANNOT have
            # traded yet — returning "open" here used to make check_open stamp
            # a fictitious fill seconds after creation (§29). It stays pending
            # (or cancels if the fill window lapses with no bars at all).
            if p.status == "pending":
                fill_deadline = (datetime.fromisoformat(p.created_at)
                                 + timedelta(days=p.fill_deadline_days))
                return ("cancelled", None) if now >= fill_deadline else ("pending", None)
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
            if p.filled_at is None:              # record the BAR time of the fill
                p.filled_at = str(rows["timestamp"].iloc[fill_i])
        else:
            fill_i = -1   # resolve from the start

        # 2) RESOLVE phase from the bar after fill — via the SHARED resolver
        # (backtest/resolver.py) so a live trade and a backtest never disagree.
        fwd = rows.iloc[fill_i + 1:]
        d = p.direction
        win_r = float(p.target_r) if p.target_r is not None else d * (p.target - p.entry) / risk
        tp1_r = (d * (p.tp1 - p.entry) / risk) if p.tp1 is not None else None
        out = resolve_bracket(
            d, p.entry, p.stop, p.target, risk, win_r,
            fwd["high"].to_numpy(), fwd["low"].to_numpy(), fwd["close"].to_numpy(),
            force_close_at_end=deadline_passed,
            tp1=p.tp1, tp1_r=tp1_r, tp1_frac=p.tp1_frac, be_after_tp1=p.be_after_tp1,
        )
        if p.tp1 is not None and out.tp1_offset is not None and p.tp1_filled_at is None:
            p.tp1_filled_at = str(fwd["timestamp"].iloc[out.tp1_offset])
        if not out.exited:
            return ("open", None)   # filled, not yet resolved (TP1 may be banked)
        r = out.outcome_r
        return ("hit" if r > 0 else "miss", float(r))

    def check_open(self) -> list[Prediction]:
        """Re-evaluate open/pending predictions; persist state transitions."""
        changed = []
        for p in self.predictions:
            if p.status not in ("open", "pending"):
                continue
            tp1_before = p.tp1_filled_at
            fill_before = p.filled_at
            status, outcome_r = self._evaluate(p)   # may bank TP1/fill as side-effects
            if status == p.status:
                if p.tp1_filled_at != tp1_before or p.filled_at != fill_before:
                    changed.append(p)               # banked TP1 / recorded a fill
                continue
            prev, p.status = p.status, status
            now = datetime.now(timezone.utc).isoformat()
            if status in ("hit", "miss"):
                p.outcome_r = outcome_r
                p.resolved_at = now
            elif status == "open" and prev == "pending":
                p.filled_at = p.filled_at or now   # bar time from _evaluate; now is fallback
            changed.append(p)
        if changed:
            self.save()
        return changed

    def scorecard(self) -> pd.DataFrame:
        """Per-setup record over RESOLVED predictions: hit rate + R expectancy,
        GROSS and NET of the per-venue round-trip fee (§26). For TradFi (0-fee)
        setups net == gross; crypto setups lose the §25 taker per trade."""
        resolved = [p for p in self.predictions if p.status in ("hit", "miss")]
        cols = ["setup", "n", "hits", "hit_rate", "expectancy_r", "total_r",
                "net_expectancy_r", "net_total_r"]
        if not resolved:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame([{"setup": p.setup or "(unlabeled)", "hit": p.status == "hit",
                            "r": p.outcome_r, "net_r": net_outcome_r(p)} for p in resolved])
        rows = []
        for setup, g in df.groupby("setup"):
            rs, nrs = g["r"].dropna(), g["net_r"].dropna()
            rows.append({"setup": setup, "n": len(g), "hits": int(g["hit"].sum()),
                         "hit_rate": g["hit"].mean(),
                         "expectancy_r": float(rs.mean()) if len(rs) else float("nan"),
                         "total_r": float(rs.sum()) if len(rs) else float("nan"),
                         "net_expectancy_r": float(nrs.mean()) if len(nrs) else float("nan"),
                         "net_total_r": float(nrs.sum()) if len(nrs) else float("nan")})
        return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)

    def venue_record(self) -> dict:
        """Resolved R-bearing record split by fee VENUE — crypto (pays the §25
        taker) vs tradfi (0-fee promo, §26) — reporting expectancy GROSS and NET
        of fees. This is the honest read on whether the zero-fee TradFi book
        actually keeps net≈gross while the crypto book bleeds the taker."""
        out = {}
        for venue in ("crypto", "tradfi"):
            ps = [p for p in self.predictions
                  if p.status in ("hit", "miss") and p.outcome_r is not None
                  and venue_of(p) == venue]
            n = len(ps)
            gross = [float(p.outcome_r) for p in ps]
            net = [net_outcome_r(p) for p in ps]
            fees = [fee_r_of(p) for p in ps]
            hits = sum(1 for p in ps if p.status == "hit")
            out[venue] = {
                "n": n, "hits": hits,
                "hit_rate": (hits / n) if n else None,
                "fee_pct_roundtrip": VENUE_FEE_PCT[venue],
                "avg_fee_r": (sum(fees) / n) if n else None,
                "expectancy_r": (sum(gross) / n) if n else None,
                "total_r": float(sum(gross)) if n else 0.0,
                "net_expectancy_r": (sum(net) / n) if n else None,
                "net_total_r": float(sum(net)) if n else 0.0,
            }
        return out

    def source_record(self) -> dict:
        """Resolved record split by provenance: your discretionary reads ('human')
        vs the engine ('bot'). The honest way to know whose edge is whose."""
        out = {}
        for src in ("bot", "human"):
            rs = [p.outcome_r for p in self.predictions
                  if p.status in ("hit", "miss") and p.source == src and p.outcome_r is not None]
            hits = sum(1 for p in self.predictions
                       if p.status == "hit" and p.source == src and p.outcome_r is not None)
            n = len(rs)
            out[src] = {"n": n, "hits": hits,
                        "hit_rate": (hits / n) if n else None,
                        "expectancy_r": (float(sum(rs) / n)) if n else None,
                        "total_r": float(sum(rs)) if n else 0.0}
        return out

    def resolved_series(self) -> list[dict]:
        """Resolved bracket outcomes in time order — the forward equity curve input.

        ``id``/``symbol``/``timeframe`` are carried so the trade-flow replay
        picker can list resolved trades (additive; existing consumers ignore them).
        """
        rows = [{"t": p.resolved_at or p.created_at, "r": p.outcome_r,
                 "source": p.source, "setup": p.setup or "(unlabeled)",
                 "id": p.id, "symbol": p.symbol, "timeframe": p.timeframe}
                for p in self.predictions
                if p.status in ("hit", "miss") and p.outcome_r is not None]
        return sorted(rows, key=lambda x: x["t"])
