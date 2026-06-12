# DEPLOY — hosting the Kudbee API on Fly.io

The dashboard (`GET /`) and the TradingView webhook (`POST /api/alert`) need
the FastAPI app reachable on the public internet over HTTPS. Provider chosen
2026-06-12 (user decision): **Fly.io** — cheapest always-on managed option
(~$3–4/mo: shared-cpu-1x 512MB + 1GB volume), automatic HTTPS, no server to
maintain. Always-on is non-negotiable: TradingView gives a webhook receiver
**~3 seconds to respond** (cold starts = dropped alerts) and only allows
ports 80/443.

## Architecture (who owns the journal)

The repo stays the **single source of truth** for `data/journal.json`, and the
hourly paper-trade Action stays its owner (it is the only thing that RESOLVES
trades). The host is a second, append-only writer:

- App **code** runs from the Docker image (pip-installed package).
- Journal **state** lives in a repo clone on the persistent volume
  (`/data/repo`); `KUDBEE_JOURNAL_PATH` points the app there.
- `deploy/journal_sync.py` reconciles every 60s: fetch → capture local journal
  → `reset --hard origin/main` → union-merge (**origin wins per id; host
  contributes new ids only** — i.e. TV alerts) → commit + push
  (`tv-alert: sync … [skip ci]`). No rebases, no merge conflicts by
  construction; a lost push race self-heals on the next tick
  (tests: `tests/test_journal_sync.py`).
- The Action's push now rebase-retries up to 3× in case the host pushed an
  alert mid-run (`.github/workflows/paper-trade.yml`).
- Known small gap (documented, accepted): the journal file has no
  cross-process lock, so an `/api/alert` write landing in the few ms between
  the sync's read and reset can be lost. A torn (mid-write) read skips the
  tick rather than wiping the file.

## One-time setup (user console steps)

1. Install flyctl and sign up/in:
   `curl -L https://fly.io/install.sh | sh`, then `fly auth signup` (or `login`).
2. Create the app + volume (names must match `fly.toml`):

   ```sh
   fly apps create kudbee-quant
   fly volumes create kudbee_data --app kudbee-quant --region iad --size 1
   ```

3. Create a **fine-grained GitHub PAT** scoped to ONLY this repo with
   **Contents: Read and write** (Settings → Developer settings → Fine-grained
   tokens). This is what lets the host pull bot updates and push TV alerts.
4. Set secrets (never in `fly.toml`):

   ```sh
   fly secrets set --app kudbee-quant \
     KUDBEE_GIT_TOKEN=<fine-grained PAT> \
     KUDBEE_API_TOKEN=<long random string, e.g. openssl rand -hex 32>
   ```

5. Deploy from the repo root: `fly deploy`.
6. Verify (all should work in a browser / curl):
   - `https://kudbee-quant.fly.dev/` — dashboard renders with live data.
   - `https://kudbee-quant.fly.dev/api/health` — `{"status": "ok", ...}`.
   - `POST /api/alert` **without** a token → 401 (fail-closed check).
   - Send a real test alert (below) → `{"logged": true, ...}`, then within
     ~2 min a `tv-alert: sync 1 host-logged trade(s) [skip ci]` commit appears
     on `main` touching only `data/journal.json`.

## TradingView alert setup

Alert → Notifications → Webhook URL: `https://kudbee-quant.fly.dev/api/alert`.
Message (TV can't send headers, so the token rides in the body — HTTPS keeps
it private; avoid the `?token=` query form, it can end up in access logs):

```json
{"symbol": "{{ticker}}", "direction": 1, "entry": {{close}},
 "stop": <stop>, "target": <target>, "tf": "1h", "note": "<setup>",
 "token": "<KUDBEE_API_TOKEN>"}
```

`direction`: 1 long / -1 short (0 is rejected). Alerts log with
`source="human"` and get resolved/scored by the hourly Action like any other
pending bracket.

## Day-2 notes

- Redeploy after merging app changes: `fly deploy` (state on the volume
  survives; the image carries code only).
- Logs: `fly logs` — look for `[journal-sync] pushed N` / `up-to-date`.
- `/api/metrics` reports the Fly VM's CPU/mem/disk (it is public, like all
  reads — minor info disclosure, accepted in the PR #9 audit).
- If the app OOMs on 512MB (pandas+sklearn), bump `memory` in `fly.toml` to
  `1gb` (~$2/mo more) rather than fighting it.
- The volume is a cache of `origin/main` + at most a few unpushed alert
  commits; if it is ever lost, the entrypoint re-clones — nothing
  unrecoverable lives only on the host.
