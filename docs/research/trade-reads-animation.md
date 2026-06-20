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
4. **Play/pause control** (keyboard-accessible; hidden under reduced motion) that
   freezes the frame and the reasoning stream and resumes from the same elapsed
   time — so a visitor can stop and actually read. The offscreen
   IntersectionObserver pause respects an explicit user pause.
5. **Bubble de-overlap pass** in `placeBubble` so agent notes never stack on top
   of each other (was visible in the static / mobile frame).
6. **Step controls (◀ ▶)** for reader-paced, candle-by-candle advance — the
   "thinks on each candle" intent made literal. `startTimeline` precomputes a
   `beats[]` list (one per candle + a final settle beat) and exposes a `seekTo(t)`
   that renders the exact frozen frame at time `t` using the same per-tick logic
   as the live loop (so a stepped frame matches a live pause). Stepping implies
   paused; the Left/Right arrow keys work when the controls have focus; buttons
   disable at the bounds; hidden under reduced motion (which already shows the
   full static list).

## The five setups (all grounded — sources)

Every beat maps to a real concept in the engine; nothing is invented.

| Setup | Dir | Real basis | Stars |
|---|---|---|---|
| **W · liquidity sweep** | long | `scenarios/patterns.py` double-bottom; `signals/pvsra.py` climax/vector; `levels/builder.py` psych + PDL | sweep → bull-vector reclaim → higher-low → neckline break, 3R |
| **Fade · psych-high → daily open** | short | `scenarios/library.py` `vector_fade` / `vector_at_daily_open`; round-number levels | climax spike *above* 65k round → bear-vector rejection → lower high → break the daily open |
| **Asian sweep · London reversal** | long | `context/mm_cycle.py` sessions; `levels/builder.py` Asian range; `library.py` `sweep_reversal` | time-of-day: London opens, sweeps the overnight Asian-range low, reclaims, runs |
| **PDH sweep · reclaim** | short | `levels/builder.py` PDH/PDL; `library.py` `sweep_reversal`; PVSRA bear vector | prior-day-high sweep → bear-vector reclaim → lower high → break to the PDL |
| **Confluence stack · gate** | long | `confluence/scorer.py` + `stack.py` (≥50% gate); stacked daily-open/PDL/round | levels stack → sweep of the stack → bull vector → gate passes 75% → breakout |

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

## The explainer page (`trade-story.html`)

The standalone showcase is now a full **explainer**: the widget, a "reading the
animation" legend (chips / play-pause / step / reasoning rail), a plain-English
**glossary** of every reasoning-log concept (open · session · level · sweep ·
vector · structure · confluence · backtest · risk · result) tied back to the
methodology, and a five-setups summary with long/short badges. It's linked from
the homepage hero card via a "How we read a trade, explained →" link. Page chrome
is self-contained inline CSS (CSP-safe, same posture as the rest of the site);
the one shared style (`.trade-story__more`, the homepage link) lives in
`trade-story.css`. Kept `noindex` — it's an illustrative teaching page.

## Not done here (candidates for a follow-up, if wanted)

Optionally surfacing the same engine inside `trade-flow.html`. (The discrete
**step** control and the dedicated explainer page — both listed here previously —
are now shipped.)
