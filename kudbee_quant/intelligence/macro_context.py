"""Macro Context Layer — Kudbee Quant Bot (READ-ONLY, PLANTED, NOT WIRED).

Source: Tino Pistou / Traders Reality "Opening Bell" briefing, week of 2026-06-07.
Captured: 2026-06-26.

──────────────────────────────────────────────────────────────────────────────
HONESTY HEADER — read before trusting anything in this file
──────────────────────────────────────────────────────────────────────────────
1. **This is Tino's DISCRETIONARY macro OPINION, not verified fact.** Every number
   below (CPI, JOLTS, DXY level, Gold price, FOMC probabilities, pair biases) is
   as *stated by Tino in a video* and has NOT been independently confirmed against
   a primary data source. Treat the whole module as a transcript, not ground truth.
   Field/section names deliberately avoid the word "confirmed".
2. **The live book trades CRYPTO** (TOP_10_CRYPTO, 1h — see kudbee_quant.universe).
   The ``PAIR_BIAS`` entries below are FX pairs (EURUSD, GBPUSD, USDJPY, XAUUSD…)
   that the bot does **not** trade. Only the DXY/gold *regime* has a plausible
   (still unvalidated) link to BTC via the dollar correlation noted in
   ``research/traders_reality_research_vol11.md``.
3. **Nothing here is wired to anything.** No scanner, signal, bracket, resolver,
   risk, or execution code imports this module. It is a planted reference layer:
   data + two pure classifier functions, no I/O, no side effects, never raises.
   Per the project thesis (CLAUDE.md / docs/MEMORY.md), it must clear the
   significance gate via a backtest before it could ever inform a live decision.
4. There is ALSO ``kudbee_quant/intelligence/event_calendar.py`` — that is the
   LIVE, owner-maintained binary-event gate. The ``HIGH_IMPACT_EVENTS`` block
   here is briefing-only and does **not** replace it.
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

# The instruments the bot actually trades. Stated here so any future reader sees
# at a glance that the FX-heavy data below is CONTEXT, not the live universe.
LIVE_BOOK = "crypto TOP_10_CRYPTO on 1h (see kudbee_quant.universe.TOP_10_CRYPTO)"


# ─────────────────────────────────────────
# SECTION 1: TINO'S WEEKLY MACRO READ
# Discretionary opinion as stated by Tino — UNVERIFIED. Not confirmed data.
# ─────────────────────────────────────────

WEEKLY_MACRO_BIAS = {
    "week_of": "2026-06-07",
    "source": "Tino Pistou - Opening Bell / Traders Reality",
    "captured": "2026-06-26",
    "nature": "discretionary_opinion",   # NOT verified fact
    "verified": False,                    # no primary-source confirmation
    "applies_to_live_book": False,        # bot trades crypto, this is FX/macro

    # ── INFLATION (as stated by Tino; not verified) ──
    "cpi_yoy": 4.2,
    # Tino: beat vs 3.8% forecast. Jan 2026 low was 2.4%.
    # Framed as re-accelerating trend, not a blip.
    "cpi_trend": "rising",
    "core_cpi_yoy": 2.9,
    "eur_core_cpi_flash": 2.5,
    # Tino: EUR CPI also rising (prior 2.2%) — global reflation

    # ── LABOR (as stated by Tino; not verified) ──
    "jolts": 7.62,           # millions — Tino: strong beat vs 6.87M prior
    "adp_nfp": 122,          # thousands — Tino: mild beat
    "unemployment_claims": 225,  # thousands — Tino: normal range
    "nfp": 172,              # thousands — Tino: MISS vs ~225K expected
    # Tino: mixed — jobs added but below expectations; negative Fri reaction

    # ── MANUFACTURING / SERVICES (as stated by Tino; not verified) ──
    "ism_manufacturing_pmi": 54.0,   # Tino: prior 52.7 — expanding
    "ism_services_pmi": 54.5,        # Tino: prior 53.6 — strong
    "ism_mfg_prices": 82.1,
    # Tino: 82.1 vs 85.3 forecast — still hot; supply-chain inflation embedded

    # ── FED / RATES (as stated by Tino; not verified) ──
    "fed_rate_current": "3.50-3.75",   # Tino: Fed holding, no cuts expected
    "fed_hold_prob_jul": 85.8,
    "fed_hike_prob_jul": 12.6,
    # Tino: 12.6% hike tail is non-trivial and not priced in
    "fed_cut_expected": False,
    "fomc_next_meeting_note": "Jun 18-20 2026 passed. Sep 16 next.",
    "fomc_sep_hold_prob": 85.8,
    "fomc_sep_hike_prob": 12.6,

    # ── DXY / USD (as stated by Tino; not verified) ──
    "dxy_current_approx": 96.2,
    # Tino: below key 100 level — not a confirmed bull breakout yet
    "dxy_key_level": 100.0,
    # Tino explicit: break above 100 = "USD reign confirmed"; below = building base
    "dxy_outlook": "bullish",
    "dxy_outlook_timeframe": "2-3 quarters",   # Tino explicit multi-quarter call
    "dxy_breakout_confirmed": False,           # flips True only on daily close > 100

    # ── GOLD / XAUUSD (as stated by Tino; not verified) ──
    "gold_current_approx": 4154.0,   # Tino chart: peaked ~5200, sold off to ~4154
    "gold_recent_high": 5200.0,
    "gold_key_supports": [4047.0, 3799.0, 3798.0],
    "gold_trend": "correcting",
    # Tino: high inflation = gold bullish, but high rates + strong USD = bearish;
    # rates/USD narrative currently dominating
    "gold_bias": "neutral_to_bearish",

    # ── OIL (as stated by Tino; not verified) ──
    "oil_regime": "elevated_but_correcting",
    # Tino: USD up + oil down = divergence; OPEC (Jun 7-13) a wildcard
    "oil_dollar_divergence": True,

    # ── STOCK MARKET (as stated by Tino; not verified) ──
    "sp500_friday_move": "slump_not_trend_change",   # Tino explicit: rotation, not reversal
    "sector_rotation_signal": "defensive",           # Tino: Healthcare + Staples moving
    "risk_sentiment": "cautious",

    # ── CAPITAL FLOWS (as stated by Tino; not verified) ──
    "capital_flow_direction": "USD",   # Tino: rate differential pulls EUR/GBP -> USD
    "consumer_sentiment": "concerned",
}


# ─────────────────────────────────────────
# SECTION 2: DERIVED PAIR BIAS (FX — NOT the bot's universe)
# Read-only reference. Never auto-execute. The bot does not trade these pairs.
# Format: "PAIR": ("direction", "conviction", "reason")
# ─────────────────────────────────────────

PAIR_BIAS = {
    "EURUSD": (
        "bearish", "high",
        "USD rate differential dominant. EUR CPI rising but ECB less hawkish "
        "than Fed. Capital flows USD.",
    ),
    "GBPUSD": (
        "bearish", "medium",
        "GBP raising rates but USD stronger. Capital flow differential favors USD.",
    ),
    "USDJPY": (
        "bullish", "high",
        "BOJ ultra-loose vs Fed 3.5-3.75%. Carry trade strongly favors USD. "
        "Yen structurally weak in this regime.",
    ),
    "USDCAD": (
        "bullish", "medium",
        "USD strong. Oil correcting (CAD headwind). Double tailwind for USDCAD longs.",
    ),
    "XAUUSD": (
        "neutral_to_bearish", "low",
        "Inflation = bullish gold; high rates + USD = bearish gold. Conflict. "
        "Slight bearish given rate regime. Chart in correction from 5200.",
    ),
    "USDCHF": (
        "bullish", "medium",
        "SNB less hawkish. USD rate advantage. Safe-haven flows mixed but USD winning.",
    ),
    "AUDUSD": (
        "bearish", "medium",
        "Risk-off rotation, defensive sectors leading. AUD = risk proxy. USD dominant.",
    ),
    "NZDUSD": (
        "bearish", "medium",
        "Same as AUDUSD. Risk-off + USD strength.",
    ),
}


# ─────────────────────────────────────────
# SECTION 3: DXY REGIME MONITOR
# Pure classifier over Tino's key-100 framework. No I/O. Call with a live DXY
# price to label the regime; do NOT use it to auto-execute anything.
# ─────────────────────────────────────────

def get_dxy_regime(dxy_price: float) -> dict:
    """Classify the DXY regime using Tino's key 100-level framework.

    Returns a dict with a regime label, a note, and a ``pair_bias_multiplier``
    in [0, 1] expressing how much weight Tino's USD-bullish read would carry at
    that level. Advisory only — nothing consumes this yet.
    """
    if dxy_price > 100.0:
        return {
            "regime": "USD_BULL_CONFIRMED",
            "note": "DXY above 100. Tino framework: reign confirmed.",
            "pair_bias_multiplier": 1.0,
        }
    elif dxy_price >= 98.0:
        return {
            "regime": "USD_APPROACHING_KEY",
            "note": "DXY 98-100. Approaching Tino's confirmation zone.",
            "pair_bias_multiplier": 0.75,
        }
    elif dxy_price >= 95.0:
        return {
            "regime": "USD_BASE_BUILDING",
            "note": "DXY 95-98. Current zone. Building base.",
            "pair_bias_multiplier": 0.5,
        }
    else:
        return {
            "regime": "USD_WEAK",
            "note": "DXY below 95. Re-evaluate USD bias.",
            "pair_bias_multiplier": 0.0,
        }


# ─────────────────────────────────────────
# SECTION 4: GOLD REGIME MONITOR
# Pure classifier over Tino's chart structure (peak ~5200 -> ~4154, supports below).
# ─────────────────────────────────────────

def get_gold_regime(gold_price: float) -> dict:
    """Classify the gold regime using Tino's chart levels. Advisory only."""
    if gold_price > 4500.0:
        return {
            "regime": "GOLD_RECOVERY",
            "note": "Above 4500. Partial recovery from highs.",
            "bias": "neutral",
        }
    elif gold_price >= 4047.0:
        return {
            "regime": "GOLD_CORRECTING",
            "note": "4047-4500 range. Correction zone. Tino chart support at 4047.",
            "bias": "neutral_to_bearish",
        }
    elif gold_price >= 3799.0:
        return {
            "regime": "GOLD_AT_SUPPORT",
            "note": "Tino support zone 3799-4047. Watch for bounce or break.",
            "bias": "neutral",
        }
    else:
        return {
            "regime": "GOLD_BREAKDOWN",
            "note": "Below 3799 Tino support. Bearish.",
            "bias": "bearish",
        }


