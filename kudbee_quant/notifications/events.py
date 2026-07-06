"""Read-only event + delta layer for the Telegram channel.

The channel used to post only **state snapshots** — every hourly Live Read just
showed the current open-book numbers. An outside observer watching the numbers
bounce (8▸1 → 6▸3 → 8▸1 → 9▸0) had no idea *what happened* between reads: a
position drifting toward its stop, a warning clearing, a red trade recovering to
green — none of it fired a message. This module turns those snapshots into
**events** by diffing the previous read against the current one, and adds a
one-line "since last read" delta header to the Live Read.

Design rules (so this can never touch the trading edge):

  * **Strictly read-only / off the trading path.** Everything here consumes the
    dict returned by :func:`review.open_trades_report` and the small JSON
    snapshot we persist; nothing imports or mutates ``bracket``/``resolver``/
    ``paper_scan`` or the journal. Events are *detected* from marks, never
    *emitted by* the execution path.
  * **Pure core.** :func:`snapshot`, :func:`diff_events`, :func:`delta_summary`
    and :func:`format_event` are pure functions over plain dicts — fully unit
    testable with no I/O. The only side effects (load/save state, send Telegram)
    live in :func:`notify.notify_summary`, behind the usual ``telegram_enabled``
    guard.
  * **Fires once per transition.** Each event is the *edge* of a state change
    (healthy→near-stop, red→green), computed against the prior snapshot, so it
    pings once and the new snapshot becomes the next baseline — no re-spamming
    while a trade simply *stays* near its stop.

State persists in ``data/notify_state.json`` — the same committed-artifact
pattern as ``data/heartbeat.json`` (the hourly Action commits it alongside the
journal). Opens/closes are already pinged by ``notify_trade_{open,close}_events``
(PR #84); this layer deliberately covers only the **intra-trade** transitions
those miss.
"""
from __future__ import annotations

import json
import os

# Default location of the persisted last-read snapshot (committed, like heartbeat).
_DEFAULT_STATE_PATH = os.path.join("data", "notify_state.json")

# Health labels from review._health that mean "this trade is in trouble".
_TROUBLE = {"near stop", "warning"}

# A trade this close to its deadline (hours) crosses into the "resolving soon"
# window — matches notify._deadline_line's default so the two agree.
_DEADLINE_SOON_HOURS = 6.0

# Per-event presentation. Keys are the event ``type`` strings emitted below.
_ICONS = {
    "filled": "📥",
    "approaching_stop": "⚠️",
    "warning_cleared": "✔️",
    "recovered": "📈",
    "flipped_red": "🔻",
    "tp1_touched": "📍",
    "tp1_banked": "💰",
    "deadline_soon": "⏳",
}
_LABELS = {
    "filled": "Entry Filled",
    "approaching_stop": "Stop Approaching",
    "warning_cleared": "Warning Cleared",
    "recovered": "Recovered to Profit",
    "flipped_red": "Slipped to Loss",
    "tp1_touched": "First Target Reached",
    "tp1_banked": "TP1 Banked",
    "deadline_soon": "Deadline Approaching",
}


def _r_str(r: float | None) -> str:
    """Format an R value with an explicit sign, or '—' when unmarked."""
    if r is None:
        return "—"
    return f"+{r:.2f}R" if r >= 0 else f"{r:.2f}R"


def snapshot(report: dict) -> dict:
    """Reduce an :func:`open_trades_report` to the minimal per-trade state we diff.

    Returns ``{"trades": {id: {...}}, "agg": {...}}``. Only fields that drive an
    event or the delta header are kept, so the persisted file stays tiny and the
    diff is trivial.
    """
    trades: dict[str, dict] = {}
    for t in report.get("trades", []) or []:
        tid = t.get("id")
        if tid is None:
            continue
        h = t.get("hours_to_deadline")
        trades[str(tid)] = {
            "symbol": t.get("symbol"),
            "ur": t.get("unrealized_r"),
            "health": t.get("health"),
            "tp1_touched": bool(t.get("tp1_touched")),
            "tp1_filled": bool(t.get("tp1_filled")),
            "stop_touched": bool(t.get("stop_touched")),
            # Boolean edge (not the raw float) so the diff is a clean False→True
            # the hour a trade enters the "resolving soon" window, not noise from
            # the countdown ticking down every read.
            "dl_soon": (h is not None and 0 < h <= _DEADLINE_SOON_HOURS),
            "status": t.get("status"),
        }
    p = report.get("portfolio", {}) or {}
    agg = {
        "n": p.get("total_open", 0),
        "winners": p.get("winners_open", 0),
        "losers": p.get("losers_open", 0),
        "unrealized_r": p.get("total_unrealized_r", 0.0),
    }
    return {"trades": trades, "agg": agg}


