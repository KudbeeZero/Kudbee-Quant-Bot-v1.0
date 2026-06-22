# Reliable trigger — stop GitHub from dropping ~70% of runs

**The problem (see MEMORY §61):** GitHub Actions' built-in `schedule:` cron is
best-effort and silently skips a large fraction of scheduled runs. A dropped run =
no scan = no Telegram. It's a *trigger* problem, not storage — no database fixes it.

**The fix:** have a *reliable* external scheduler poke the bot every X minutes through
GitHub's API. This repo's workflows already expose `workflow_dispatch`, so an external
cron can fire them directly. Two equivalent options:

- **Option A — cron-job.org** (this doc): a free website, no CLI, ~5 min. **Recommended.**
- **Option B — Cloudflare Worker** (`cloudflare/trade-bot-cron/README.md`): same effect,
  needs `wrangler`/Node. Use this if you'd rather host it on Cloudflare.

You only need **one** of them. Both call the same GitHub endpoint below.

In-repo mitigations are already live regardless: 4 scheduled attempts/hour and a
**run heartbeat** that reports coverage in your Telegram summary
(`⏱ Runs: last 8m ago • 22/24h covered`, or a `⚠️ Scheduler gap … X% dropped` warning).
An external trigger is what drives that coverage line to `24/24h`.

---

## Option A — cron-job.org (recommended, ~5 minutes)

### Step 1 — make a GitHub token (one time)
1. GitHub → **Settings** → **Developer settings** → **Fine-grained tokens** → **Generate new token**.
2. **Token name:** `kudbee-cron`  •  **Expiration:** 1 year (set a reminder to rotate).
3. **Repository access** → *Only select repositories* → **`KudbeeZero/Kudbee-Quant-Bot-v1.0`**.
4. **Permissions** → **Repository permissions** → **Actions** → **Read and write**. (Nothing else.)
5. **Generate token** and copy it (starts with `github_pat_…`). You won't see it again.

### Step 2 — create the cron job
1. Sign up free at **https://cron-job.org** → **Create cronjob**.
2. **Title:** `Kudbee paper-trade`
3. **URL:**
   ```
   https://api.github.com/repos/KudbeeZero/Kudbee-Quant-Bot-v1.0/actions/workflows/paper-trade.yml/dispatches
   ```
4. **Schedule:** every 15 minutes (or every hour — your call). Every 15 min matches the
   in-repo cadence and the per-(symbol,timeframe,book) dedup means re-runs never double-open.
5. Open **Advanced** (or "Headers / Request method"):
   - **Request method:** `POST`
   - **Request headers** (add three):
     | Header | Value |
     |---|---|
     | `Authorization` | `Bearer github_pat_…`  ← paste your token after `Bearer ` |
     | `Accept` | `application/vnd.github+json` |
     | `X-GitHub-Api-Version` | `2022-11-28` |
   - **Request body:**
     ```json
     {"ref":"main"}
     ```
6. **Save**, make sure the job is **Enabled**.

### Step 3 — verify it works
- In cron-job.org, hit **Run now** (or **Test run**). A success is **HTTP 204** (GitHub
  returns 204 No Content on a successful dispatch — that's expected, not an error).
- In the repo → **Actions** tab you'll see a `Forward paper-trade` run with event
  **workflow_dispatch**. Telegram pings follow as usual.
- Next hourly summary should show the heartbeat line trending toward `24/24h covered`.

### Optional — also fire the every-5-min status ping
The read-only open-position reminder (`paper-status.yml`) has its own dense schedule;
you generally don't need an external trigger for it. If you want belt-and-suspenders,
duplicate the cron job with this URL (same headers + body):
```
https://api.github.com/repos/KudbeeZero/Kudbee-Quant-Bot-v1.0/actions/workflows/paper-status.yml/dispatches
```

---

## Quick test from your own machine (optional)
If you have a terminal, you can confirm the token + endpoint before wiring cron-job.org.
A successful dispatch returns **HTTP 204** and silently starts a run:

```bash
curl -i -X POST \
  -H "Authorization: Bearer github_pat_…" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/KudbeeZero/Kudbee-Quant-Bot-v1.0/actions/workflows/paper-trade.yml/dispatches \
  -d '{"ref":"main"}'
```

- `HTTP/2 204` → success (check the Actions tab).
- `401` → bad/expired token. `403` → token missing **Actions: read & write**.
  `404` → wrong repo/workflow filename or the token can't see the repo.

## Notes
- The token is the only secret — keep it in cron-job.org, never commit it.
- Rotate it anytime: regenerate in GitHub, paste the new value into the cron job's
  `Authorization` header.
- This does **not** replace the in-repo cron; it runs alongside it. The dedup makes
  overlapping runs safe (no duplicate trades), and the heartbeat will show the
  improved coverage.
