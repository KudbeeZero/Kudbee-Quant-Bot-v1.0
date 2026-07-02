# Kudbee trade-bot cron (reliable external trigger)

**Why this exists:** GitHub Actions' built-in `schedule:` cron is best-effort — it
silently drops and delays a large fraction of scheduled runs. Observed on this repo:
only ~6 of 18 hourly runs fired, 15–40 min late, with multi-hour gaps. When a run is
dropped, **no Telegram message is sent** (trade-open, resolved, or summary). That's why
alerts only arrived reliably when you triggered the workflow manually.

**The fix:** Cloudflare **Cron Triggers** are reliable. This tiny Worker fires the
`paper-trade.yml` workflow every hour through GitHub's REST API
(`workflow_dispatch`), so the scan + its Telegram pings actually run.

> The repo also has an in-repo mitigation (a backup `:35` scheduled run + denser
> read-only reminders). This Worker is the belt-and-suspenders that makes it bulletproof.

## One-time setup (~5 minutes)

1. **Create a GitHub token** (fine-grained PAT):
   - GitHub → Settings → Developer settings → Fine-grained tokens → *Generate new token*.
   - **Repository access:** only `KudbeeZero/Kudbee-Quant-Bot-v1.0`.
   - **Permissions:** Repository → **Actions: Read and write** (nothing else needed).
   - Copy the token (starts with `github_pat_…`).

2. **Install wrangler and log in to Cloudflare** (you already have a Cloudflare account
   — the repo's Pages site lives there):
   ```bash
   npm install -g wrangler          # or use: npx wrangler ...
   wrangler login
   ```

3. **Add the token as a Worker secret** (kept out of the repo) and deploy:
   ```bash
   cd cloudflare/trade-bot-cron
   wrangler secret put GH_TOKEN     # paste the github_pat_… token when prompted
   wrangler deploy
   ```

   > ⚠️ **Windows / PowerShell gotcha:** type the token at the interactive prompt above,
   > or pipe it from **Git Bash** (`printf '%s' '<token>' | npx wrangler secret put GH_TOKEN`).
   > Do **NOT** pipe it from PowerShell (`$t | wrangler secret put …`) — PowerShell's
   > child-process stdin writer prepends a UTF-8 BOM to the value, so GitHub rejects it with
   > `401 Bad credentials` even though the token is valid. (Cost us a whole debug session.)

4. **(Optional) Failure alerts** — set two more secrets so a dispatch failure (e.g. the
   token expires → 401) pings Telegram instead of failing silently. Reuse the repo's bot:
   ```bash
   wrangler secret put TELEGRAM_BOT_TOKEN   # same bot as the repo's TELEGRAM_* secrets
   wrangler secret put TELEGRAM_CHAT_ID
   wrangler deploy
   ```
   Leave them unset and the Worker just stays silent on failure (no behavior change).

5. **(Required for the manual URL trigger) Set `TRIGGER_SECRET`** — the scheduled cron
   needs nothing extra, but the manual `fetch()` health-check URL is now auth-gated so a
   stranger who learns the `*.workers.dev` URL can't spam `workflow_dispatch`:
   ```bash
   wrangler secret put TRIGGER_SECRET   # any long random string
   wrangler deploy
   ```
   Then trigger a run with the secret in a header (preferred) or query param:
   ```bash
   curl -H "X-Trigger-Secret: <secret>" https://<worker-url>
   # or, for a browser: https://<worker-url>?key=<secret>
   ```
   **Fail-closed:** if `TRIGGER_SECRET` is unset the manual URL returns 403 (the cron still
   runs); with it set, a missing/wrong secret returns 403.

That's it. The Worker now fires the bot on Cloudflare's reliable cron, dispatching every
workflow in `WORKFLOW_FILES` (currently `paper-trade.yml` + the read-only `paper-status.yml`).

## Verify it works
- Hit the Worker's URL once with the `TRIGGER_SECRET` (`-H "X-Trigger-Secret: <secret>"`
  or `?key=<secret>`) — it triggers a run immediately and returns a generic `ok` (200) or
  `dispatch error` (500). Per-workflow detail stays in `wrangler tail`, not the HTTP body.
- In the repo, **Actions** tab → you'll see `paper-trade` (and `paper-status`) runs with
  event **workflow_dispatch** kicked off by the token. Telegram pings follow as usual.
- `wrangler tail` streams the Worker's logs if you want to watch the cron fire.
- **Smoke-test the failure alert** (after setting `TELEGRAM_*`): temporarily point it at a
  non-existent workflow — `wrangler deploy --var WORKFLOW_FILES:nope.yml`, hit the URL,
  confirm the Telegram alert fires, then `wrangler deploy` to restore.

## What it does and does NOT catch
- ✅ A **dispatch failure** (non-204 from GitHub: expired/invalid token → 401, missing
  Actions permission → 403) triggers a Telegram alert.
- ❌ The **Worker itself never firing** (Cloudflare outage, billing, a dead isolate) is
  still invisible here — there's no "alert me if you DON'T hear from the cron." A
  dead-man's-switch (e.g. healthchecks.io) is the stronger pattern, deliberately deferred.
  The in-repo run-heartbeat partially covers this from the workflow side.

## Tuning
- **More frequent:** add cron lines in `wrangler.toml`, e.g.
  `crons = ["5 * * * *", "35 * * * *"]`.
- **Which workflows fire:** edit `WORKFLOW_FILES` in `wrangler.toml` (comma-separated).
- The token is the only *required* secret; rotate it anytime with `wrangler secret put
  GH_TOKEN` (see the PowerShell BOM warning above). `TELEGRAM_*` are optional.
