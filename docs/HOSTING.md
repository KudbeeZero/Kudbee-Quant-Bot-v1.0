# HOSTING — Render runbook (dashboard + TradingView webhook)

Provider decision (user-confirmed 2026-06-12): **Render, Starter plan
($7/mo)** — always-on (free tier's 15-min spin-down + 30-60s cold start would
drop TradingView webhook POSTs), native Python (no Docker), auto-deploy on
push, free TLS. Blueprint: `render.yaml` at the repo root.

## How the data flows once hosted

- **Dashboard freshness:** the app reads `data/journal.json` from its own
  checkout. Render auto-deploys on every push, and the bot pushes the journal
  hourly — so the dashboard refreshes on the bot's cadence. The host is a
  *mirror*, never the journal of record.
- **TV alerts → scored record:** the host's checkout is ephemeral, so
  `/api/alert` ALSO commits each alert to `data/alert_inbox/<id>.json` in the
  repo (create-only paths — cannot race the bot). The hourly Action runs
  `python -m kudbee_quant.cli ingest-alerts` before its scan, logging the
  alert into the real journal with `source="human"` and consuming the file.
  Your chart reads then score against the bot's in `by_source`. Full design:
  `kudbee_quant/alert_inbox.py`.
- If the response from `/api/alert` says `"inbox": false`, the repo commit
  didn't happen (no `KUDBEE_GH_TOKEN` configured, or GitHub was unreachable)
  — the alert shows on the dashboard but will be lost on the next redeploy
  and never scored.

## One-time setup (user, ~10 minutes)

1. **Create the service:** Render dashboard → New → Blueprint → connect
   `KudbeeZero/Kudbee-Quant-Bot-v1.0` → it picks up `render.yaml`
   (service `kudbee-quant-api`, Starter). If Render reports the name is
   taken, accept its suggestion and update the host in `netlify.toml`.
2. **Set the secret env vars** (blueprint marks them `sync: false`):
   - `KUDBEE_API_TOKEN` — generate a long random string
     (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
   - `KUDBEE_SITE_ORIGIN` — the Netlify site origin (scopes CORS).
   - `KUDBEE_GH_TOKEN` — GitHub → Settings → Developer settings →
     Fine-grained tokens → **only this repo**, Repository permissions →
     **Contents: Read and write**, nothing else. This is the only credential
     with write reach into the repo; keep its scope that narrow.
   - `KUDBEE_DASHBOARD_PASSWORD` — the shared password that unlocks the
     admin/investor dashboard at `/dashboard` (and the curated runner). Pick
     anything memorable for now (a passphrase / the business name is fine).
     **Unset ⇒ login disabled, dashboard locked** (fail-closed).
   - `KUDBEE_SESSION_SECRET` — long random value signing the session cookie
     (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). Optional
     (derived from the password if unset) but recommended; rotating it signs
     everyone out.
3. **Smoke-test** (after first deploy goes live):
   ```bash
   curl https://kudbee-quant-api.onrender.com/api/health
   curl -s -X POST "https://kudbee-quant-api.onrender.com/api/alert" \
     -H 'Content-Type: application/json' \
     -d '{"symbol":"BTCUSDT","direction":1,"entry":100000,"stop":98000,
          "target":106000,"tf":"1h","note":"smoke","token":"<KUDBEE_API_TOKEN>"}'
   ```
   Expect `"logged": true, "inbox": true`, a `data/alert_inbox/*.json` commit
   in the repo, and the entry ingested (then resolved/cancelled normally) by
   the next hourly run. Open `https://kudbee-quant-api.onrender.com/` — the
   dashboard should render live journal data.
4. **Netlify:** redeploy the site so the `/api/*` proxy in `netlify.toml`
   takes effect — the Live Signals page then calls the API same-origin.

## TradingView alert setup (paid TV plan required for webhooks)

- Webhook URL: `https://kudbee-quant-api.onrender.com/api/alert`
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
- **Three CSP sources of truth** now: `netlify.toml` + `_headers` (the static
  marketing host) and a FastAPI response header in `api.py` (this Render host,
  which serves the dashboard/login). Keep them in mind together; the FastAPI one
  is strict (`script-src 'self'`, no inline) — that's why the dashboard JS lives
  in `kudbee_quant/static/app.js`, not inline.

## Styling build (Tailwind, compiled + committed)

- Dashboard/login + marketing pages use compiled Tailwind. Edit
  `assets/css/tailwind.css` / `tailwind.config.js`, then `npm run build` — this
  writes `assets/css/app.css` AND copies it to `kudbee_quant/static/app.css`.
  **Both compiled files are committed** so neither Netlify (`command=""`) nor the
  Render `pip install` build needs Node. Re-run after changing any class usage.

## Security posture (unchanged by hosting)

- Writes fail closed: no `KUDBEE_API_TOKEN` on the host → 503 on
  `/api/alert` and `/api/paper/scan`; wrong token → 401 (constant-time
  compare in all three token paths).
- Dashboard login is fail-closed the same way (no password → 503/locked,
  wrong password → 401, constant-time compare), and brute-force-limited (5/min).
- Reads are public by design (Live Signals), rate-limited 120/min;
  writes 10/min; login 5/min; runner 6/min.
- Known disclosures (accepted, from the PR #9 audit): `/api/metrics` exposes
  host CPU/mem/disk publicly (it's the dashboard's host panel; the host is a
  disposable mirror with no secrets in the journal); `?token=` is supported
  for TV compatibility but body-token is the documented path.
