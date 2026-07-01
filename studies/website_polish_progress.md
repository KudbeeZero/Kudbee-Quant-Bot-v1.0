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

Loop started: 2026-06-27 (~15:40 UTC); EXTENDED by owner re-invocation ~19:26 UTC. Continue until all pages checked or owner stops.

## Checklist
- [x] **0. Global design system** (`style.css` polish layer): refined depth/shadows,
      fluid type scale, button/card/nav polish, focus-visible, selection, scrollbar,
      section rhythm. (Lifts every page at once.)
- [x] 1a. `index.html` trade-reads showcase — EXPANDED to 8 setups (4 long / 4 short): added Trend short, Breakdown·retest, Trend long; every scenario now narrates POSITION management (1% risk, bank half @1R → BE → ride 3R). Goal-driven.
- [x] 1b. `index.html` — hero highlights get honey accent + hover; FAQ accordions get depth/hover; trust row firmed. Screenshot-verified.
- [x] 2. `methodology.html` — editorial drop-cap opener, honey numbered-badge ordered lists (Layer 3 + honesty contract), refined prose-link underlines. Page-local scoped style; all internal links verified. Screenshot-verified.
- [x] 3. `start-here.html` — copy clean; methodology cross-link added; path-step depth + number-badge hover via shared CONTENT-PAGES layer. (2026-07-01)
- [x] 4. `about.html` — drop-cap + prose-link treatment (methodology parity); honesty fix ('prove'→'test'); pipeline sentence links methodology. (2026-07-01)
- [x] 5. `lab.html` — REFRESHED stale data: regenerated lab-data.js from the live engine (generated 2026-06-27, was 2026-06-09; 10 crypto + 6 stocks); made the generator's date dynamic; fixed '+-0.112R' sign-format bug in lab.js. All page claims re-verified against fresh numbers.
- [x] 6. `compare.html` — over-claim fixed ('Tick-accurate'→'Event-driven', matches the real backtester); table row-hover polish. (2026-07-01)
- [x] 7. `live-signals.html` — SEO done earlier (canonical+OG, intentional noindex); dynamic page, graceful offline fallback verified in the sweep. (2026-07-01)
- [x] 8. `glossary.html` — nav normalized (was the only page missing Blog), footer enriched, Start-Here CTA link; term-card hover rail. (2026-07-01)
- [x] 9. `trade-story.html` / `trade-flow.html` — canonical + OG/Twitter share cards added; both stay intentional noindex (demo/sandbox). (2026-07-01)
- [x] 10. `blog/` — shared article layer (drop-cap, byline badge, button prev/next); all 7 posts proofread, zero typos, links verified. (2026-07-01)
- [x] 11. `404.html` (theme-color, glow backdrop, blog link) + cross-page consistency (lang/viewport/theme-color everywhere, zero img-alt gaps) + full mobile(375)/desktop(1440) Playwright sweep over all 22 pages. (2026-07-01)

## Screenshots
- index_before.png captured (scratchpad) before polish layer.

## SEO + AEO/AI-search track (owner: ranking on Google + AI engines once domain connects)
Baseline audit (2026-06-27): most pages already have title/desc/canonical/OG/Twitter/JSON-LD.
Gaps being closed one page per iteration:
- [x] SEO: `lab.html` — added OG + Twitter + JSON-LD (WebPage + **Dataset** for AEO + BreadcrumbList) + new `assets/img/og/og-lab.svg`. JSON-LD validated.
- [x] SEO: `live-signals.html` — kept intentional `noindex,follow` (volatile live data, borderline advice) but added canonical + OG/Twitter cards (social-share preview) + new `og-live-signals.svg`. No JSON-LD (noindex → no rich-result need).
- [x] SEO: `trade-story.html` + `trade-flow.html` — canonical + OG/Twitter added; kept noindex (demo-only), so no JSON-LD needed. (2026-07-01)
- [x] SEO: `be-report.html` — full head (desc/canonical/robots/OG/Twitter/theme-color) + Article/Breadcrumb JSON-LD + dated 2026-07-01 update note; added to sitemap. (2026-07-01)
- [x] SEO: `leverage-report.html` — Article + Breadcrumb JSON-LD added. (2026-07-01)
- [x] SEO: `sitemap.xml` — + be-report; live-signals/trade-story/trade-flow correctly EXCLUDED (noindex); lastmod refreshed; XML validated. (2026-07-01)
- [x] SEO: `llms.txt` — verified current; + Lab, leverage-report, be-report; email fixed to hello@kudbeex.xyz. (2026-07-01)
- [x] SEO: global pass — lang/viewport/theme-color on every page; no img-alt gaps (all inline aria-hidden SVGs); WebSite+SearchAction JSON-LD already on index. DOMAIN RESOLVED: the site standard is kudbeex.xyz (123 refs incl. sitemap/robots/llms); the 11 stray kudbeequant.com EMAILS were standardized to @kudbeex.xyz — owner must create/forward hello@/partners@/press@kudbeex.xyz. (2026-07-01)
