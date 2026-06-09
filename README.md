# Kudbee Quant — Marketing Website

The marketing / waitlist site for **Kudbee Quant** — the quant cockpit for modern traders:
real-time trade signals, institutional-grade analytics, and a no-code strategy backtesting engine.

> This repo holds the **front-end marketing site only**. The trading engine / backend lives separately.

## Tech

Zero-dependency **static HTML / CSS / JS** — fast, SEO-friendly, and deployable anywhere
(GitHub Pages, Netlify, Vercel, Cloudflare Pages, S3, etc.). No build step required.

```
.
├── index.html            # Landing page
├── glossary.html         # Quant-terms glossary (AEO / SEO asset)
├── 404.html              # Branded not-found page
├── robots.txt            # Crawler directives (incl. AI bots)
├── sitemap.xml           # Sitemap for search engines
├── llms.txt              # AI-crawler site summary (emerging standard)
├── site.webmanifest      # PWA / icon metadata
├── _headers              # Security headers (Netlify / Cloudflare Pages)
├── netlify.toml          # Netlify config + headers + 404 redirect
└── assets/
    ├── css/style.css     # Design system + page styles
    ├── js/main.js        # Animations, counters, charts, search, waitlist
    └── img/
        ├── favicon.svg   # Hex/bee mark
        └── og-cover.svg  # Social share image
```

## Run locally

No tooling needed — just serve the folder:

```bash
# Python
python3 -m http.server 8000

# or Node
npx serve .
```

Then open <http://localhost:8000>.

## SEO + AI search (AEO/GEO) included

- Semantic HTML, descriptive `<title>` / meta description / keywords per page
- Open Graph + Twitter Card tags with a social cover image
- Rich JSON-LD `@graph`: `Organization`, `WebSite`+`SearchAction`, `SoftwareApplication`,
  `HowTo`, `FAQPage`, `BreadcrumbList`, and a `DefinedTermSet` glossary
- Definitional, quotable, Q&A-style content that AI answer engines extract and cite
- `llms.txt` AI-crawler summary; `robots.txt` explicitly welcomes GPTBot, PerplexityBot,
  ClaudeBot, Google-Extended, CCBot, etc.
- `robots.txt`, `sitemap.xml`, canonical URLs, theme color, PWA manifest
- Accessible: skip link, ARIA labels, reduced-motion support, keyboard-friendly

## Security

- Strict **Content-Security-Policy** (allowlist `self` + Google Fonts only) plus
  `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `Strict-Transport-Security`, and COOP/CORP — set via `_headers` and `netlify.toml`,
  with a CSP `<meta>` fallback for hosts that can't send headers (e.g. GitHub Pages)
- No inline event handlers, no `eval`/`innerHTML`/`document.write` — JS only writes via
  `textContent` / CSSOM, so there are no XSS sinks
- No third-party scripts or trackers; only Google Fonts is loaded cross-origin
- `interest-cohort=()` opts out of FLoC; `referrer` policy limits leakage

## Notes / next steps

- **Domain:** update the hard-coded `https://kudbeequant.com/` URLs (meta tags, sitemap,
  robots) if you launch on a different domain.
- **Waitlist:** the form currently validates and stores emails in `localStorage` only —
  wire `assets/js/main.js` (`waitlistForm` handler) to your email provider (Mailchimp,
  ConvertKit, Formspree, etc.) when you're ready to collect real signups.
- All product stats/testimonials are illustrative placeholders — swap in real numbers
  before a public launch.