# ─────────────────────────────────────────
# SECTION 5: HIGH-IMPACT EVENT CALENDAR (briefing-only)
# NOTE: the LIVE binary-event gate is kudbee_quant/intelligence/event_calendar.py.
# This block is a human-readable briefing snapshot, NOT a second gate.
# ─────────────────────────────────────────

HIGH_IMPACT_EVENTS = {
    "2026-06-10": {
        "event": "CPI y/y",
        "actual": 4.2, "forecast": 3.8, "beat": True,
        "impact": "USD bullish surprise (as stated by Tino; unverified)",
    },
    "2026-06-18": {
        "event": "FOMC Meeting (estimated passed)",
        "result": "HOLD at 3.50-3.75 (Tino: 85.8% hold prob)",
        "note": "Verify actual outcome against a primary source",
    },
    "2026-09-16": {
        "event": "FOMC Meeting",
        "hold_prob": 85.8, "hike_prob": 12.6,
        "note": "Consider reduced sizing within 48h (human decision only)",
        "status": "upcoming",
    },
}

# Hours before a high-impact event to FLAG for caution (human decision only).
PRE_EVENT_CAUTION_HOURS = 24


# ─────────────────────────────────────────
# SECTION 6: RISK FILTER SIGNALS
# READ-ONLY advisory flags. A human must review before acting on any of them.
# These are Tino's framings, not validated signals.
# ─────────────────────────────────────────

