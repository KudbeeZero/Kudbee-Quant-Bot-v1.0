# Vendored motion libraries (served same-origin)

The site CSP is `script-src 'self'` — no third-party script hosts. These libraries
are therefore committed and served from our own origin (no CDN at runtime).

| File | Library | Version | License |
|------|---------|---------|---------|
| `gsap.min.js` | GSAP | 3.12.5 | Standard "no charge" license (free, incl. ScrollTrigger) — https://gsap.com/community/standard-license/ |
| `ScrollTrigger.min.js` | GSAP ScrollTrigger | 3.12.5 | as above |
| `lenis.min.js` | Lenis smooth-scroll | 1.1.18 | MIT — https://github.com/darkroomengineering/lenis |

Source: `https://cdn.jsdelivr.net/npm/<pkg>@<version>/dist/<file>` (fetched at build time).
To update: re-fetch the pinned version and update this table.