def diff_events(prev: dict | None, curr: dict) -> list[dict]:
    """Intra-trade transitions between two snapshots, as a list of event dicts.

    Only trades present in BOTH snapshots are considered (entries/exits are
    handled by ``notify_trade_{open,close}_events``). Each event is
    ``{"type", "symbol", "r", "detail"}``; render with :func:`format_event`.
    """
    if not prev:
        return []
    out: list[dict] = []
    prev_trades = prev.get("trades", {})
    for tid, c in curr.get("trades", {}).items():
        p = prev_trades.get(tid)
        if not p:
            continue  # newly opened — the open-event ping covers it
        sym = c.get("symbol") or "?"
        c_ur, p_ur = c.get("ur"), p.get("ur")
        c_health, p_health = c.get("health"), p.get("health")

        # Entry filled (pending→open edge): the open-event ping fires when the
        # BRACKET is created, but a resting limit filling later had no ping at
        # all — the moment the trade actually goes live (§86 owner ask).
        if p.get("status") == "pending" and c.get("status") == "open":
            out.append({"type": "filled", "symbol": sym, "r": c_ur,
                        "detail": "Limit order filled — bracket is live."})

        # TP1 banked (one-way latch: only fires on the False→True edge).
        if c.get("tp1_filled") and not p.get("tp1_filled"):
            out.append({"type": "tp1_banked", "symbol": sym, "r": c_ur,
                        "detail": "Partial booked, stop to breakeven."})
        # TP1 *touched* but not yet banked — price reached the first target.
        # Suppressed once it actually banks (the tp1_banked ping covers that).
        elif (c.get("tp1_touched") and not p.get("tp1_touched")
              and not c.get("tp1_filled")):
            out.append({"type": "tp1_touched", "symbol": sym, "r": c_ur,
                        "detail": "Reached first target."})

        # Entered the "resolving soon" deadline window (False→True edge only).
        if c.get("dl_soon") and not p.get("dl_soon"):
            out.append({"type": "deadline_soon", "symbol": sym, "r": c_ur,
                        "detail": "Will auto-resolve at its deadline soon."})

        # Health crossing into / out of trouble.
        if c_health in _TROUBLE and p_health not in _TROUBLE:
            detail = ("Tagged stop." if c.get("stop_touched")
                      else "Drifting toward stop. Watching.")
            out.append({"type": "approaching_stop", "symbol": sym, "r": c_ur,
                        "detail": detail})
        elif p_health in _TROUBLE and c_health not in _TROUBLE:
            out.append({"type": "warning_cleared", "symbol": sym, "r": c_ur,
                        "detail": "Back to healthy."})

        # Profit/loss sign flips — only when BOTH reads carry a live mark.
        if c_ur is not None and p_ur is not None:
            if p_ur < 0 <= c_ur:
                out.append({"type": "recovered", "symbol": sym, "r": c_ur,
                            "detail": "Back in profit since last read."})
            elif p_ur >= 0 > c_ur:
                out.append({"type": "flipped_red", "symbol": sym, "r": c_ur,
                            "detail": "Was green last read; now underwater."})
    return out


def format_event(ev: dict) -> str:
    """Render one event dict as a Telegram message block."""
    etype = ev.get("type", "")
    icon = _ICONS.get(etype, "•")
    label = _LABELS.get(etype, etype.replace("_", " ").title())
    lines = [f"{icon} {ev.get('symbol', '?')} — {label}", _r_str(ev.get("r"))]
    detail = ev.get("detail")
    if detail:
        lines.append(detail)
    return "\n".join(lines)


def delta_summary(prev: dict | None, curr: dict) -> str:
    """One-line "since last read" header, or '' when there's nothing to say.

    Reconciles the human-visible aggregates (recovered/flipped counts + the
    unrealized-R move). Returns '' on the first read (no prior) or a quiet hour
    so the Live Read isn't cluttered with "no changes".
    """
    if not prev:
        return ""
    pa, ca = prev.get("agg", {}), curr.get("agg", {})
    changes: list[str] = []

    up = (ca.get("winners", 0) or 0) - (pa.get("winners", 0) or 0)
    if up > 0:
        changes.append(f"{up} recovered")
    elif up < 0:
        changes.append(f"{-up} flipped red")

    # Count warning edges across the per-trade snapshots (both directions).
    warned = cleared = 0
    pt = prev.get("trades", {})
    for tid, c in curr.get("trades", {}).items():
        p = pt.get(tid)
        if not p:
            continue
        c_bad, p_bad = c.get("health") in _TROUBLE, p.get("health") in _TROUBLE
        warned += int(c_bad and not p_bad)
        cleared += int(p_bad and not c_bad)
    if warned:
        changes.append(f"{warned} warning{'s' if warned != 1 else ''}")
    if cleared:
        changes.append(f"{cleared} warning{'s' if cleared != 1 else ''} cleared")

    r_delta = (ca.get("unrealized_r", 0.0) or 0.0) - (pa.get("unrealized_r", 0.0) or 0.0)
    if abs(r_delta) >= 0.1:
        changes.append(f"unrealized {r_delta:+.2f}R")

    if not changes:
        return ""
    return "📊 Since last read: " + ", ".join(changes)


# --- state persistence (the only I/O; callers guard on telegram_enabled) -----

def load_state(path: str = _DEFAULT_STATE_PATH) -> dict | None:
    """Load the last persisted snapshot, or ``None`` if absent/unreadable."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) and "trades" in data else None
    except (OSError, ValueError):
        return None


def save_state(snap: dict, path: str = _DEFAULT_STATE_PATH) -> bool:
    """Persist a snapshot. Never raises — returns True on success."""
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, sort_keys=True)
        return True
    except (OSError, ValueError, TypeError):
        return False
