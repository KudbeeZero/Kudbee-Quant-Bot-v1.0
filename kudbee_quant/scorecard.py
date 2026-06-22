"""Forward-validation toolkit — turn the live paper books into honest keep/cut calls.

Read-only over the journal. The hourly bot logs trades tagged by *book* (the setup
suffix: baseline 'core', §C '_cts', §A '_lo', tradfi venue, human reads). The owner's
standing watch-items are all per-book ("after N forward trades, score the book net of
fees and keep or revert it"). This module operationalizes exactly that, plus the
toxic-hour and regime lenses, all net of the venue fee (the project's honest number).

Five lenses (each its own function):
  1. book_scorecard      — per-book n / expectancy / win% / PF / maxDD + KEEP/REVERT/WAIT
  2. book_hour_breakdown — entry-hour (UTC) expectancy, flags toxic hours
  3. book_regime_breakdown — expectancy by entry volatility regime (ATR% terciles)
  4. format_scorecard    — a compact Telegram digest of the verdicts
  5. write_forward_report — a human-readable markdown report combining the above
"""
from __future__ import annotations

from .journal import TradeJournal, net_outcome_r

# Below this many resolved trades a book is too thin to judge — WAIT, don't act.
WAIT_MIN_N = 30


def book_of(setup: str | None) -> str:
    """Human book label from a setup tag (mirrors notify._book_label, + bias/human)."""
    s = setup or ""
    if "_cts" in s:
        return "trend(_cts)"
    if "_lo" in s:
        return "longs(_lo)"
    if "_tradfi" in s:
        return "tradfi"
    if s.startswith("bias"):
        return "bias"
    if "my_read" in s or s == "":
        return "human"
    return "core"


def _resolved_on_or_after(p, since: str | None) -> bool:
    """True if the trade resolved on/after ``since`` (YYYY-MM-DD or ISO). The whole
    point of a FORWARD scorecard: score only trades after a config change, so a
    long-dead pre-revert era can't poison the verdict. None = all history."""
    if since is None:
        return True
    ts = p.resolved_at or p.created_at
    if not ts:
        return False
    return str(ts) >= since          # ISO-8601 sorts lexicographically by time


def _closed(journal: TradeJournal, mode: str | None, since: str | None = None):
    return [p for p in journal.predictions
            if p.status in ("hit", "miss") and p.outcome_r is not None
            and (mode is None or p.mode == mode)
            and _resolved_on_or_after(p, since)]


def _net(p) -> float | None:
    nr = net_outcome_r(p)
    return None if nr is None else float(nr)


def _stats(rs: list[float]) -> dict | None:
    """Net-of-fee stats for a list of R outcomes (None if empty)."""
    n = len(rs)
    if n == 0:
        return None
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    eq = peak = maxdd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        maxdd = min(maxdd, eq - peak)
    return {
        "n": n,
        "total_r": round(sum(rs), 3),
        "expectancy_r": round(sum(rs) / n, 4),
        "win_rate": round(len(wins) / n, 3),
        "avg_win_r": round(sum(wins) / len(wins), 3) if wins else None,
        "avg_loss_r": round(sum(losses) / len(losses), 3) if losses else None,
        "profit_factor": round(sum(wins) / abs(sum(losses)), 3) if losses else None,
        "max_drawdown_r": round(maxdd, 3),
    }


def _verdict(st: dict | None) -> str:
    """KEEP / REVERT once there's a real sample (n>=WAIT_MIN_N); else WAIT."""
    if st is None or st["n"] < WAIT_MIN_N:
        return "WAIT"
    return "KEEP" if st["expectancy_r"] > 0 else "REVERT"


def book_scorecard(journal: TradeJournal | None = None, *, mode: str | None = None,
                   since: str | None = None) -> dict:
    """Per-book net-of-fee scorecard with a KEEP/REVERT/WAIT verdict each, plus an
    overall line. ``mode`` filters paper/live (None = both)."""
    j = journal or TradeJournal()
    closed = _closed(j, mode, since)
    by_book: dict[str, list[float]] = {}
    allr: list[float] = []
    for p in closed:
        nr = _net(p)
        if nr is None:
            continue
        by_book.setdefault(book_of(p.setup), []).append(nr)
        allr.append(nr)
    books = {}
    for b, rs in sorted(by_book.items()):
        st = _stats(rs)
        st["verdict"] = _verdict(st)
        books[b] = st
    return {"books": books, "overall": _stats(allr) or {}, "wait_min_n": WAIT_MIN_N,
            "mode": mode, "since": since}


