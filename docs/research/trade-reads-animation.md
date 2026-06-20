# Research / design — expanded "How Kudbee reads a trade" animation

> Branch `claude/trade-reads-animation`. Scope: expand the homepage `trade-story`
> centerpiece (`assets/js/trade-story.js` + `.css`, mounted on `index.html` and the
> standalone `trade-story.html`) from a single hard-coded scenario into a longer,
> narrated, **multi-setup** walkthrough — a candle-by-candle "reasoning log" that
> explains *why*, grounded in the real methodology. **Transparency is the brief:**
> every concept shown must reflect what the system actually does, and the
> illustrative disclaimers stay loud.

## What existed before

A polished single-IIFE canvas engine: 18 candles of ONE setup (a W double-bottom
with a 64k liquidity sweep), three levels (Daily Open / Psych High / Psych Low),
five "thinking → note" agent bubbles (Liquidity, PVSRA, Structure, Reviewer,
Risk), a 3R bracket, a reviewer back-scan, a ~60s loop, a reduced-motion static
frame, responsive condensing, and an IntersectionObserver pause. Good bones — the
expansion **reuses** all of it and generalizes the data.

## What changed (this PR)

1. **Data-driven, multiple setups.** The single global `CANDLES/IDX/levels` is
   replaced by a `SCENARIOS` array. Each scenario carries its own candles, levels
   (a per-scenario list, so Asian-range setups draw Asian High/Low instead of
   Psych High/Low), index beats, agents, bracket (now **direction-aware** — works
   for shorts), result tag, and a new `thinking` track. Scenarios **cycle**, and
   the header shows clickable **setup chips** so a visitor can jump between them.
2. **The "reasoning log" rail (the headline feature).** A streaming side rail
   (below the chart on narrow screens) prints one reasoning line per important
   candle as it forms — each line tagged with **time-of-day / session** and a
   **concept chip** (open · sweep · vector · structure · confluence · backtest ·
   risk). This is the "file system that thinks on each candle" the brief asked
   for: it narrates the *why* — the daily open, the psychological level, the
   sweep, the fade, the structure, and explicitly the **backtest lens** ("a
   measured hypothesis, not a promise").
3. **Direction-aware bracket** so short setups render a correct stop-above /
   target-below zone, with the target clamped into view at either edge.

## The three setups (all grounded — sources)

Every beat maps to a real concept in the engine; nothing is invented.

| Setup | Dir | Real basis | Stars |
|---|---|---|---|
| **W · liquidity sweep** | long | `scenarios/patterns.py` double-bottom; `signals/pvsra.py` climax/vector; `levels/builder.py` psych + PDL | sweep → bull-vector reclaim → higher-low → neckline break, 3R |
| **Fade · psych-high → daily open** | short | `scenarios/library.py` `vector_fade` / `vector_at_daily_open`; round-number levels | climax spike *above* 65k round → bear-vector rejection → lower high → break the daily open |
| **Asian sweep · London reversal** | long | `context/mm_cycle.py` sessions; `levels/builder.py` Asian range; `library.py` `sweep_reversal` | time-of-day: London opens, sweeps the overnight Asian-range low, reclaims, runs |

Volume classes use the engine's real thresholds (climax ≥2× avg vol; vector ≥1.5×;
else norm — `signals/pvsra.py:13-16`). Confluence percentages shown by the
Reviewer reference the **≥50% gate** the site documents as the validated config.

## Transparency (non-negotiable, kept verbatim in spirit)

- The footer caption stays: *"Illustrative scenario — not live data, not a track
  record. The agents depict how the system reads a setup, not real signals."*
- The reasoning log's backtest line reuses the methodology framing: a pattern is
  *"a measured hypothesis, not a promise"* — never "this is a buy."
- Result tags are labelled **illustrative**; R targets are framed as plan, not
  outcome. No live-edge or returns claims anywhere.
- Screen-reader description (`.ts-sr`) is rebuilt per scenario so the narration is
  accessible, and the reasoning rail is `aria-hidden` to avoid duplicate SR spam.

## Constraints honored

Vanilla JS, no deps, no build step, single IIFE; CSP-safe (no inline handlers —
chip clicks are bound in JS); `prefers-reduced-motion` renders a static composed
frame with the full reasoning list and no loop; DPR-aware canvas; ResizeObserver
+ IntersectionObserver retained. No change to any Python / engine / live path —
this is marketing-site front-end only.

## Verification

- `node --check assets/js/trade-story.js` (syntax).
- `node scripts/check_trade_story.mjs` — invariant validator: every scenario's
  OHLC is well-formed (l ≤ o,c ≤ h), index beats and `thinking.at` are in range,
  and bracket prices sit within the visible price band. (Canvas rendering itself
  can't run headless; this guards the data that drives it.)
- Visual review on the branch's Cloudflare Pages preview (homepage + the
  `trade-story.html` showcase page) before any merge to production.

## Not done here (candidates for a follow-up, if wanted)

A 4th/5th setup (PDH sweep + reclaim short; multi-factor confluence-stack gate),
and optionally surfacing the same engine inside `trade-flow.html`. Kept out to
keep this PR reviewable.
