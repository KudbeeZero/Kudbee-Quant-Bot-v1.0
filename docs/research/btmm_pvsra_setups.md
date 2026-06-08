# Traders Reality / BTMM / PVSRA — precise mechanical setups (for testing)

Catalog of the most backtestable setups from the deep-research pass, with exact
rules and sources. Traders Reality's "Hybrid System" = PVSRA (vector candles) +
Steve Mauro's BTMM (sessions / market-maker cycle), so BTMM's precise rules are
the structural backbone. Crypto has no "pips", so pip thresholds below are
re-expressed in **ATR units** when implemented.

Honesty: these are *hypotheses with exact parameters*, not proven edges. Each
is tested with the same null-first, lookahead-audited sweep that caught a
Sharpe-9.56 lookahead bug. Source confidence noted per setup.

## Shared parameters (consistent across free BTMM sources)
- **EMA stack (15m):** 5, 13, 50, 200, 800.
- **Cross "levels":** 13/50 = Level 1; 50/200 = Level 2; 50/800 = Level 3 (overall trend filter).
- **Sessions (GMT):** High/Low reset 21:00; Asian 00:30–07:00; London 07:30–13:00; New York 13:30–21:00.
- **Risk defaults:** trade closed candles; stops 7–10 (2nd leg) / ~23 (1st leg) pips; TP1 = 50 EMA; ~50 pip/day objective.

## Backtestable setups

1. **13/50 EMA cross + close filter (Level 1).** Long when 13 EMA crosses
   above 50 EMA *and* the candle closes above the 13 EMA; short on the mirror.
   PRECISE. (BTMM simplified.)

2. **50/800 trend filter (Level 3).** Directional filter: only longs when
   50 EMA > 800 EMA, only shorts when below. PRECISE. (BTMM simplified.)

3. **Trend-pullback:** in the 50/800 trend direction, enter on a 13/50 cross
   back in trend direction (combines 1+2). PRECISE.

4. **Asian stop-hunt reversal ("Type 1 London trade").** Asian box = completed
   00:30–07:00 GMT range; require it "smooth" and **< ~40 pips** (→ range <
   ~0.8·ADR). In London, price **breaches the Asian high/low by 25–30 pips**
   (→ > ~0.15·ATR) then **closes back inside** → reversal entry. Stop beyond
   the sweep extreme; target opposite side / 50 EMA. BACKTESTABLE. (BTMM
   Secrets, CrysfoAnalysis.) — *This is the real version of the setup whose
   lookahead variant faked a +9.56 Sharpe.*

5. **Shadow-box / Brinks opening-range breakout.** Mark the **08:00–09:00 GMT**
   box (EU Brinks; the one time confirmed in free sources); trade the breakout
   in the higher-timeframe trend direction during London. BACKTESTABLE once
   timezone fixed. (TradersReality forum; Signature Traders.)

6. **Railroad-track (RRT) reversal.** Two adjacent ~equal-range candles of
   opposite direction at a session extreme → reversal. PRECISE/codeable.
   (BTMM M/W timing note.)

7. **M/W second-leg entry (the core BTMM trade).** M at high-of-day / W at
   low-of-day (two peaks/troughs ~30–90 min apart). Enter on neckline break
   confirmed by a 13/50 cross and close beyond the 13 EMA. Stop beyond HOD/LOD.
   Needs a swing-pivot/neckline detector. PARTIAL (one discretionary piece).
   (BTMM, BTMM Secrets.)

8. **Vector-zone retest rejection (PVSRA Setup 4).** Price returns to a prior
   climax-vector candle's price box and rejects → enter in the original
   vector's direction. Zone = the vector candle's OHLC range (precise); the
   rejection trigger is the interpretive piece. MEDIUM. (TradingView Vector
   Candle Zones.)

9. **Sweep + opposing vector (PVSRA Setup 6).** Price sweeps a prior swing /
   Asian-box edge and prints an opposing climax vector on the sweep → reversal.
   MEDIUM. (BTMM stop-hunt + PVSRA.)

10. **ADR-exhaustion fade.** When the day has used ~a full ADR and price sits
    at the ADR extreme, fade toward the mean with a reversal candle. The exact
    % (the speculated "85%") is **unconfirmed** — parameterized. PARTIAL.

## Vague / not hard-coded (per research caveats)
- "Three pushes" (no objective push definition); exact Brinks clock beyond EU
  08:00–09:00 GMT; a single guaranteed weekly-high weekday; Mauro's exact TDI
  settings; ADR fade %. Tested only as parameterized hypotheses, never as
  asserted constants.

Sources: see `tino_traders_reality.md` plus the per-setup citations above
(BTMM simplified / Secrets via pdfcoffee; TradingView TradersReality scripts;
TradersReality forum Brinks; CrysfoAnalysis BTMM walk-through).
