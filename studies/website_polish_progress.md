# Website Premium-Polish — loop tracker

Goal: elevate the **existing Kudbee Quant** marketing site to a "$10k" level of
craft — typography, spacing, hierarchy, depth, component polish, motion,
responsiveness, a11y. **Refinement, not a rebrand.**

## Hard rules (every iteration)
- Keep **Kudbee Quant** branding. The Ascendancy rebrand is PARKED (needs owner's
  TradingView URL + brand direction + logo). Do NOT introduce Ascendancy here.
- **No fabricated stats / no public performance or returns claims** (repo norm).
  Only honest, verifiable copy. Keep the existing "anti-hype / measure honestly" voice.
- Content + marketing CSS/HTML only. Do NOT touch backend/API, trading/execution,
  resolver/bracket/journal, or workflows. Marketing pages use `assets/css/style.css`
  (hand-written; NO Tailwind rebuild needed — edits apply directly).
- Prefer an **additive "PREMIUM POLISH LAYER"** appended at the end of `style.css`
  (scoped overrides) so the existing cascade isn't destabilised; per-page tweaks
  inline or in the page's own section.
- **Screenshot-verify** before/after each page with chromium headless:
  `CHROME=$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome|head -1)`
  `"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1440,2200 --screenshot=OUT.png "file://$PWD/PAGE.html"`
  (Google-Fonts SSL errors in headless are cosmetic — fonts load fine in prod.)
- Commit + push to `feat/website-premium-polish` each iteration. Keep ONE draft PR.
  **Do NOT merge** — production visual change awaits the owner reviewing the
  Cloudflare preview. Mark PR ready only when the sweep is complete.

## Loop protocol (dynamic /loop, self-paced ~15 min)
Each wake: pick next unchecked item → polish → screenshot-verify → commit+push →
check it off here (with a one-line note) → re-arm ScheduleWakeup if items remain
and < ~2h since loop start; else mark PR ready + post preview URL + stop.

Loop started: 2026-06-27 (~15:40 UTC). Stop by ~17:40 UTC or when all checked.

## Checklist
- [x] **0. Global design system** (`style.css` polish layer): refined depth/shadows,
      fluid type scale, button/card/nav polish, focus-visible, selection, scrollbar,
      section rhythm. (Lifts every page at once.)
- [ ] 1. `index.html` — hero, feature cards, ticker, sections, footer
- [ ] 2. `methodology.html`
- [ ] 3. `start-here.html`
- [ ] 4. `about.html`
- [ ] 5. `lab.html`
- [ ] 6. `compare.html`
- [ ] 7. `live-signals.html`
- [ ] 8. `glossary.html`
- [ ] 9. `trade-story.html` / `trade-flow.html`
- [ ] 10. `blog/` index + posts (shared article styling)
- [ ] 11. `404.html` + final cross-page consistency + responsive (mobile) pass

## Screenshots
- index_before.png captured (scratchpad) before polish layer.
