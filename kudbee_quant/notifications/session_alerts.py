"""Session crossover alerts — surface TR-style session context to Telegram.

Fires a once-per-session-open ping with each crypto major's weekly bias and the
key levels it's sitting near. The data is already computed by ``build_levels``;
this module just decides *when* a session opens and *what's worth saying*.

Sessions (NY local time, DST-correct via ``context.calendar.NY``):
  Asia open    20:00 ET  🌏  (Sunday 20:00 = the crypto week's first liquidity pool)
  London open  02:00 ET  🇬🇧  (institutional killzone)
  NY / Brinks  08:00 ET  🇺🇸  (Brinks box forms 08:00-09:00 ET; highest-volume window)

Firing model: STATELESS. The session that fires is the one whose start-hour equals
the latest bar's NY hour. Wired into the hourly paper-trade run only (NOT the :35
status job), so the hourly cron lands in each session-open hour exactly once per day
-> one ping per session. No state file, no double-ping.
"""
from __future__ import annotations

import pandas as pd

from ..context.calendar import NY
from .notify import _g  # compact price format (never scientific notation on mobile)

# (start_hour_NY, label, emoji, tip)
SESSION_OPENS: list[tuple[int, str, str, str]] = [
    (20, "asia", "🌏",
     "First crypto liquidity pool of the week.\n"
     "Asia often sweeps one side of last week's range before setting direction."),
    (2, "london", "🇬🇧",
     "London killzone open — institutional flow entering.\n"
     "Watch for a sweep of the Asian High or Low, then reversal."),
    (8, "ny", "🇺🇸",
     "NY Brinks box forming (08:00-09:00 ET).\n"
     "Market makers load liquidity at the open; watch for the ~09:50 macro reversal."),
]


def _ny_hour_dow(df: pd.DataFrame) -> tuple[int, int] | None:
    """(NY hour, weekday Mon=0..Sun=6) of the latest bar, or None if unparseable."""
    if df is None or df.empty or "timestamp" not in df:
        return None
    try:
        ts = pd.to_datetime(df["timestamp"].iloc[-1], utc=True).tz_convert(NY)
    except (TypeError, ValueError):
        return None
    return int(ts.hour), int(ts.weekday())


def _level_line(label: str, price, current: float, atr: float) -> str | None:
    """A level line iff ``price`` is within 1.5 ATR of ``current`` (else None)."""
    if price is None or pd.isna(price) or atr <= 0:
        return None
    dist = abs(current - price)
    if dist > 1.5 * atr:
        return None
    pct = (current - price) / price * 100 if price else 0.0
    arrow = "📍" if dist < 0.3 * atr else ("⬆️" if current > price else "⬇️")
    return f"  {arrow} {label}: {_g(price)}  ({pct:+.2f}%)"


def build_session_alert(session: str, emoji: str, tip: str, *, is_week_start: bool,
                        last_rows: dict) -> str:
    """Format the Telegram message. ``last_rows`` = {symbol: latest build_levels row}."""
    header = f"{emoji} {'Week starts — ' if is_week_start else ''}{session.upper()} Open"
    lines = [header, tip, ""]
    for symbol, row in last_rows.items():
        cur = row.get("close")
        if cur is None or pd.isna(cur):
            continue
        atr = row.get("atr")
        atr = 0.0 if atr is None or pd.isna(atr) else float(atr)
        wo = row.get("weekly_open")
        if wo is not None and not pd.isna(wo):
            bias = "📈 ABOVE weekly open" if cur > wo else "📉 BELOW weekly open"
            lines.append(f"• {symbol}  {_g(cur)}  — {bias} ({_g(wo)})")
        else:
            lines.append(f"• {symbol}  {_g(cur)}")
        for lbl, val in (("M0 Monthly open", row.get("monthly_open")),
                         ("Pivot PP", row.get("pivot_pp")),
                         ("ADR High", row.get("adr_high")),
                         ("ADR Low", row.get("adr_low")),
                         ("Asian High", row.get("asian_high")),
                         ("Asian Low", row.get("asian_low"))):
            ln = _level_line(lbl, val, cur, atr)
            if ln:
                lines.append(ln)
        lines.extend(_brinks_open_lines(row, cur))   # today's open + NY Brinks box, marked off
        lines.append("")
    return "\n".join(lines).strip()


