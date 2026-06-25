"""Paper-trading scan (see package docstring)."""
from __future__ import annotations

import logging

from ..confluence.stack import KILLZONE_GATE_FLAGS, confluence_score
from ..ingest import RouterClient
from ..ingest.router import parse_spec
from ..intelligence.event_calendar import (
    get_blocking_event,
    hours_until_event,
    is_friday_close_window,
    is_monday_open_window,
)
from ..journal import Prediction, TradeJournal
from ..levels import build_levels

logger = logging.getLogger(__name__)

# Bar duration in minutes for each supported interval — lets the trade horizon
# scale with the timeframe (a 5m scalp resolves in hours; a 4h swing in days).
_INTERVAL_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                 "1h": 60, "2h": 120, "3h": 180, "4h": 240, "6h": 360,
                 "8h": 480, "12h": 720, "1d": 1440}
# Horizon in BARS (calibrated to the validated 1h: 24 bars = 1 day deadline,
# 12 bars = 0.5 day fill window). Applied uniformly so every timeframe gets a
# proportional, bar-count-equivalent window. (Deadline shortened 72->24 bars on
# 2026-06-24: align the live 1h resolve window with the validated max_bars=24.)
_DEADLINE_BARS = 24
_FILL_BARS = 12


def _bars_to_days(interval: str, bars: int) -> float:
    return bars * _INTERVAL_MIN.get(interval, 60) / 1440.0


