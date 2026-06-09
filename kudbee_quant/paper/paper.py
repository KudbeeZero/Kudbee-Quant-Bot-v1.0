"""Paper-trading scan (see package docstring)."""
from __future__ import annotations

from ..confluence.stack import confluence_score
from ..ingest import BinanceClient
from ..journal import Prediction, TradeJournal
from ..levels import build_levels

# Bar duration in minutes for each supported interval — lets the trade horizon
# scale with the timeframe (a 5m scalp resolves in hours; a 4h swing in days).
_INTERVAL_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                 "1h": 60, "2h": 120, "3h": 180, "4h": 240, "6h": 360,
                 "8h": 480, "12h": 720, "1d": 1440}
# Horizon in BARS (calibrated to the validated 1h: 72 bars = 3 days deadline,
# 12 bars = 0.5 day fill window). Applied uniformly so every timeframe gets a
# proportional, bar-count-equivalent window.
_DEADLINE_BARS = 72
_FILL_BARS = 12


def _bars_to_days(interval: str, bars: int) -> float:
    return bars * _INTERVAL_MIN.get(interval, 60) / 1440.0


def paper_scan(
    symbols: list[str],
    min_pct: float = 0.5,
    target_r: float = 3.0,   # 3R validated to beat 2R with the limit-retrace entry
    stop_atr: float = 1.5,  # validated: wider stop avoids noise stop-outs (keep ~3:1)
    retrace_atr: float = 0.25,  # limit entry pullback (validated execution)
    interval: str = "1h",
    intervals: list[str] | None = None,  # multi-timeframe scan (1h core; 5m/15m/2h/4h also)
    deadline_days: float | None = None,   # None = scale with the timeframe (recommended)
    fill_deadline_days: float | None = None,
    journal: TradeJournal | None = None,
    client: BinanceClient | None = None,
    biases=None,
    require_bias: bool = False,
    tp1_r: float | None = None,    # optional TARGET ONE (partial bank); None = full target only
    tp1_frac: float = 0.5,
) -> list[Prediction]:
    """Log a bracket paper trade for each symbol currently signalling.

    Threshold is a confluence PERCENTAGE (``min_pct``). DIRECTION is gated by
    the human bias layer: if a bias is set for a symbol, only signals that AGREE
    with it are taken (scalp WITH the read, never against). If ``require_bias``
    is True, symbols without an active bias are skipped entirely (pure
    human-directed mode). One open trade per symbol at a time.
    """
    j = journal or TradeJournal()
    client = client or BinanceClient()
    if biases is None:
        from ..bias import BiasBook
        biases = BiasBook()
    # One open trade per (symbol, timeframe) -> multi-TF widens the chances.
    open_keys = {(p.symbol, p.timeframe) for p in j.predictions
                 if p.status in ("open", "pending") and p.kind == "bracket"}
    tf_list = intervals or [interval]

    logged = []
    for interval in tf_list:
      # Trade horizon scales with the timeframe unless explicitly overridden.
      tf_deadline = deadline_days if deadline_days is not None else _bars_to_days(interval, _DEADLINE_BARS)
      tf_fill = fill_deadline_days if fill_deadline_days is not None else _bars_to_days(interval, _FILL_BARS)
      for sym in symbols:
        sym = sym.upper()
        if (sym, interval) in open_keys:
            continue  # already in a paper trade on this symbol+timeframe
        f = build_levels(client.klines(sym, interval=interval, limit=600))
        last = confluence_score(f).iloc[-1]
        pct, direction = float(last["confluence_pct"]), float(last["direction"])
        strength = float(last["strength"])
        if pct < min_pct or direction == 0:
            continue
        # Direction gate: scalp only WITH the human read (bias), never against.
        bias = biases.get(sym)
        if bias is not None:
            if direction != bias.direction:
                continue            # signal opposes the read -> skip
        elif require_bias:
            continue                # human-directed mode: no read -> no trade
        signal_price = float(last["close"])
        atr = float(last["atr"])
        sd = atr * stop_atr
        if sd <= 0:
            continue
        # Validated execution: LIMIT entry at a retrace pullback (maker), stop/
        # target measured from the limit. The order is PENDING until filled.
        limit = signal_price - direction * retrace_atr * atr
        stop = limit - direction * sd
        target = limit + direction * sd * target_r
        tp1 = (limit + direction * sd * tp1_r) if tp1_r is not None else None
        side = "long" if direction > 0 else "short"
        p = j.add(Prediction(
            symbol=sym, kind="bracket", level=limit, entry=limit, stop=stop,
            target=target, direction=direction, target_r=target_r,
            tp1=tp1, tp1_frac=tp1_frac,
            deadline_days=tf_deadline, timeframe=interval,
            pending_limit=True, signal_price=signal_price, fill_deadline_days=tf_fill,
            setup=("bias_scalp" if bias is not None else "confluence_r") + f"_{int(round(pct*100))}pct",
            note=(f"{'BIAS-aligned' if bias is not None else 'Auto'} confluence-R {side} scalp: "
                  f"{pct:.0%} confluence (strength {int(strength)})." +
                  (f" Read: {bias.note}" if bias is not None and bias.note else "") +
                  f" LIMIT {limit:.4g} (retrace {retrace_atr} ATR from {signal_price:.4g}), "
                  f"stop {stop:.4g}, target {target:.4g} ({target_r}R, maker)." +
                  (f" TP1 {tp1:.4g} ({tp1_r}R, bank {tp1_frac:.0%})." if tp1 is not None else "")),
        ))
        logged.append(p)
    return logged