def _entry_hour(p) -> int | None:
    from datetime import datetime, timezone
    ts = p.filled_at or p.created_at
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.hour


def book_hour_breakdown(journal: TradeJournal | None = None, *, mode: str | None = None,
                        book: str | None = None, min_n: int = 8,
                        since: str | None = None) -> dict:
    """Entry-hour (UTC) net expectancy over closed trades, flagging TOXIC hours
    (>=min_n trades AND negative net expectancy) — operationalizes the 18h/06h
    toxic-cluster watch. ``book`` restricts to one book label (None = all)."""
    j = journal or TradeJournal()
    per_hour: dict[int, list[float]] = {}
    for p in _closed(j, mode, since):
        if book is not None and book_of(p.setup) != book:
            continue
        nr = _net(p)
        h = _entry_hour(p)
        if nr is None or h is None:
            continue
        per_hour.setdefault(h, []).append(nr)
    hours = {}
    toxic = []
    for h in sorted(per_hour):
        st = _stats(per_hour[h])
        is_toxic = st["n"] >= min_n and st["expectancy_r"] < 0
        hours[h] = {**st, "toxic": is_toxic}
        if is_toxic:
            toxic.append(h)
    return {"hours": hours, "toxic_hours": toxic, "min_n": min_n, "book": book}