RISK_FILTER_FLAGS = {
    "inflation_re_accelerating": True,
    # Tino: CPI 2.4% Jan -> 4.2% now = trend change; Fed cannot cut; hike tail alive
    "hike_tail_risk_active": True,
    # Tino: 12.6% hike prob; a hot CPI print could lift it fast
    "dxy_below_confirmation": True,
    # Tino: DXY ~96.2, not above 100 — USD bias valid but unconfirmed
    "gold_in_major_correction": True,
    # Tino: gold 5200 -> 4154; rate environment a headwind
    "oil_opec_wildcard": True,
    # Tino: OPEC supply uncertainty; oil not tracking inflation cleanly
    "stock_defensive_rotation": True,
    # Tino: Friday = slump not trend change; Healthcare/Staples leading = late-cycle
    "fomc_window_caution": False,
    # Set True manually within 48h of an FOMC meeting (next: Sep 16)
    "reduce_position_near_cpi": True,
    # Tino: next CPI (est Jul 14) could move markets; consider lighter sizing 24h prior
}


# ─────────────────────────────────────────
# SECTION 7: TINO THESIS SUMMARY (for a Telegram briefing / audit log)
# ─────────────────────────────────────────

TINO_THESIS_WEEK = """
TINO OPENING BELL — Week Jun 7-13 2026  (discretionary view, UNVERIFIED)

CORE THESIS:
Stagflationary lean. Economy hot (ISM 54+, JOLTS 7.62M). Inflation said to be
re-accelerating (CPI 4.2% from a 2.4% Jan low). Fed holding, no cuts; 12.6% hike
tail alive. Dollar to "reign supreme" for 2-3 quarters.

DXY: ~96.2. Must break 100 for full confirmation (not yet).
Gold: major correction (5200 -> 4154); rate regime = headwind.
Oil: down while dollar up = divergence; OPEC wildcard.
Friday selloff: rotation slump, not trend reversal.
Defensive sectors (Healthcare, Consumer Staples) moving.

PAIR BIAS (FX — NOT the bot's crypto universe):
USD bullish vs EUR, GBP, AUD, NZD (rate differential + capital flow)
USDJPY: strong bullish (BOJ ultra-loose vs Fed 3.5-3.75%)
USDCAD: bullish (USD strong + oil correcting)
XAUUSD: neutral-to-bearish (rate headwind dominates)

RISK FLAGS: CPI re-acceleration; 12.6% hike tail; DXY 100 = key confirmation
(not broken); FOMC Sep 16 = next major event risk.

REMINDER: none of the above is verified or wired to the bot. The live edge is
crypto top-10/1h confluence; any macro overlay must clear the significance gate
(see research/traders_reality_research_vol11.md) before informing a live trade.
"""


