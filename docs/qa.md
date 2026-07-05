# Cross-device UI QA checklist

The static site is responsive by construction (viewport meta on all pages,
980/680px breakpoints, fluid `clamp()` type, hamburger nav, skip-link, strong
ARIA — audited 7.5/10). This checklist is the **pixel pass** to run in a real
browser/device (the container here has no headless browser, so this must be done
in a browser-enabled session or on devices).

## Viewports to test
| Device | Width | Notes |
|---|---|---|
| iPhone SE / mini | 375px | tightest common phone — the key target |
| iPhone 14/15 Pro | 393px | |
| Android (Pixel) | 412px | |
| iPad portrait | 768px | hits the 980px breakpoint |
| iPad landscape | 1024px | |
| Desktop | 1280–1920px | |

## Per-page checks (index, compare, lab, methodology, glossary, contact, blog, start-here)
- [ ] No horizontal page scroll / overflow at 375px (only the `.compare` table may scroll, intentionally).
- [ ] Header: hamburger opens/closes; links + CTA reachable and not overlapping on short screens.
- [ ] Tap targets ≥ 44px (buttons, nav links, form controls, lab inputs/select).
- [ ] Type legible (≥ ~12px effective); no clipped headings; `clamp()` scales hero cleanly.
- [ ] Focus-visible outlines on keyboard tab; skip-link works.
- [ ] Dark theme contrast OK; (light/`prefers-color-scheme` is not yet implemented — design choice).

## Lab page specifics (assets/js/lab.js)
- [ ] Charts now use `height:auto` + viewBox → they scale proportionally, no fixed
      380px letterbox. Confirm axis labels are readable at 375px; if still cramped,
      the next step is **responsive re-render** (redraw at container width on
      `resize`) rather than pure downscale — TODO, needs visual iteration.
- [ ] Calculator + venue `<select>` usable on touch; inputs ≥ 44px.
- [ ] `.chart-wrap` never causes page-level horizontal scroll.

## Known follow-ups (need a browser to do well)
1. **Partials build (Dev 3)** — de-dup the header/footer across 18 files via
   a to-be-created `scripts/build_site.py` + `partials/` (neither exists yet);
   verify byte-stable regeneration and
   identical nav on every page.
2. **Responsive chart re-render (Dev 5+)** — redraw charts at the container's true
   width on resize for crisp mobile labels.
3. **Compare table → stacked cards < 480px** — optional; current smooth-scroll fit
   is acceptable but cards read better on phones (needs `data-label` on each `<td>`).

## How to run (browser-enabled session)
```bash
python -m http.server 8080      # serve the static site
# then drive a headless browser (playwright/puppeteer) at the viewports above,
# screenshot each page, and walk this checklist.
```
