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

> **Update (same day): host decision changed.** The owner is **not using Render**.
> Backend host is now **Fly.io** (`Dockerfile` + `fly.toml`; `render.yaml` retired).
> The gaps below stand; the fixes were re-pointed at Fly.

## 🔴 RED — real gaps found

### 1. The FastAPI engine is NOT deployed (owner-side)
`https://kudbee-quant-api.onrender.com/api/health` returned **404 /
`x-render-routing: no-server`** — nothing was ever deployed on Render, and the
owner is not using it. The API is real (`kudbee_quant/api.py`), it just has no
host yet. **Impact:** the compute-on-demand pages (Live Signals, Trade Flow, Lab)
have no backend. **Owner action:** deploy to **Fly.io** — `fly launch --no-deploy`,
`fly secrets set …`, `fly deploy` (full runbook: `docs/HOSTING.md`).

### 2. The `/api/*` proxy was Netlify-only — dead on Cloudflare Pages (FIXED in repo)
The site calls same-origin `/api/*` on purpose (keeps CSP `connect-src 'self'`).
That rewrite lived only in `netlify.toml`, which **Cloudflare Pages never reads**,
so `/api/*` on the live apex 404s at the static layer. **Fix:** added a Cloudflare
Pages Function `functions/api/[[path]].js` that proxies `/api/*` → the Fly app
same-origin (upstream overridable via the `API_ORIGIN` Pages env var). Carries
traffic the moment gap #1 is deployed. *Unverified until the next Pages deploy
picks up `functions/`.*

### 3. Raw `data/` was publicly downloadable — privacy leak (FIXED in repo)
`https://kudbeex.xyz/data/journal.json` (and `overnight_results.json`,
`heartbeat.json`, …) all returned **200** with the FULL raw contents — including
the exact **entry/stop/target** levels on open positions that `/api/journal`
deliberately strips (the stop-hunt / front-running vector). Cause: Cloudflare
Pages publishes the repo root (`publish = "."`), so `data/` shipped as static
files. **Fix:** added Pages Function `functions/data/[[path]].js` that 404s every
`/data/*` request at the edge. The site only ever calls `/api/*`, so nothing
legitimate breaks. *Unverified until the next Pages deploy; re-check with
`curl -o /dev/null -w '%{http_code}' https://kudbeex.xyz/data/journal.json` → 404.*

## 🟡 UNVERIFIABLE FROM HERE — needs an owner-side check

| Item | Why it can't be confirmed here |
|---|---|
| `https://www.kudbeex.xyz/` | The agent proxy returns **502 CONNECT (policy denial or upstream failure)** for the `www` host while the apex succeeds through the same proxy. Can't distinguish "proxy policy blocks www" from "www not added as a Pages custom domain." **Owner:** in Cloudflare Pages → Custom domains, confirm both `kudbeex.xyz` **and** `www` are added (part of X2). |
| Telegram webhook registration | Depends on the Render service being up + `KUDBEE_API_TOKEN`; register via `.github/workflows/telegram-register.yml` or `GET /api/telegram/register-webhook?token=…` once #1 is done. |
| Worker `TRIGGER_SECRET` | Owner-side secret (X3) — `wrangler secret put TRIGGER_SECRET`. Cron runs without it; only the manual trigger URL needs it. |

## Bottom line
The **marketing site is live and hardened**. The **application layer is not wired
end-to-end**: the API isn't deployed yet (owner-side, now targeting **Fly.io**),
the Pages→API proxy was missing (fixed in-repo → Fly), and the raw `data/` leak is
closed (fixed in-repo). Closing gap #1 (`fly deploy`, runbook `docs/HOSTING.md`) +
confirming `www` is what turns the dynamic pages on.
