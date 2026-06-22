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

That's it. The Worker now fires the bot hourly on Cloudflare's reliable cron.

## Verify it works
- Hit the Worker's URL once (shown after `wrangler deploy`) — it triggers a run
  immediately and returns `OK: dispatched paper-trade.yml@main`.
- In the repo, **Actions** tab → you'll see a `paper-trade` run with event
  **workflow_dispatch** kicked off by the token. Telegram pings follow as usual.
- `wrangler tail` streams the Worker's logs if you want to watch the cron fire.

## Tuning
- **More frequent:** add cron lines in `wrangler.toml`, e.g.
  `crons = ["5 * * * *", "35 * * * *"]`.
- **Also fire the read-only status pings:** duplicate this Worker (or add logic) to
  dispatch `paper-status.yml` too.
- The token is the only secret; rotate it anytime with `wrangler secret put GH_TOKEN`.
