# Security + quality review — pre-Fable-5 code — 2026-07-02

Owner-requested review of everything built by prior sessions that this chat's model
had not touched: the public API/auth surface, the Telegram + Cloudflare edge ingress,
the live-execution money path, and the analytical engine. Four parallel read-only
reviewers; every finding below was re-verified firsthand against the code before any
fix. Fixes shipped this pass are web-surface only — the live-money path is under the
standing "explicit owner sign-off" governance rule, so its findings are documented as
a hard pre-live gate, not auto-fixed.

## What was FIXED this pass (PR — web surface, no trading-logic change)

| # | Sev | Finding | Fix |
|---|-----|---------|-----|
| 1 | HIGH | `/api/journal` (public) exposed every open position's exact `entry`/`stop`/`target` + was the only unthrottled read (disk + pandas per call) — a stop-hunt / front-running vector. | Stripped `entry`/`stop`/`target` from the public `open[]` (kept id/symbol/setup/status/direction/created_at); added `_read_limit`. Verified neither consumer needs the prices: the public Lab reads only `by_source`/`resolved_series`/`exposure`; the gated dashboard uses `counts`/`resolved_series` here and the separate gated `/api/open-trades` for position detail. Test: `test_journal_open_positions_hide_price_levels`. |
| 2 | MED | Cloudflare Worker `fetch()` ran `dispatch()` with **no auth** — any URL-knower could spam `workflow_dispatch` (Actions-minute burn + Telegram flood). | `fetch()` now requires `TRIGGER_SECRET` (header or `?key=`), constant-time compare, **fail-closed** (403 when unset). Returns a generic status, not GitHub's raw body. `scheduled` cron path untouched. README documents the new secret. |
| 3 | MED | `register-webhook` accepted `KUDBEE_API_TOKEN` only via query string → lands in access logs. | Now prefers the `X-API-Token` header; query param kept for browser convenience with a rotate-if-used caveat in the docstring. |
| 4 | LOW | `/api/metrics` (host CPU/RAM/disk totals) was unauthenticated infra disclosure. | Added `Depends(require_session)`. Test: `test_metrics_endpoint_requires_session`. |
| 5 | LOW | Rate-limiter `_HITS` map never evicted emptied buckets (slow unbounded growth). | Evict aged-out buckets each call. |

**Deliberately NOT changed (deployment concern, flagged):** the rate limiter keys on
`request.client.host`, which behind Render/Cloudflare is the proxy IP — all clients share
one bucket (a single attacker can trip the global login limit and lock others out; or, if
`X-Forwarded-For` is honored untrusted, per-IP limits are bypassable). The correct fix is
to configure trusted-proxy forwarded-IP handling at the ASGI layer, which is a deploy/config
decision — recorded for the owner, not changed blind.

## Verified SAFE (checked, sound — do not re-flag)
- **Auth primitives:** `check_token`, `check_password`, `verify_session`, and the Telegram
  webhook secret all use `hmac.compare_digest` (constant-time) and fail closed. Session
  cookie is HMAC-SHA256, `HttpOnly; Secure; SameSite=lax`.
- **Telegram ingress:** fail-closed webhook-secret gate + single-owner chat-id allow-list +
  admin-id gate on mutators; `/trade`→`/yes` is strictly PAPER (no exchange path); 60s
  per-chat confirmation gate. No command injection; D1 uses parameterized binds.
- **Alert→journal:** every field Pydantic-bounded, symbol regex-constrained, inbox filename
  is a SHA-256 digest (no path traversal), journal is JSON (no structural injection). A
  token holder logging a paper trade is the intended auth boundary, not a bypass.
- **Runner:** fixed action dispatch (no dynamic import), bounded params, dry-run only,
  session-gated, tracebacks never returned.
- **Worker→GitHub:** Bearer `GH_TOKEN` is a Worker secret (not in `wrangler.toml`), never
  echoed to Telegram. Workflow secrets injected via `${{ secrets.* }}`, never echoed.
- **Engine lookahead-audit (spot-check):** `levels/builder.py` ADR, floor pivots,
  prior-NY high/low, day-color, monthly range, and consec-run all use `shift(1)` for
  strictly-prior periods with documented current-day fallbacks. The shared `resolver.py`
  is a pure function (no global state), checks stop before target within a bar, and updates
  the trailing extreme only from prior bars — no same-bar look-ahead. Claim holds where checked.

## HARD PRE-LIVE GATE — live-execution latent findings (NOT fixed; owner sign-off required)

The double opt-in gate is **airtight** (re-confirmed: `require_live_enabled` at both
construction and submit; `LiveExecutor` is invoked nowhere; production is paper-only). But
the code *after* the gate has latent bugs that would bite the first time live is enabled.
These touch the money path (off-limits without explicit sign-off), so they are recorded
here as blockers, not changed:

1. **CRITICAL (latent):** `submit` places only the entry limit — **no stop/target order on
   the venue**. Exits are inferred from bars via the shared `check_open`, which has no
   `mode=="live"` guard → the journal can mark a live trade "closed/stopped" while the real
   position stays open and unstopped on the exchange (and if the process is down, there is no
   stop at all). Fix before live: place real OCO/stop orders at submit, OR drive live exits
   only from venue polling (exclude live from bar resolution).
2. **HIGH (latent):** no idempotency / `newClientOrderId`, and the order is placed before
   journaling → a retry double-submits (2× size, exceeding the cap) or orphans a real position.
3. **HIGH (latent):** `PARTIALLY_FILLED` is handled by neither `poll` branch → trade stuck
   `pending` with real money in the market; downstream accounting uses full (unfilled) qty.
4. **MED (latent):** live fill timestamp is matched to a bar by **exact equality** — a
   real 14:37 fill never equals an hourly boundary → resolves from window start (wrong price).
5. **MED (latent):** no `exchangeInfo` lot/tick/min-notional rounding; small qty serializes
   as `1.2e-05` → Binance rejects (fails closed, but live never actually works).
6. **MED (latent):** a non-finite (`NaN`) `position_size_usd` passes the `<=0` guards
   (`NaN<=0` is False) → `qty=NaN` reaches the venue (rejected, but no explicit guard).
7. **MED (latent):** kill-switch `realized_loss_usd_today` skips a trade whose timestamp
   fails to parse (`except: continue`) → a corrupt stamp on a big loser makes the cap
   under-count and **fail open** for that trade. Also realized-only (open drawdown uncapped).
8. **LOW (latent):** `submit` doesn't require a resolvable `target`/`target_r` → a
   target-less live bracket crashes the whole resolve loop.

These are the concrete preconditions for the still-pending live bring-up. The defensive
subset (6, 7, 8 — pure fail-closed hardening that can never place a worse order) is safe to
do first under sign-off; items 1–5 need design decisions.

## Not completed this pass
The engine-quality deep-dive reviewer did its analysis but could not emit its final report
(repeated API-Overload errors during this run). The lookahead spot-check above is my own
firsthand verification, not that agent's full pass — a complete engine correctness/numerical
review (division-by-zero, NaN propagation into sizing, caching TTL, pandas foot-guns) remains
a scoped follow-up. Advisory slug: `claude/engine-quality-review`.