def _book_of(setup: str) -> str:
    """Experiment 'book' identity = the flag/venue suffix after the '...pct' token
    (e.g. 'confluence_r_50pct_tf_cts' -> '_tf_cts'; baseline -> ''). Lets a
    separately-tagged experiment (§C '_cts', §A '_lo') hold its OWN open trade per
    symbol+timeframe alongside the baseline book, instead of colliding on
    (symbol, timeframe). The net-exposure guard still caps COMBINED per-coin risk."""
    i = setup.find("pct")
    return setup[i + 3:] if i != -1 else setup


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
    client: RouterClient | None = None,
    biases=None,
    require_bias: bool = False,
    tp1_r: float | None = None,    # optional TARGET ONE (partial bank); None = full target only
    tp1_frac: float = 0.5,         # fraction banked at TP1 (0.0 = breakeven-only: bank nothing, ride full size)
    be_after_tp1: bool = True,     # move stop to breakeven once TP1 is reached
    risk_per_trade: float = 0.01,      # each defined-risk trade ~= 1% of the account
    max_symbol_risk: float = 0.02,     # cap COMBINED long+short risk per coin (two-sided guard)
    trend_filter: bool = False,        # tested: skip signals fighting the 800-EMA HTF trend
    long_only: bool = False,           # skip SHORT signals (5m excursion_audit: longs 32% vs shorts 14%, n=48)
    killzone_gate: bool = False,       # skip signals outside London/NY/Brinks windows (NOT validated for 5m)
    trailing_atr: float | None = None, # chandelier trail at trailing_atr*ATR behind the extreme (None = off)
    clean_trend_stack: bool = False,   # §C: only trade when 13/50/800-EMA cleanly stacked 10 bars + gap widening
    dry_run: bool = False,             # compute brackets WITHOUT persisting (read-only preview)
) -> list[Prediction]:
    """Log a bracket paper trade for each symbol currently signalling.

    Threshold is a confluence PERCENTAGE (``min_pct``). DIRECTION is gated by
    the human bias layer: if a bias is set for a symbol, only signals that AGREE
    with it are taken (scalp WITH the read, never against). If ``require_bias``
    is True, symbols without an active bias are skipped entirely (pure
    human-directed mode). One open trade per symbol+timeframe.

    NET-EXPOSURE GUARD: a new trade is skipped if it would push a coin's COMBINED
    (long+short, all timeframes) gross risk over ``max_symbol_risk`` — so running
    both sides at once (1h long + 5m short) can't silently over-expose one coin.

    DRY RUN: when ``dry_run`` is True the same signals + brackets are computed but
    NOTHING is written to the journal (no ``j.add``). This is the read-only seam
    the dashboard's curated runner uses, so a web preview can never poison the
    bot-owned ``data/journal.json`` (the data-poisoning vector api_security.py
    was written to close).
    """
    # --- Binary-event gate (read-only, checked BEFORE any signal evaluation) ---
    # Tino's rule: do not open NEW positions near a known high-impact scheduled
    # event (earnings, PCE, NFP, FOMC) — binary moves invalidate technical setups.
    # This blocks NEW entries only; existing open/pending trades are untouched.
    # The gate mirrors live behaviour in dry_run so the read-only dashboard preview
    # stays faithful, but the Telegram ping is suppressed on dry_run (a preview
    # must have no side effects — same invariant as never writing to the journal).
    block_event, block_hours, block_reason = None, 0.0, None
    blocking = get_blocking_event(hours_before=4.0)
    if blocking:
        block_event = blocking["name"]
        block_hours = hours_until_event(blocking)
        block_reason = f"{block_event} in {block_hours:.1f}h"
    elif is_friday_close_window():
        block_event, block_reason = "Friday close", "Friday close window"
    elif is_monday_open_window():
        block_event, block_reason = "Monday open gap risk", "Monday open gap risk"
    if block_reason:
        logger.info("SCAN BLOCKED: %s — no new entries", block_reason)
        if not dry_run:
            from ..notifications import notify_scan_blocked
            notify_scan_blocked(block_event, block_hours)
        return []

    from ..exposure import symbol_exposure
    j = journal or TradeJournal()
    client = client or RouterClient()
    if biases is None:
        from ..bias import BiasBook
        biases = BiasBook()
    # One open trade per (symbol, timeframe, BOOK) — the book = the experiment's
    # flag/venue suffix (§C '_cts', §A '_lo', baseline '') — so separately-tagged
    # paper experiments coexist with the validated book on the same symbol+timeframe.
    open_keys = {(p.symbol, p.timeframe, _book_of(p.setup or "")) for p in j.predictions
                 if p.status in ("open", "pending") and p.kind == "bracket"}
    tf_list = intervals or [interval]

    logged = []
    for interval in tf_list:
      # Trade horizon scales with the timeframe unless explicitly overridden.
      tf_deadline = deadline_days if deadline_days is not None else _bars_to_days(interval, _DEADLINE_BARS)
      tf_fill = fill_deadline_days if fill_deadline_days is not None else _bars_to_days(interval, _FILL_BARS)
      for sym in symbols:
        sym = sym.upper()
        # Venue: bare/binance: crypto vs yahoo: TradFi (gold/S&P/oil/FX). TradFi
        # rides the exchange's 0-fee promo (MEMORY §26) and is tagged so its
        # forward record scores SEPARATELY from the fee-paying crypto book.
        source, _ = parse_spec(sym)
        is_tradfi = source != "binance"
        venue_tag = "_tradfi" if is_tradfi else ""
        # This scan's book = its flag/venue suffix (must match the setup built below).
        book = (("_tf" if trend_filter else "") + ("_lo" if long_only else "")
                + ("_kz" if killzone_gate else "") + ("_cts" if clean_trend_stack else "")
                + venue_tag)
        if (sym, interval, book) in open_keys:
            continue  # already in a paper trade on this symbol+timeframe+book
        f = build_levels(client.klines(sym, interval=interval, limit=600))
        last = confluence_score(f).iloc[-1]
        pct, direction = float(last["confluence_pct"]), float(last["direction"])
        strength = float(last["strength"])
        if pct < min_pct or direction == 0:
            continue
        # HTF TREND FILTER (tested, robust): don't fight the 800-EMA trend.
        if trend_filter and "ema_800" in last and last["ema_800"] == last["ema_800"]:
            if direction != (1.0 if last["close"] > last["ema_800"] else -1.0):
                continue
        # LONG-ONLY (experiment §A): skip shorts. 5m excursion_audit (n=48): longs
        # 32% (11/34) win vs shorts 14% (2/14). Tagged "_lo" for separate scoring.
        if long_only and direction < 0:
            continue
        # KILLZONE GATE (experimental, default OFF — NOT validated for 5m): keep
        # only signals inside the active London/NY/Brinks windows. No-op when the
        # frame lacks those flag columns (so it never silently blocks every trade).
        if killzone_gate:
            present = [c for c in KILLZONE_GATE_FLAGS if c in last.index]
            if present and not any(bool(last[c]) for c in present):
                continue
        # CLEAN TREND STACK gate (§C experiment, default OFF; UNVERIFIED): only trade
        # when 13/50/800-EMA are cleanly stacked one direction for 10 bars AND the
        # 13/50 gap is WIDENING (a separating trend, not a braided one). Runs on the
        # feature frame `f` and checks the latest bar; no-op if columns are missing.
        if clean_trend_stack and {"ema_13", "ema_50", "ema_800", "atr"} <= set(f.columns):
            up = (f["ema_13"] > f["ema_50"]) & (f["ema_50"] > f["ema_800"])
            dn = (f["ema_13"] < f["ema_50"]) & (f["ema_50"] < f["ema_800"])
            stacked = (up.rolling(10, min_periods=10).min().fillna(0).astype(bool)
                       | dn.rolling(10, min_periods=10).min().fillna(0).astype(bool))
            gap = (f["ema_13"] - f["ema_50"]).abs() / f["atr"]
            widening = gap > gap.shift(10)
            if not bool((stacked & widening).iloc[-1]):
                continue   # not a clean, separating trend -> skip this signal
        # Direction gate: scalp only WITH the human read (bias), never against.
        bias = biases.get(sym)
        if bias is not None:
            if direction != bias.direction:
                continue            # signal opposes the read -> skip
        elif require_bias:
            continue                # human-directed mode: no read -> no trade
        # NET-EXPOSURE GUARD: would this new trade push the coin's COMBINED
        # (long+short, all timeframes) gross risk over the ceiling? If so, skip.
        ex = symbol_exposure(j.predictions, sym, risk_per_trade)
        if ex.gross_risk + risk_per_trade > max_symbol_risk + 1e-9:
            continue
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
        pred = Prediction(
            symbol=sym, kind="bracket", level=limit, entry=limit, stop=stop,
            target=target, direction=direction, target_r=target_r,
            tp1=tp1, tp1_frac=tp1_frac, be_after_tp1=be_after_tp1,
            trailing_atr=trailing_atr,
            atr_at_entry=(atr if trailing_atr is not None else None),
            deadline_days=tf_deadline, timeframe=interval,
            pending_limit=True, signal_price=signal_price, fill_deadline_days=tf_fill,
            setup=("bias_scalp" if bias is not None else "confluence_r") + f"_{int(round(pct*100))}pct"
                  + ("_tf" if trend_filter else "")
                  + ("_lo" if long_only else "")
                  + ("_kz" if killzone_gate else "")
                  + ("_cts" if clean_trend_stack else "") + venue_tag,
            note=(f"{'BIAS-aligned' if bias is not None else 'Auto'} confluence-R {side} scalp: "
                  f"{pct:.0%} confluence (strength {int(strength)})." +
                  (" [TradFi 0-fee venue]" if is_tradfi else "") +
                  (f" Read: {bias.note}" if bias is not None and bias.note else "") +
                  f" LIMIT {limit:.4g} (retrace {retrace_atr} ATR from {signal_price:.4g}), "
                  f"stop {stop:.4g}, target {target:.4g} ({target_r}R, maker)." +
                  (f" TP1 {tp1:.4g} ({tp1_r}R, bank {tp1_frac:.0%})." if tp1 is not None else "")),
        )
        # DRY RUN never touches the journal — preview-only (see docstring).
        p = pred if dry_run else j.add(pred)
        logged.append(p)
    return logged