# ─────────────────────────────────────────
# SECTION 8: TINO CRYPTO METHODOLOGY OBSERVATIONS
# Source: BTCC SOLUSDT trade-log analysis, 2026-06-22..06-27.
# READ-ONLY educational context. UNVERIFIED. NOT wired to any bot signal.
# ─────────────────────────────────────────

# DISCLAIMER: these are observations of Tino's discretionary SOLUSDT perp trades
# on a copy-trade platform at 42x leverage. They are NOT the bot's universe, NOT
# verified, and NOT a signal input. Cross-asset *methodology* notes only — they
# describe HOW he trades (scale-in, hedge-then-flip, EMA/level gates), which is
# context for candidate studies, not a basis for any live decision.

TINO_CRYPTO_OBSERVATIONS = {
    "instrument": "SOLUSDT Perp 42x",
    "exchange": "BTCC (copy-trade platform)",
    "observation_period": "2026-06-22 to 2026-06-27",
    "verified": False,                 # discretionary log read, not confirmed
    "applies_to_live_book": False,     # bot trades top-10 crypto confluence, not this

    # ── methodology observed (the transferable part) ──
    "entry_style": "scale_in",          # 3-7 fills around a level, not one shot
    "hold_time": "swing_1_to_3_days",   # swing despite 42x, not an intraday scalp
    "flip_style": "hedge_then_flip",    # opens the new side BEFORE closing the old
    # e.g. 06/26: shorted ~70.24 at 09:03 UTC while longs stayed open until
    # ~73.67 at 14:31 UTC — locks the next position, then banks the current.

    # ── SOL-specific levels (USDT; unverified) ──
    "sol_range_top": 74.5,
    "sol_range_bottom": 65.0,
    "sol_range_size_approx": 9.0,
    "sol_800_ema_zone": "72.0-74.5",
    # 800 EMA (Tino's TF, unverified) acts as the macro ceiling. Rejection =
    # short bias; a clean close + hold above on retest = bull flip. This "EMA gate"
    # is the transferable idea worth testing (see EMA_800_STUDY_CANDIDATE below).

    # ── current state (as of 2026-06-27, unverified) ──
    "current_sol_position": "short",
    "sol_short_entry_range": "70.24 to 72.23",
    "sol_short_avg_approx": 70.9,
    "sol_current_price_approx": 72.7,
    "sol_short_thesis": (
        "Rejection of 800 EMA / Psy-Hi (~43B mcap, ~74.5). Closed longs at ~73.67 "
        "after the NY push, shorting back toward the 65-66 support zone."
    ),

    # ── BTMM principles visible (methodology continuity, not signals) ──
    "session_timing": True,             # entries cluster at London open (~09:00 UTC)
    "level_framework": [
        "Psy-Hi (~74.5 SOL / ~43B mcap)",
        "Psy-Lo (~72.5 SOL)",
        "YDay Hi (~70.8 SOL)",
        "Daily Open (~67.8 SOL)",
        "800 EMA (Tino's TF) — resistance",
    ],
    "pvsra_applicable": True,           # red climax at Psy-Hi = distribution (observed)

    "bull_flip_conditions": [
        "Hourly close above the 800 EMA zone (~74.5)",
        "PVSRA: green/teal rising-volume candle on the reclaim",
        "Holds above the 800 EMA on the retest (intrabar spikes do NOT count)",
    ],

    "fx_relevance": (
        "Same BTMM framework across assets: session killzones, psychological "
        "levels, EMA-rejection gates, scale-in entries. The 800-EMA gate is a "
        "candidate confluence filter for the validated crypto book — but it must "
        "clear the same bootstrap significance gate as the DXY/VAH studies, with a "
        "PRE-REGISTERED hypothesis, before any wiring."
    ),
}

# Candidate study (NOT started, NOT wired). Pre-register before running, then
# put it through the same bootstrap gate as the DXY (INCONCLUSIVE) and VAH
# (REJECT) studies. Positive-and-significant-and-meaningful, or it stays inert.
EMA_800_STUDY_CANDIDATE = {
    "status": "proposed_not_started",
    "hypothesis": (
        "On the validated top-10/1h population, signals taken on the side of the "
        "800 EMA (longs above / shorts below) show higher net-R per trade than "
        "signals taken against it."
    ),
    "requires": "pre_registration_before_running",
    "gate": "n>=30 AND boot_p<0.05 AND improvement>0.02R (same as DXY/VAH)",
    "priority": "owner's call — next candidate after the two negatives",
}
