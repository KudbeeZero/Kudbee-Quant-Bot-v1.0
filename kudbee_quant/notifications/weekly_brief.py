"""Weekly macro brief — a READ-ONLY Telegram digest of the (inert) macro layer.

This is deliberately NOT a signal. It surfaces the planted macro context
(`intelligence.macro_context`) as a human-readable weekly note, with loud
caveats that nothing here is verified, significance-tested, or wired to the bot.

Honesty rules baked in (per the project thesis):
  * Every macro/FX number is Tino's UNVERIFIED weekly read — labelled as such.
  * The bot-status block states the TRUE research state: the DXY-regime study
    came back INCONCLUSIVE and the VAH trap-reversal study REJECT — both inert,
    nothing wired. No edge is claimed.
  * No auto-execution, no signal influence. The brief is opt-in: it only sends
    when someone calls it (e.g. the `notify-weekly-brief` CLI), and only if the
    TELEGRAM_* creds are present. It is NOT on any cron/workflow.

``format_weekly_brief`` is pure (no I/O) so it is unit-tested without network.
``notify_weekly_brief`` gates on creds and sends via the shared transport
(which handles token redaction, message splitting and rate-limit headroom).
"""
from __future__ import annotations

from ..intelligence.macro_context import (
    PAIR_BIAS,
    RISK_FILTER_FLAGS,
    TINO_CRYPTO_OBSERVATIONS,
    WEEKLY_MACRO_BIAS,
    get_dxy_regime,
)
from .telegram import send_telegram, telegram_enabled

# True research state as of this module — keep in sync with the studies on main.
# (DXY: research/dxy_regime_crypto.py; VAH: research/vah_trap_reversal.py.)
_STUDY_STATUS = [
    "DXY-regime study: INCONCLUSIVE — not wired (no regime cell cleared the gate)",
    "VAH trap-reversal study: REJECT — not wired (boot_p 0.634)",
    "800-EMA gate: candidate, not started (pre-register first)",
    "Macro layer: PLANTED / INERT — informs nothing; nothing auto-executes",
]


def _arrow(direction: str) -> str:
    if "bullish" in direction:
        return "UP"
    if "bearish" in direction:
        return "DOWN"
    return "flat"


def format_weekly_brief() -> str:
    """Build the weekly brief text from the inert macro layer. Pure (no I/O)."""
    mb = WEEKLY_MACRO_BIAS
    dxy = mb.get("dxy_current_approx", 0.0)
    regime = get_dxy_regime(dxy)
    active_flags = [k for k, v in RISK_FILTER_FLAGS.items() if v is True]
    pair_lines = [
        f"  {pair}: {_arrow(direction)} {direction} [{conviction}]"
        for pair, (direction, conviction, _reason) in PAIR_BIAS.items()
    ]
    crypto = TINO_CRYPTO_OBSERVATIONS

    return "\n".join([
        "KUDBEE QUANT — WEEKLY MACRO BRIEF (read-only)",
        f"Week of: {mb['week_of']} | Source: {mb['source']}",
        "*** Tino's discretionary read — UNVERIFIED. Nothing below is wired to the",
        "    bot, significance-tested, or actionable. Human review only. ***",
        "",
        "── MACRO SNAPSHOT (as stated by Tino, unverified) ──",
        f"CPI y/y: {mb['cpi_yoy']}% ({mb['cpi_trend']})  |  core {mb['core_cpi_yoy']}%",
        f"ISM mfg {mb['ism_manufacturing_pmi']} / svc {mb['ism_services_pmi']}",
        f"NFP {mb['nfp']}K (miss)  |  JOLTS {mb['jolts']}M (beat)",
        f"Fed {mb['fed_rate_current']}  |  hold {mb['fed_hold_prob_jul']}%  |  "
        f"hike tail {mb['fed_hike_prob_jul']}%",
        "",
        "── DXY REGIME ──",
        f"DXY ~{dxy} (key 100.0) -> {regime['regime']}",
        f"{regime['note']}",
        f"Outlook (Tino): {mb['dxy_outlook']} {mb['dxy_outlook_timeframe']}",
        "NOTE: DXY-regime effect on our crypto book tested = INCONCLUSIVE. Not wired.",
        "",
        "── FX PAIR BIAS (read-only; FX is NOT the bot's universe) ──",
        *pair_lines,
        "*** Bias only — not wired, not significance-tested. ***",
        "",
        "── SOL CRYPTO CONTEXT (Tino, unverified; observation only) ──",
        f"{crypto['instrument']} on {crypto['exchange']}",
        f"Current bias: {crypto['current_sol_position']} "
        f"(entries {crypto['sol_short_entry_range']})",
        f"Thesis: {crypto['sol_short_thesis']}",
        "Bull flip needs: " + "; ".join(crypto["bull_flip_conditions"]),
        "*** Crypto observation, not an FX/bot signal. Unverified. ***",
        "",
        "── ACTIVE RISK FLAGS (Tino's framing) ──",
        *(f"  - {f}" for f in active_flags),
        "",
        "── BOT STATUS (the honest state) ──",
        *(f"  - {s}" for s in _STUDY_STATUS),
        "",
        "Nothing is wired. Nothing auto-executes. The validated edge is unchanged:",
        "crypto top-10 / 1h confluence. All overlays above remain inert.",
    ])


def notify_weekly_brief() -> bool:
    """Send the weekly brief to Telegram if creds are set. Returns sent/not-sent.
    Opt-in: nothing calls this automatically. Never raises."""
    if not telegram_enabled():
        return False
    try:
        return send_telegram(format_weekly_brief())
    except Exception:  # noqa: BLE001 — a brief must never break a caller
        return False
