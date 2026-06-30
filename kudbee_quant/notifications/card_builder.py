"""Signal Intelligence Card — a structured, gate-aware Telegram card for a new signal.

This upgrades the plain "new setup" ping into a card that shows the bracket (entry /
stop / TP1 / TP2) and a per-gate "why now" breakdown, plus a fingerprint win-rate and a
HIGH/MEDIUM/LOW confidence read. It is **pure formatting** — :func:`build_signal_card`
takes a :class:`SignalEvent` and returns a string; it NEVER raises (any internal error
degrades to a safe plain-text line). The one side effect lives in :func:`notify_signal_card`,
which is **default-off** behind ``TELEGRAM_SIGNAL_CARDS_ENABLED`` and falls back to the
caller's existing plain-text alert when off or on any failure.

Confidence (spec):
  * HIGH   — fingerprint win-rate ≥ 70% AND all gates pass
  * MEDIUM — win-rate ≥ 55% OR exactly one non-blocking gate warn
  * LOW    — win-rate < 55% OR any gate sitting on its threshold
"""
from __future__ import annotations

import html
from dataclasses import dataclass

from .notify import _g
from .telegram import send_telegram, telegram_enabled

_RULE = "━" * 21
_GATES_TOTAL = 6


@dataclass
class SignalEvent:
    """Everything the card needs about one signal. Only ``symbol``/``direction``/
    ``entry``/``stop`` are really required; every context field is optional and
    renders as a neutral placeholder when missing (the card never throws on a gap).

    Fields:
      symbol, direction (+1 long / -1 short), entry, stop, target (TP2 price),
      tp1 (price|None), tp1_r, tp2_r — the bracket.
      pvsra_label (str|None), pvsra_bull (bool|None) — PVSRA candle read.
      inside_pdh_pdl (bool|None) — price inside prior day's high/low range.
      session_name (str|None) — "London"/"NY"/"Asia"/…
      dxy_regime (str|None) — "RISK_ON"/"RISK_OFF"/"NEUTRAL".
      corr_ok (bool|None), corr_peer (str|None) — correlation guard result.
      adr_pct (0..1|None), adr_threshold — ADR consumed fraction + its gate.
      fp_winrate (0..1|None), fp_trades (int|None) — fingerprint bucket stats.
      gates_passed (int|None of gates_total), near_threshold (bool) — confidence inputs.
    """
    symbol: str
    direction: float
    entry: float
    stop: float
    target: float
    tp1: float | None = None
    tp1_r: float = 1.0
    tp2_r: float = 3.0
    pvsra_label: str | None = None
    pvsra_bull: bool | None = None
    inside_pdh_pdl: bool | None = None
    session_name: str | None = None
    dxy_regime: str | None = None
    corr_ok: bool | None = None
    corr_peer: str | None = None
    adr_pct: float | None = None
    adr_threshold: float = 0.75
    fp_winrate: float | None = None
    fp_trades: int | None = None
    gates_passed: int | None = None
    gates_total: int = _GATES_TOTAL
    near_threshold: bool = False


def _is_long(ev: SignalEvent) -> bool:
    return ev.direction > 0


def _stop_pct(ev: SignalEvent) -> float:
    if not ev.entry:
        return 0.0
    return abs(ev.stop - ev.entry) / abs(ev.entry) * 100.0


def confidence(ev: SignalEvent) -> str:
    """HIGH / MEDIUM / LOW per the spec (HIGH needs a strong, clean read)."""
    wr = ev.fp_winrate
    allpass = ev.gates_passed is not None and ev.gates_passed >= ev.gates_total
    one_warn = ev.gates_passed is not None and ev.gates_passed == ev.gates_total - 1
    if wr is not None and wr >= 0.70 and allpass and not ev.near_threshold:
        return "HIGH"
    if (wr is not None and wr < 0.55) or ev.near_threshold:
        return "LOW"
    if (wr is not None and wr >= 0.55) or one_warn:
        return "MEDIUM"
    return "LOW"


def _esc(s) -> str:
    return html.escape(str(s), quote=False)


def _session_emoji(name: str | None) -> str:
    n = (name or "").lower()
    if "london" in n:
        return "🌅"
    if "ny" in n or "new york" in n:
        return "🗽"
    if "asia" in n or "tokyo" in n:
        return "🌏"
    return ""


