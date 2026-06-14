"""Vector-candle STUDY — does a climax candle actually precede a move?

The logger (`vector_log.py`) records WHERE/WHEN climax candles form. This measures
WHAT HAPPENS NEXT, honestly, so a vector candle is validated as a feature rather
than assumed to be a signal (the standing pvsra.py caveat).

For each climax candle we simulate the system's own trade — enter at the bar close
in the climax's direction (bull_climax long / bear_climax short), a `stop_atr` ATR
stop and a `target_r` bracket — and resolve it over the next `max_bars` bars with
the SHARED resolver (`backtest/resolver.resolve_bracket`), so a vector-candle
outcome and a backtest never disagree. Results are bucketed by the chart location
the candle formed at, by confluence agreement, and by climax type, with the honest
fee subtracted in R.

This is research, not a green light: §37 says trading 1m/5m is fee-poisoned, so a
positive bucket here is a hypothesis to forward-test, never a license to scalp 1m.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from ..backtest.resolver import resolve_bracket
from ..config.validated_defaults import TAKER_FEE_PCT
from ..ingest import RouterClient
from ..levels import build_levels
from .vector_log import detect_vector_events


def vector_outcomes(df: pd.DataFrame, symbol: str, timeframe: str, *,
                    max_bars: int = 24, stop_atr: float = 1.0,
                    target_r: float = 3.0) -> list[dict]:
    """One simulated bracket per climax candle; returns event context + outcome_r
    (gross) and the fee in R for that trade."""
    base = build_levels(df) if "atr" not in df.columns else df
    events = detect_vector_events(base, symbol, timeframe, last_only=False)
    rows = base.reset_index(drop=True)
    by_ts = {str(t): i for i, t in enumerate(rows["timestamp"])}

    high = rows["high"].to_numpy(float)
    low = rows["low"].to_numpy(float)
    close = rows["close"].to_numpy(float)
    atr = rows["atr"].to_numpy(float)

    out = []
    for ev in events:
        i = by_ts.get(ev.timestamp)
        if i is None or i + 1 >= len(rows):
            continue
        a = float(atr[i])
        if a <= 0:
            continue
        d = 1.0 if ev.vector == "bull_climax" else -1.0
        entry = float(close[i])
        risk = stop_atr * a
        stop = entry - d * risk
        target = entry + d * risk * target_r
        j = min(i + 1 + max_bars, len(rows))
        res = resolve_bracket(d, entry, stop, target, risk, target_r,
                              high[i + 1:j], low[i + 1:j], close[i + 1:j],
                              force_close_at_end=True)
        if res.outcome_r is None:
            continue
        # Round-trip taker fee expressed in R (mirrors journal.fee_r_of for a
        # crypto trade): fee_pct * entry / risk.
        fee_r = TAKER_FEE_PCT * entry / risk
        out.append({
            "symbol": symbol, "timeframe": timeframe, "timestamp": ev.timestamp,
            "vector": ev.vector, "level": ev.level, "agree": ev.agree,
            "confluence_pct": ev.confluence_pct, "vol_ratio": ev.vol_ratio,
            "outcome_r": float(res.outcome_r), "fee_r": float(fee_r),
            "net_r": float(res.outcome_r) - float(fee_r),
        })
    return out


def summarize(rows: list[dict], by: tuple[str, ...]) -> pd.DataFrame:
    """Group outcomes by ``by`` keys; report n, win rate, gross + net expectancy."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[tuple(r[k] for k in by)].append(r)
    recs = []
    for key, rs in buckets.items():
        n = len(rs)
        wins = sum(1 for r in rs if r["net_r"] > 0)
        rec = dict(zip(by, key, strict=True))
        rec.update({
            "n": n,
            "win_rate": wins / n,
            "exp_gross_r": sum(r["outcome_r"] for r in rs) / n,
            "exp_net_r": sum(r["net_r"] for r in rs) / n,
            "total_net_r": sum(r["net_r"] for r in rs),
        })
        recs.append(rec)
    cols = [*by, "n", "win_rate", "exp_gross_r", "exp_net_r", "total_net_r"]
    df = pd.DataFrame(recs, columns=cols)
    return df.sort_values("n", ascending=False).reset_index(drop=True)


def study_symbols(symbols: list[str], intervals: list[str],
                  client: RouterClient | None = None, *, limit: int = 1000,
                  max_bars: int = 24, stop_atr: float = 1.0,
                  target_r: float = 3.0) -> list[dict]:
    """Collect vector-candle outcomes across a universe x timeframes."""
    client = client or RouterClient()
    allrows: list[dict] = []
    for interval in intervals:
        for sym in symbols:
            try:
                df = client.klines(sym, interval=interval, limit=limit)
                allrows += vector_outcomes(df, sym, interval, max_bars=max_bars,
                                           stop_atr=stop_atr, target_r=target_r)
            except Exception:
                continue
    return allrows
