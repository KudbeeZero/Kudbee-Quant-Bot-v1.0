# Runbook — Make the Telegram bot work (webhook + command menu)

A one-time setup so the Telegram bot **responds** to commands and shows a **command menu**.
Needs only a terminal, the three values below, and ~5 minutes. Run the steps in order.
Nothing here places real trades — the bot is paper-only.

> Code references (for maintainers): the webhook endpoint is `POST /api/telegram`
> (`kudbee_quant/api.py` — authenticates the `X-Telegram-Bot-Api-Secret-Token` header against
> the `TELEGRAM_WEBHOOK_SECRET` env var); the command handlers are in
> `kudbee_quant/telegram_commands.py` and are covered by `tests/test_telegram_commands.py`.
>
> **Host note (2026-07-05):** the backend runs on **Fly.io** (Render retired 2026-07-02,
> MEMORY §80). This runbook assumes the API is already deployed per `docs/HOSTING.md`
> (CROSSROADS X2 step 3). App secrets are set with `fly secrets set NAME=value`.

---

## 0. You need three values (ask the owner if you don't have them)

| Value | What it is | Where to find it |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token, looks like `123456789:AA...` | BotFather, or the Fly secret `TELEGRAM_BOT_TOKEN` (`fly secrets list`) |
| `WEBHOOK_SECRET` | shared secret — **MUST exactly equal** the Fly secret `TELEGRAM_WEBHOOK_SECRET` | `fly secrets list` (set with `fly secrets set`) |
| `API_URL` | the public app URL, no trailing slash, e.g. `https://kudbee-quant-api.fly.dev` | Fly dashboard / `fly status` |

> ⚠️ The **#1 failure** is `WEBHOOK_SECRET` not matching the app's `TELEGRAM_WEBHOOK_SECRET` byte-for-byte.

---

## 1. Set them as shell variables (do NOT commit/paste these anywhere public)

```bash
export BOT_TOKEN='PASTE_BOT_TOKEN'
export WEBHOOK_SECRET='PASTE_TELEGRAM_WEBHOOK_SECRET'   # must match the Fly secret
export API_URL='https://kudbee-quant-api.fly.dev'       # no trailing slash
```

---

## 2. Register the webhook (makes the bot RECEIVE commands)

```bash
curl -s -X POST \
  "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${API_URL}/api/telegram" \
  -d "secret_token=${WEBHOOK_SECRET}"
```

Expected: `{"ok":true,"result":true,"description":"Webhook was set"}`

---

## 3. Verify the webhook

```bash
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

Expected: `"url"` shows `https://<your-app>.fly.dev/api/telegram`, `"pending_update_count"` is a number,
and there is **no** `"last_error_message"`. **Copy this entire JSON and send it back to the owner.**

---

## 4. Register the slash-command MENU (the blue popup when you type "/")

```bash
curl -s -X POST \
  "https://api.telegram.org/bot${BOT_TOKEN}/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "status",    "description": "Open positions + unrealized R"},
      {"command": "score",     "description": "Today’s closed trades"},
      {"command": "positions", "description": "Full open book"},
      {"command": "scan",      "description": "Trigger a fresh scan now"},
      {"command": "summary",   "description": "Force the hourly summary now"},
      {"command": "levels",    "description": "TR level grid — usage: /levels SYMBOL"},
      {"command": "history",   "description": "Daily open + Asia H/L, 7d — usage: /history SYMBOL"},
      {"command": "vectors",   "description": "Unrecovered climax magnets — usage: /vectors SYMBOL"},
      {"command": "trade",     "description": "Log a paper trade — /trade SYMBOL LONG|SHORT PRICE"},
      {"command": "yes",       "description": "Confirm the pending trade"},
      {"command": "cancel",    "description": "Cancel the pending trade"},
      {"command": "help",      "description": "Show the command menu"}
    ]
  }'
```

Expected: `{"ok":true,"result":true}`  ·  Verify with: `curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMyCommands"`

> The menu is just autocomplete. The bot replying still depends on the webhook (Steps 2–3).

---

## 5. Live walk-through (from the Telegram app, messaging the bot)

Send each, record the reply:

| Send | Expected |
|---|---|
| `/help` | the command menu (within ~10s) |
| `/status` | open positions + unrealized R |
| `/score` | today's closed trades |
| `/positions` | full open book |
| `/scan` | "✅ Scan triggered" (+ cooldown notice) |
| `/scan` (again immediately) | rate-limit message (5-min cooldown) |
| `/trade` (no args) | usage message |
| `/trade SOLUSDT LONG 72.87` | confirmation prompt (expires in 60s) |
| `/cancel` | "🚫 Trade cancelled" |
| `/trade SOLUSDT LONG 72.87` then `/yes` | "✅ Paper trade logged" |
| `/help` | still works (stateless) |

> `/levels`, `/history`, `/vectors` need **Cloudflare D1 provisioned** (Step 6). Until then they reply
> with a friendly "not configured" message — that's expected, not a bug.

---

## 6. (Later, owner-side) Provision Cloudflare D1 — lights up /levels /history /vectors

```bash
wrangler d1 create kudbee-tr-levels
# apply the migration in the repo: cloudflare/trade-bot-cron/migrations/0001_tr_levels.sql
```
Then paste the printed `database_id` into `wrangler.toml` **and** set `D1_DATABASE_ID`,
`CF_ACCOUNT_ID` + `CF_API_TOKEN` as Fly secrets (`fly secrets set …`). Run a paper-scan,
then re-test `/levels SOLUSDT`.

---

## Troubleshooting (if `/help` doesn't reply in ~10s)

1. Re-run `getWebhookInfo` (Step 3). If `last_error_message` mentions **403 / Forbidden / Wrong response**
   → the secret doesn't match. Make `WEBHOOK_SECRET` == the Fly secret `TELEGRAM_WEBHOOK_SECRET`, redo Step 2.
2. Check **Fly logs** (`fly logs -a kudbee-quant-api`) for an incoming `POST /api/telegram`:
   - `403` in logs → secret mismatch (see #1)
   - no line at all → wrong `API_URL`, or app not deployed (open `API_URL` in a browser first)
   - `200` but no reply → confirm `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` are set as Fly secrets and you're
     messaging from the **whitelisted** chat id
3. `"url"` empty in `getWebhookInfo` → `setWebhook` didn't take; re-run Step 2 and read its JSON for the reason.

---

## Report back to the owner

- The full `getWebhookInfo` JSON (Step 3)
- `setMyCommands` result (Step 4)
- Which of the Step-5 commands replied (yes/no + reply text or screenshot)
- Any `last_error_message` or Fly-log error you hit
