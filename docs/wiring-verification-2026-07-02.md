# Live wiring verification — 2026-07-02

> Owner asked to "verify the wiring." This is the honest checklist: what's green,
> what's red, and what can't be verified from the agent container. Probed with
> `curl` against the live hostnames. No secrets, no guesses — where a thing can't
> be confirmed from here it says so.

## ✅ GREEN — confirmed live

| Endpoint | Result |
|---|---|
| `https://kudbeex.xyz/` | **200**, `server: cloudflare`, The Journal redesign served |
| Security headers on apex | CSP (`connect-src 'self'`), HSTS `max-age=63072000; preload`, `x-frame-options: DENY`, `x-content-type-options: nosniff`, COOP/CORP, Permissions-Policy — all present |
| `https://kudbeex.xyz/sitemap.xml` | 200 |
| `https://kudbeex.xyz/robots.txt` | 200 |
| `https://kudbeex.xyz/llms.txt` | 200 |
| Mobile hero (390/375/320px) | fixed 2026-07-02 (commit `30c3a0f`) — beta pill clears the nav (19px), verified via Playwright |

## 🔴 RED — real gaps found

### 1. The FastAPI engine is NOT deployed on Render
`https://kudbee-quant-api.onrender.com/api/health` (and `/`, `/api/journal`) all
return **404** with header `x-render-routing: no-server` — Cloudflare (fronting
Render) reports **no service** behind that hostname. The API defines `/api/health`
and `/` in code (`kudbee_quant/api.py:98,693`), so this is a deploy gap, not a
routing bug: the service was never created / is suspended on Render.
**Impact:** every dynamic page (Live Signals, Trade Flow, Lab) has no backend to
call. **Owner action:** create/redeploy the `kudbee-quant-api` service on Render
(`render.yaml`, runbook `docs/HOSTING.md`), set its env (`KUDBEE_API_TOKEN`, etc.).

### 2. The `/api/*` proxy was Netlify-only — dead on Cloudflare Pages (FIXED in repo)
The site calls same-origin `/api/*` on purpose (keeps CSP `connect-src 'self'`).
That rewrite lived only in `netlify.toml`, which **Cloudflare Pages never reads**,
so `/api/*` on the live apex 404s at the static layer even before reaching Render.
**Fix (this commit):** added a Cloudflare Pages Function
`functions/api/[[path]].js` that proxies `/api/*` → Render same-origin (upstream
overridable via the `API_ORIGIN` Pages env var). This carries traffic the moment
gap #1 is closed. *Unverified until the next Pages deploy picks up `functions/`.*

## 🟡 UNVERIFIABLE FROM HERE — needs an owner-side check

| Item | Why it can't be confirmed here |
|---|---|
| `https://www.kudbeex.xyz/` | The agent proxy returns **502 CONNECT (policy denial or upstream failure)** for the `www` host while the apex succeeds through the same proxy. Can't distinguish "proxy policy blocks www" from "www not added as a Pages custom domain." **Owner:** in Cloudflare Pages → Custom domains, confirm both `kudbeex.xyz` **and** `www` are added (part of X2). |
| Telegram webhook registration | Depends on the Render service being up + `KUDBEE_API_TOKEN`; register via `.github/workflows/telegram-register.yml` or `GET /api/telegram/register-webhook?token=…` once #1 is done. |
| Worker `TRIGGER_SECRET` | Owner-side secret (X3) — `wrangler secret put TRIGGER_SECRET`. Cron runs without it; only the manual trigger URL needs it. |

## Bottom line
The **marketing site is live and hardened**. The **application layer is not wired
end-to-end**: the API isn't deployed (owner-side), and the Pages→API proxy was
missing (fixed here in-repo). Closing gap #1 (Render deploy) + confirming `www` is
what turns the dynamic pages on.
