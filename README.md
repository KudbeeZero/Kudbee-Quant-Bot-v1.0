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
├── 404.html              # Branded not-found page
├── robots.txt            # Crawler directives
├── sitemap.xml           # Sitemap for search engines
├── site.webmanifest      # PWA / icon metadata
└── assets/
    ├── css/style.css     # Design system + page styles
    ├── js/main.js        # Animations, counters, charts, waitlist form
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

## SEO included

- Semantic HTML, descriptive `<title>` / meta description / keywords
- Open Graph + Twitter Card tags with a social cover image
- JSON-LD structured data (`SoftwareApplication` + `FAQPage`)
- `robots.txt`, `sitemap.xml`, canonical URL, theme color, PWA manifest
- Accessible: skip link, ARIA labels, reduced-motion support, keyboard-friendly

## Notes / next steps

- **Domain:** update the hard-coded `https://kudbeequant.com/` URLs (meta tags, sitemap,
  robots) if you launch on a different domain.
- **Waitlist:** the form currently validates and stores emails in `localStorage` only —
  wire `assets/js/main.js` (`waitlistForm` handler) to your email provider (Mailchimp,
  ConvertKit, Formspree, etc.) when you're ready to collect real signups.
- All product stats/testimonials are illustrative placeholders — swap in real numbers
  before a public launch.
