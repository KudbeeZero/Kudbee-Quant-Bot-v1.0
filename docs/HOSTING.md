# HOSTING — Fly.io runbook (dashboard + TradingView webhook)

Provider decision (owner-confirmed 2026-07-02): **Fly.io** (Render retired). The
FastAPI engine ships as a container (`Dockerfile` + `fly.toml` at the repo root)
with one always-on machine — the free-tier spin-down elsewhere would drop
TradingView webhook POSTs, so `min_machines_running = 1` / `auto_stop_machines
= false` is the floor. The public site (Cloudflare Pages) calls the API
same-origin through the Pages Function `functions/api/[[path]].js`, which proxies
`/api/*` → the Fly app (override the upstream with the `API_ORIGIN` Pages env var
if your app name differs from `kudbee-quant-api.fly.dev`).

## How the data flows once hosted

- **Compute endpoints are always fresh:** `/api/signal`, `/api/trace`,
  `/api/sandbox/trace` fetch live market data and compute on demand — they need
  no journal file and are current regardless of deploy cadence.
- **Dashboard/Lab journal freshness:** the app reads `data/journal.json` baked
  into the image, so it is only as fresh as the last deploy. The
  **`.github/workflows/fly-deploy.yml`** workflow redeploys hourly (rolling,
  near-zero-downtime, so the always-on webhook survives) to keep it current. It
  is a **no-op until you set the `FLY_API_TOKEN` repo secret**. The host is a
  *mirror*, never the journal of record (that's the repo).
- **Raw `data/` is NOT public:** the Pages Function `functions/data/[[path]].js`
  404s every `/data/*` request at the edge, so the raw journal (with the exact
  entry/stop/target levels `/api/journal` deliberately strips) is never served
  from the marketing domain. The API is the only public read path.
- **TV alerts → scored record:** the host's checkout is ephemeral, so
  `/api/alert` ALSO commits each alert to `data/alert_inbox/<id>.json` in the
  repo (create-only paths — cannot race the bot). The hourly Action runs
  `python -m kudbee_quant.cli ingest-alerts` before its scan, logging the alert
  into the real journal with `source="human"` and consuming the file. If the
  `/api/alert` response says `"inbox": false`, no `KUDBEE_GH_TOKEN` was
  configured (or GitHub was unreachable) — the alert shows on the dashboard but
  is lost on the next redeploy and never scored. Full design:
  `kudbee_quant/alert_inbox.py`.

## One-time setup (owner, ~15 minutes, needs a machine with `flyctl`)

1. **Install + auth:** `curl -L https://fly.io/install.sh | sh`, then
   `fly auth login`.
2. **Create the app** (does not deploy yet):
   ```bash
   fly launch --no-deploy --copy-config --name kudbee-quant-api
   ```
   Accept the config in `fly.toml`. If the name is taken, pick another and set
   the `API_ORIGIN` Pages env var to `https://<your-app>.fly.dev`.
3. **Set the secrets** (these were Render env vars; on Fly they are secrets):
   ```bash
   fly secrets set \
     KUDBEE_API_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')" \
     KUDBEE_DASHBOARD_PASSWORD="<a memorable passphrase>" \
     KUDBEE_SESSION_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')" \
     KUDBEE_SITE_ORIGIN="https://kudbeex.xyz" \
     KUDBEE_GH_TOKEN="<fine-grained PAT, THIS repo, Contents R/W only>" \
     KUDBEE_GH_REPO="KudbeeZero/Kudbee-Quant-Bot-v1.0"
   ```
   Optional (leave unset to disable that feature — all fail-closed):
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`;
   `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `D1_DATABASE_ID` (TR Level Intelligence).
   - `KUDBEE_GH_TOKEN` is the only credential with write reach into the repo —
     GitHub → Settings → Developer settings → Fine-grained tokens → **only this
     repo**, Repository permissions → **Contents: Read and write**, nothing else.
   - `KUDBEE_DASHBOARD_PASSWORD` unset ⇒ login disabled, `/dashboard` locked.
4. **Deploy:** `fly deploy`. Then smoke-test:
   ```bash
   curl https://kudbee-quant-api.fly.dev/api/health
   curl -s -X POST "https://kudbee-quant-api.fly.dev/api/alert" \
     -H 'Content-Type: application/json' \
     -d '{"symbol":"BTCUSDT","direction":1,"entry":100000,"stop":98000,
          "target":106000,"tf":"1h","note":"smoke","token":"<KUDBEE_API_TOKEN>"}'
   ```
   Expect `"logged": true, "inbox": true`, a `data/alert_inbox/*.json` commit in
   the repo, and the entry ingested by the next hourly run. `GET /` (with the
   dashboard password) should render live journal data.
5. **Turn on auto-deploy freshness (optional):** `fly tokens create deploy`,
   then add the value as the repo secret `FLY_API_TOKEN` (GitHub → Settings →
   Secrets → Actions). `fly-deploy.yml` then redeploys on every code push + hourly.
6. **Cloudflare Pages:** the `/api/*` proxy is already in-repo
   (`functions/api/[[path]].js`). Set `API_ORIGIN` in Pages → Settings →
   Environment variables only if your Fly app name differs from the default.

## TradingView alert setup (paid TV plan required for webhooks)

- Webhook URL: `https://kudbee-quant-api.fly.dev/api/alert`
- Alert message (the token rides in the BODY — TV can't send headers; avoid
  `?token=` which can land in access logs):
  ```json
  {"symbol": "{{ticker}}", "direction": 1, "entry": {{close}},
   "stop": 0.0, "target": 0.0, "tf": "1h", "note": "pvsra chart read",
   "token": "<KUDBEE_API_TOKEN>"}
  ```
  Set `direction` (+1 long / −1 short; 0 is rejected), real `stop`/`target`
  prices, and optionally `conf` (0-1). Duplicate alerts on a symbol+timeframe
  that already has an open/pending bracket are ignored (`"logged": false`).

## Admin / investor dashboard (gated)

- `/` and `/dashboard` require a session: no cookie → 302 to `/login`. Sign in
  with `KUDBEE_DASHBOARD_PASSWORD`; the server sets a signed, HttpOnly, Secure,
  SameSite=Lax cookie (`kudbee_session`, 12h). Code: `kudbee_quant/api_auth.py`.
- The dashboard aggregates the full record (scorecard, open positions, closed-
  trade analytics + equity curve, portfolio risk, live signals, research/overnight
  findings) and a **curated test runner** (`kudbee_quant/api_runner.py`):
  whitelisted engine actions (signal / backtest / validate / sweep / bracket-sweep
  / paper-scan-DRY-RUN) with bounded params, run as async in-memory jobs. It is
  **not** a code executor and **never writes the journal** (paper-scan is dry-run).
- Gated read endpoints (session required): `/api/open-trades`, `/api/trade-history`,
  `/api/research`, and `/api/run*`. The public marketing reads (`/api/signal`,
  `/api/trace`, `/api/journal`, `/api/metrics`, …) are unchanged.
- **CSP sources of truth:** `_headers` (the Cloudflare Pages marketing host) and a
  FastAPI response header in `api.py` (the Fly host, which serves the dashboard/
  login). The FastAPI one is strict (`script-src 'self'`, no inline) — that's why
  the dashboard JS lives in `kudbee_quant/static/app.js`, not inline. (`netlify.toml`
  is kept only as a fallback for a Netlify deploy; Cloudflare Pages ignores it.)

## Styling build (Tailwind, compiled + committed)

- Dashboard/login + marketing pages use compiled Tailwind. Edit
  `assets/css/tailwind.css` / `tailwind.config.js`, then `npm run build` — this
  writes `assets/css/app.css` AND copies it to `kudbee_quant/static/app.css`.
  **Both compiled files are committed** so neither Cloudflare Pages (no build) nor
  the Fly image (`pip install` only, no Node) needs Node. Re-run after changing
  any class usage.

## Security posture (unchanged by hosting)

- Writes fail closed: no `KUDBEE_API_TOKEN` on the host → 503 on `/api/alert`
  and `/api/paper/scan`; wrong token → 401 (constant-time compare in all three
  token paths).
- Dashboard login is fail-closed the same way (no password → 503/locked, wrong
  password → 401, constant-time compare), and brute-force-limited (5/min).
- Reads are public by design (Live Signals), rate-limited 120/min; writes
  10/min; login 5/min; runner 6/min.
- Known disclosures (accepted, from the PR #9 audit): `/api/metrics` exposes host
  CPU/mem/disk publicly (it's the dashboard's host panel; the host is a disposable
  mirror with no secrets in the journal); `?token=` is supported for TV
  compatibility but body-token is the documented path.
