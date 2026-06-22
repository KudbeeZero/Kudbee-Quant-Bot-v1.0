"""One-shot LIVE price-action read against the BTMM / M-level / day-color framework.

For each major: current price vs the M-level grid, the prior-day color projection,
the psychological round levels, daily/NY open, ADR extension, and how many times the
current NY day has REJECTED the prior-day high/low and the daily open. Read-only;
no journal, no trading. Run: PYTHONPATH=. python scripts/live_level_read.py
"""
from __future__ import annotations

import pandas as pd

from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels
from kudbee_quant.levels.builder import ny_session_date
from kudbee_quant.notifications.notify import _g

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
MLEVELS = ["mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5"]


def _pos_vs(price, level):
    if level is None or pd.isna(level):
        return "n/a"
    return "ABOVE" if price >= level else "below"


def _m_zone(price, row):
    """Which M-band is price in? Returns (label, lower_tag, upper_tag)."""
    grid = [(m, row.get(m)) for m in MLEVELS if not pd.isna(row.get(m))]
    grid.sort(key=lambda kv: kv[1])
    if not grid:
        return "n/a"
    if price < grid[0][1]:
        return f"BELOW {grid[0][0][-2:].upper()} ({_g(grid[0][1])}) — under the grid"
    if price >= grid[-1][1]:
        return f"ABOVE {grid[-1][0][-2:].upper()} ({_g(grid[-1][1])}) — above the grid"
    for (lo_m, lo_v), (hi_m, hi_v) in zip(grid, grid[1:]):
        if lo_v <= price < hi_v:
            span = hi_v - lo_v
            frac = (price - lo_v) / span if span else 0
            return (f"in {lo_m[-2:].upper()}-{hi_m[-2:].upper()} band "
                    f"({_g(lo_v)} – {_g(hi_v)}), {frac*100:.0f}% up the band")
    return "n/a"


def _reject_count(day_bars, level, *, side):
    """Count bars that TAPPED a level and closed back (a rejection). side='res'
    => wick above, close below; side='sup' => wick below, close above."""
    if level is None or pd.isna(level):
        return 0
    n = 0
    for _, b in day_bars.iterrows():
        if side == "res" and b["high"] >= level and b["close"] < level:
            n += 1
        if side == "sup" and b["low"] <= level and b["close"] > level:
            n += 1
    return n


def read_symbol(client, sym):
    df = build_levels(client.klines(sym, interval="1h", limit=400))
    df["ny_date"] = ny_session_date(df["timestamp"])
    row = df.iloc[-1]
    price = float(row["close"])
    today = df[df["ny_date"] == row["ny_date"]]

    color = row.get("prev_day_color")
    color_txt = ("🟢 GREEN" if color == 1 else "🔴 RED" if color == -1 else "⚪ flat")
    # BTMM day projection: after a GREEN day, price tends to work the UPPER grid
    # (M3->M4/M5, buy dips into M2/M3); after a RED day, the LOWER grid (M3->M2/M1,
    # sell rallies into M3/M4). This is the day-color bias, not a guarantee.
    if color == 1:
        proj = "prior day GREEN → bias works M3→M4/M5; buy dips into M2/M3 (longs favoured)"
    elif color == -1:
        proj = "prior day RED → bias works M3→M2/M1; sell rallies into M3/M4 (shorts favoured)"
    else:
        proj = "prior day flat → no clean day-color bias"

    psy_lo, psy_hi = row.get("round_below"), row.get("round_above")
    if not pd.isna(psy_hi) and price >= psy_hi:
        psy_txt = f"ABOVE psych {_g(psy_hi)} → favours LONGS"
    elif not pd.isna(psy_lo) and price < psy_lo:
        psy_txt = f"BELOW psych {_g(psy_lo)} → favours SHORTS"
    else:
        psy_txt = f"between psych {_g(psy_lo)}–{_g(psy_hi)} → no clean psych bias"

    pdh, pdl, do = row.get("pdh"), row.get("pdl"), row.get("daily_open")
    rej_pdh = _reject_count(today, pdh, side="res")
    rej_pdl = _reject_count(today, pdl, side="sup")
    rej_do_res = _reject_count(today, do, side="res")
    rej_do_sup = _reject_count(today, do, side="sup")
    pct_adr = row.get("pct_adr_used")

    print(f"\n{'='*70}\n{sym}   price {_g(price)}")
    print(f"  Prior-day color : {color_txt}  →  {proj}")
    print(f"  M-level zone    : {_m_zone(price, row)}")
    print(f"  Pivot PP        : {_g(row.get('pivot_pp'))}  (price {_pos_vs(price, row.get('pivot_pp'))})")
    print(f"  Psychological   : {psy_txt}")
    print(f"  Daily open      : {_g(do)}  (price {_pos_vs(price, do)})  "
          f"| NY open {_g(row.get('ny_open'))} (price {_pos_vs(price, row.get('ny_open'))})")
    print(f"  Prior day H/L   : PDH {_g(pdh)} (price {_pos_vs(price, pdh)}) | "
          f"PDL {_g(pdl)} (price {_pos_vs(price, pdl)})")
    print(f"  Rejections today: PDH rejected {rej_pdh}x | PDL held {rej_pdl}x | "
          f"daily-open rejected {rej_do_res}x from above / {rej_do_sup}x from below")
    print(f"  ADR band        : {_g(row.get('adr_low'))} – {_g(row.get('adr_high'))}  "
          f"({pct_adr*100:.0f}% of ADR used)" if not pd.isna(pct_adr) else "")
    print(f"  NY Brinks box   : {_g(row.get('ny_brinks_low'))} – {_g(row.get('ny_brinks_high'))}  "
          f"| Asian {_g(row.get('asian_low'))} – {_g(row.get('asian_high'))}")


def main():
    client = BinanceClient()
    ts = pd.Timestamp.now(tz="America/New_York")
    print(f"LIVE LEVEL READ — {ts:%Y-%m-%d %H:%M} NY")
    for sym in SYMS:
        try:
            read_symbol(client, sym)
        except Exception as e:  # noqa: BLE001
            print(f"\n{sym}: read failed ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