def _dxy_bits(regime: str | None) -> str:
    r = (regime or "").upper()
    if r == "RISK_ON":
        return "RISK_ON 🟢"
    if r == "RISK_OFF":
        return "RISK_OFF 🔴"
    if r == "NEUTRAL":
        return "NEUTRAL ⚪"
    return "unknown"


def _yesno(flag: bool | None, yes: str = "yes ✅", no: str = "no", unknown: str = "n/a") -> str:
    if flag is None:
        return unknown
    return yes if flag else no


def build_signal_card(ev: SignalEvent) -> str:
    """Render the HTML signal card. Never raises — returns a plain-text fallback line
    if anything goes wrong (so a malformed event can't break the send path)."""
    try:
        long = _is_long(ev)
        head_emoji = "🟢" if long else "🔴"
        side = "LONG" if long else "SHORT"
        sym = _esc(ev.symbol)

        pvsra = "n/a"
        if ev.pvsra_label:
            pe = "🟢" if ev.pvsra_bull else ("🔴" if ev.pvsra_bull is False else "")
            pvsra = f"{_esc(ev.pvsra_label)} {pe}".strip()

        sess = "n/a"
        if ev.session_name:
            sess = f"{_esc(ev.session_name)} {_session_emoji(ev.session_name)}".strip()

        if ev.corr_ok is None:
            corr = "n/a"
        elif ev.corr_ok:
            corr = "clear ✅"
        else:
            peer = f" ({_esc(ev.corr_peer)})" if ev.corr_peer else ""
            corr = f"correlated{peer} ⚠️"

        if ev.adr_pct is None:
            adr_line = "ADR consumed: n/a"
        else:
            room = "room left" if ev.adr_pct < ev.adr_threshold else "stretched"
            adr_line = f"ADR consumed: {ev.adr_pct * 100:.0f}% ({room})"

        if ev.fp_winrate is None or ev.fp_trades is None:
            fp_line = "Fingerprint bucket: building (need ≥5 trades)"
        else:
            fp_line = f"Fingerprint bucket: {ev.fp_winrate * 100:.0f}% win rate ({ev.fp_trades} trades)"

        tp1 = f"<code>${_g(ev.tp1)}</code>  (+{ev.tp1_r:.1f}R)" if ev.tp1 is not None else "—"
        lines = [
            f"{head_emoji} <b>{side} SIGNAL — {sym}</b>",
            _RULE,
            f"Entry:      <code>${_g(ev.entry)}</code>",
            f"Stop:       <code>${_g(ev.stop)}</code>  (−{_stop_pct(ev):.1f}%)",
            f"Target 1:   {tp1}",
            f"Target 2:   <code>${_g(ev.target)}</code>  (+{ev.tp2_r:.1f}R)",
            _RULE,
            "<b>Why now:</b>",
            f"-  PVSRA: {pvsra}",
            f"-  Inside PDH/PDL range: {_yesno(ev.inside_pdh_pdl)}",
            f"-  Session: {sess}",
            f"-  DXY regime: {_dxy_bits(ev.dxy_regime)}",
            f"-  Correlation guard: {corr}",
            f"-  {adr_line}",
            _RULE,
            fp_line,
            f"Signal confidence: <b>{confidence(ev)}</b>",
        ]
        return "\n".join(lines)
    except Exception:  # noqa: BLE001 — a formatting bug must never break the send
        try:
            side = "LONG" if ev.direction > 0 else "SHORT"
            return (f"{side} signal — {ev.symbol}: entry {_g(ev.entry)} "
                    f"stop {_g(ev.stop)} target {_g(ev.target)}")
        except Exception:  # noqa: BLE001
            return "New signal (details unavailable)."


def signal_cards_enabled() -> bool:
    """Default-off feature flag for the rich card (env ``TELEGRAM_SIGNAL_CARDS_ENABLED``)."""
    from ..config.secrets import get_secret
    s = get_secret("TELEGRAM_SIGNAL_CARDS_ENABLED", required=False)
    return bool(s) and s.reveal().strip().lower() in {"1", "true", "yes", "on"}


def notify_signal_card(ev: SignalEvent) -> bool:
    """Send the HTML card IFF the flag is on and Telegram is configured. Returns False
    (so the caller falls back to its existing plain-text alert) when off or unconfigured.
    Never raises."""
    try:
        if not signal_cards_enabled() or not telegram_enabled():
            return False
        return send_telegram(build_signal_card(ev), parse_mode="HTML")
    except Exception:  # noqa: BLE001
        return False