def book_regime_breakdown(journal: TradeJournal | None = None, *, mode: str | None = None,
                          book: str | None = None, since: str | None = None) -> dict:
    """Net expectancy by ENTRY volatility regime — ATR% (atr_at_entry / entry) split
    into low/mid/high terciles across the sample. Tells us whether the edge is
    regime-conditional (e.g. only pays in mid-vol). Trades without atr_at_entry are
    bucketed as 'unknown'."""
    j = journal or TradeJournal()
    rows = []          # (atr_pct or None, net_r)
    for p in _closed(j, mode, since):
        if book is not None and book_of(p.setup) != book:
            continue
        nr = _net(p)
        if nr is None:
            continue
        atr_pct = (p.atr_at_entry / p.entry
                   if (p.atr_at_entry and p.entry) else None)
        rows.append((atr_pct, nr))
    known = sorted([a for a, _ in rows if a is not None])
    regimes: dict[str, list[float]] = {"low": [], "mid": [], "high": [], "unknown": []}
    if len(known) >= 6:
        lo_cut = known[len(known) // 3]
        hi_cut = known[2 * len(known) // 3]
        for a, nr in rows:
            if a is None:
                regimes["unknown"].append(nr)
            elif a <= lo_cut:
                regimes["low"].append(nr)
            elif a <= hi_cut:
                regimes["mid"].append(nr)
            else:
                regimes["high"].append(nr)
    else:                                   # too few to tercile -> everything 'unknown'
        regimes["unknown"] = [nr for _, nr in rows]
    out = {k: _stats(v) for k, v in regimes.items() if v}
    return {"regimes": out, "book": book}


_VERDICT_EMOJI = {"KEEP": "✅", "REVERT": "🛑", "WAIT": "⏳"}


def format_scorecard(card: dict) -> str:
    """Compact Telegram digest of the per-book verdicts (from book_scorecard)."""
    books = card.get("books", {})
    lines = ["🧮 Forward scorecard (net of fees)"]
    if not books:
        lines.append("No resolved trades yet.")
        return "\n".join(lines)
    for b, st in sorted(books.items(), key=lambda kv: kv[1]["expectancy_r"], reverse=True):
        em = _VERDICT_EMOJI.get(st["verdict"], "")
        tail = f"  (<{card['wait_min_n']} trades)" if st["verdict"] == "WAIT" else ""
        lines.append(f"{em} {b}: {st['expectancy_r']:+.3f}R/t  •  "
                     f"{st['n']} trades  •  {st['win_rate']:.0%} win  •  "
                     f"{st['total_r']:+.1f}R{tail}")
    ov = card.get("overall") or {}
    if ov:
        lines.append(f"— Overall: {ov['expectancy_r']:+.3f}R/t over {ov['n']} "
                     f"({ov['total_r']:+.1f}R, maxDD {ov['max_drawdown_r']:.1f}R)")
    rev = [b for b, st in books.items() if st["verdict"] == "REVERT"]
    if rev:
        lines.append("🛑 REVERT candidates: " + ", ".join(rev))
    return "\n".join(lines)


def notify_scorecard(journal: TradeJournal | None = None, *, mode: str | None = "paper",
                     since: str | None = None) -> bool:
    """Send the forward scorecard to Telegram. No-op (False) if muted or on error."""
    from .notifications import telegram_enabled, send_telegram
    if not telegram_enabled():
        return False
    try:
        return send_telegram(format_scorecard(book_scorecard(journal, mode=mode, since=since)))
    except Exception:  # noqa: BLE001 — a report failure must never break a run
        return False


def _fmt_row(name: str, st: dict | None) -> str:
    if not st:
        return f"| {name} | 0 | — | — | — | — |"
    return (f"| {name} | {st['n']} | {st['expectancy_r']:+.3f} | {st['win_rate']:.0%} | "
            f"{st['total_r']:+.1f} | {st.get('max_drawdown_r', 0):.1f} |")


def write_forward_report(path, journal: TradeJournal | None = None, *,
                         mode: str | None = "paper", since: str | None = None) -> str:
    """Write a human-readable markdown forward-validation report (book scorecard +
    toxic hours + regime breakdown) to ``path``. Returns the markdown text."""
    from datetime import datetime, timezone
    from pathlib import Path
    j = journal or TradeJournal()
    card = book_scorecard(j, mode=mode, since=since)
    hrs = book_hour_breakdown(j, mode=mode, since=since)
    reg = book_regime_breakdown(j, mode=mode, since=since)

    L = ["# Forward-validation scorecard\n",
         f"> Auto-generated by `kudbee_quant.scorecard`. Mode: **{mode or 'all'}**. "
         f"Net of venue fees. KEEP/REVERT once a book has ≥{card['wait_min_n']} resolved "
         f"trades; WAIT below that. _Generated "
         f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}._\n",
         "## Per-book verdicts\n",
         "| book | n | exp R/t | win% | total R | maxDD R | verdict |",
         "|---|---|---|---|---|---|---|"]
    for b, st in sorted(card["books"].items(),
                        key=lambda kv: kv[1]["expectancy_r"], reverse=True):
        L.append(_fmt_row(b, st)[:-2] + f" {st['verdict']} |")
    L.append(f"\n**Overall:** " + (_fmt_row("all", card["overall"]) if card["overall"]
                                   else "no resolved trades") + "\n")

    L.append("## Toxic entry hours (UTC)\n")
    toxic = hrs["toxic_hours"]
    L.append(f"Flagged (≥{hrs['min_n']} trades, negative net): "
             f"**{', '.join(f'{h:02d}h' for h in toxic) if toxic else 'none'}**\n")
    L.append("| hour | n | exp R/t | toxic |\n|---|---|---|---|")
    for h, st in hrs["hours"].items():
        L.append(f"| {h:02d} | {st['n']} | {st['expectancy_r']:+.3f} | "
                 f"{'🛑' if st['toxic'] else ''} |")

    L.append("\n## By volatility regime (entry ATR% terciles)\n")
    L.append("| regime | n | exp R/t | total R |\n|---|---|---|---|")
    for rname in ("low", "mid", "high", "unknown"):
        st = reg["regimes"].get(rname)
        if st:
            L.append(f"| {rname} | {st['n']} | {st['expectancy_r']:+.3f} | {st['total_r']:+.1f} |")

    text = "\n".join(L) + "\n"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    return text



def today_autopsy(journal: TradeJournal | None = None, *, mode: str | None = "paper",
                  since: str | None = None) -> dict:
    """Today's closed trades (net of fees) for the summary's daily breakdown — total
    R + count, per-book {n, r}, and the single best/worst trade. ``since`` defaults to
    the current trading-day open (NY session, calendar.session_day_start). Doubles as
    the ``realized_today`` payload (keys ``r``/``n``), so 'what moved today' is always
    visible without a separate query."""
    from .context.calendar import session_day_start
    j = journal or TradeJournal()
    cut = since or session_day_start().isoformat()
    by_book: dict[str, dict] = {}
    best = worst = None
    total = 0.0
    n = 0
    for p in _closed(j, mode, cut):
        nr = _net(p)
        if nr is None:
            continue
        n += 1
        total += nr
        d = by_book.setdefault(book_of(p.setup), {"n": 0, "r": 0.0})
        d["n"] += 1
        d["r"] += nr
        if best is None or nr > best[1]:
            best = (p.symbol, round(nr, 2))
        if worst is None or nr < worst[1]:
            worst = (p.symbol, round(nr, 2))
    return {"r": round(total, 2), "n": n,
            "by_book": {b: {"n": v["n"], "r": round(v["r"], 2)} for b, v in by_book.items()},
            "best": best, "worst": worst}