def _brinks_open_lines(row, cur: float) -> list[str]:
    """Mark off the two levels the desk tracks all day/week: TODAY'S OPEN (price above
    or below it) and the NY BRINKS BOX (08:00-09:00 NY) with its sweep status. The box
    is only shown once it has formed (build_levels leaves it NaN until 09:00 NY)."""
    out: list[str] = []
    dop = row.get("daily_open")
    if dop is not None and not pd.isna(dop) and cur:
        side = "📈 above" if cur > dop else "📉 below"
        pct = (cur - dop) / dop * 100 if dop else 0.0
        out.append(f"  📌 Day open {_g(dop)} — price {side} ({pct:+.2f}%)")
    bh, bl = row.get("ny_brinks_high"), row.get("ny_brinks_low")
    if bh is not None and bl is not None and not pd.isna(bh) and not pd.isna(bl):
        if cur > bh:
            status = "⬆️ HIGH swept"
        elif cur < bl:
            status = "⬇️ LOW swept"
        else:
            status = "📦 inside box"
        out.append(f"  🥊 NY Brinks {_g(bl)}–{_g(bh)}  {status}")
    return out


def check_and_fire_session_alerts(df_by_symbol: dict, notify_fn, *,
                                  verbose: bool = False) -> list[str]:
    """Fire one alert if the latest bar's NY hour is a session open. Returns the
    list of sessions fired (empty = none / no data)."""
    if not df_by_symbol:
        return []
    anchor = next(iter(df_by_symbol.values()))
    hd = _ny_hour_dow(anchor)
    if hd is None:
        return []
    ny_hour, dow = hd
    last_rows = {s: df.iloc[-1] for s, df in df_by_symbol.items() if not df.empty}
    if not last_rows:
        return []

    fired: list[str] = []
    for start_h, name, emoji, tip in SESSION_OPENS:
        if ny_hour != start_h:
            continue
        is_week_start = (name == "asia" and dow == 6)  # Sunday 20:00 ET
        notify_fn(build_session_alert(name, emoji, tip,
                                      is_week_start=is_week_start, last_rows=last_rows))
        fired.append(name)
        if verbose:
            print(f"[session_alerts] fired: {name}")
    return fired


def _is_session_hour_now() -> bool:
    """True iff the current NY wall-clock hour is a session open — a cheap guard so
    we skip the fetch+build_levels work on the ~21 non-session hours of the day."""
    from datetime import datetime
    return datetime.now(NY).hour in {h for h, *_ in SESSION_OPENS}


def run_session_alerts(symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT"), *,
                       client=None, interval: str = "1h", limit: int = 200,
                       notify_fn=None, verbose: bool = False) -> list[str]:
    """Fetch -> build_levels -> check_and_fire. A bad symbol is skipped, not fatal.
    Short-circuits (no I/O) when the current hour isn't a session open."""
    if not _is_session_hour_now():
        if verbose:
            print("[session_alerts] not a session-open hour — skipping fetch.")
        return []
    from ..ingest.router import RouterClient
    from ..levels.builder import build_levels
    client = client or RouterClient()
    df_by: dict = {}
    for sym in symbols:
        try:
            df_by[sym] = build_levels(client.klines(sym, interval=interval, limit=limit))
        except Exception as e:  # noqa: BLE001 — one bad feed must not kill the alert
            if verbose:
                print(f"[session_alerts] {sym}: {e}")
    if notify_fn is None:
        from . import send_telegram
        notify_fn = send_telegram
    return check_and_fire_session_alerts(df_by, notify_fn=notify_fn, verbose=verbose)
