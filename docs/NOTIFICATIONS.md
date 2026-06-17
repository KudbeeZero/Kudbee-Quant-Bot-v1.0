# Telegram notifications

Get a ping when the bot logs a new setup or a trade resolves, plus an hourly
portfolio summary — delivered to Telegram by the existing hourly paper-trade
Action. The whole layer is **opt-in and side-effect-safe**: with no secrets set
it is a silent no-op, and a failed send can never crash a scan
(`kudbee_quant/notifications/`).

## What you get

| Event | Fires from | Message |
| --- | --- | --- |
| **New setups logged** | `paper-scan`, `ingest-alerts` | one batched message listing the new brackets (paper entries start as *pending limits*) |
| **Trades resolved** | `journal-check` | one batched message — ✅ target / ❌ stop / ⚪ cancelled, with realized R |
| **Hourly summary** | `notify-summary` (added to the Action) | open count, unrealized R/USD, up/down, open risk, closest-to-stop/target, warnings, net record |
| **Run failure** | the Action's `if: failure()` step | 🚨 ping if checkout/deps/commit hard-fail |

Cadence is **hourly**, riding the existing `paper-trade.yml` Action (runs at
:05). Trade-open / resolved pings are effectively real-time *for this bot* —
they fire the moment the hourly scan creates or closes a trade.

## One-time setup (~3 minutes)

1. **Create a bot.** In Telegram, message [@BotFather](https://t.me/BotFather),
   send `/newbot`, follow the prompts. He gives you a **bot token** like
   `123456789:AAExampleTokenString`.
2. **Get your chat id.** Send any message to your new bot, then message
   [@userinfobot](https://t.me/userinfobot) (or open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read
   `chat.id`). For a group, add the bot to the group and use the group's id.
3. **Add the two GitHub repo secrets** (so the hourly Action can send): repo →
   *Settings → Secrets and variables → Actions → New repository secret*:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. **Done.** The next hourly run (or a manual *Run workflow*) will start pinging.

## Test it locally

```bash
export TELEGRAM_BOT_TOKEN=123456789:AA...
export TELEGRAM_CHAT_ID=987654321
python -m kudbee_quant.cli notify-test      # sends "✅ ... wired up"
python -m kudbee_quant.cli notify-summary   # sends the portfolio snapshot
```

## Config (env vars)

| Var | Required | Meaning |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | yes | numeric chat id to deliver to |
| `KUDBEE_TELEGRAM_ENABLED` | no | kill-switch; set to `0`/`false`/`no`/`off` to mute even with creds present |

Secrets are read at use time via the masked `get_secret` helper — never logged,
never committed. Without both creds set, `telegram_enabled()` is `False` and
every `notify_*` call returns immediately.
