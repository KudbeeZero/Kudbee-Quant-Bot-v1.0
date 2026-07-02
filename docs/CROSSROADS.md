# CROSSROADS.md — the decision board (the OFC's desk)

> One place for every open fork: the evidence, the options, the recommended default,
> and who has to move. This is real decision-making made visible — see `docs/BRAIN.md`
> Part II (the OFC/insula/reward council that sits here).
>
> **Discipline:** a decision made or deferred moves on this board **the same turn**,
> or the council is choosing on stale information. Each row is: *the fork → what we
> know → the options → the recommended default → who acts → status.*
>
> Legend — **OWNER** = needs your call/sign-off · **AGENT** = I can do it under the
> streaming workflow (direct commit / PR as it earns one) · **WATCH** = a trigger that
> fires later, no decision yet. Updated 2026-07-02.

---

## 🔴 DECIDE — needs the owner

### X1 · Live bring-up: the money-path pre-live gate  · **OWNER**
- **Fork:** enable live execution someday, or stay paper-only.
- **Know:** the on/off gate is airtight, but `docs/audits/security-review-2026-07-02.md`
  lists **8 latent bugs** that bite the first time live runs — critically, `submit`
  places an entry with **no venue-side stop** (a live position could run unstopped).
- **Options:** (a) stay paper — do nothing; (b) authorize me to fix the defensive
  subset (NaN/target/kill-switch fail-closed) now; (c) authorize the full pre-live
  hardening (venue stops, idempotency, partial fills) as a reviewed PR.
- **Recommended:** (b) now — pure fail-closed hardening that can't place a worse order;
  hold (c) until you actually intend to go live. **Never merge-on-green — money path.**
- **Status:** OPEN, awaiting owner. No live capital is at risk today (live unwired).

### X2 · Domain mailboxes on kudbeex.xyz  · **OWNER**
- **Fork:** the site links `hello@ / partners@ / press@kudbeex.xyz`; those mailboxes
  must exist or the addresses bounce.
- **Options:** (a) create/forward the three addresses; (b) tell me to drop them and
  route everything through the Formspree contact form instead.
- **Recommended:** (a) create `hello@` at minimum; I'll switch the others to the form
  if you prefer. **Status:** OPEN, owner-side (DNS/mail, outside the repo).

### X3 · Deploy secrets for the security hardening  · **OWNER**
- **Fork:** the Worker's manual trigger now needs `TRIGGER_SECRET`; the API rate-limiter
  wants a trusted-proxy config to key on the real client IP behind Render/Cloudflare.
- **Recommended:** `wrangler secret put TRIGGER_SECRET` (else the manual URL 403s — cron
  still runs); the proxy-IP config is a deploy-config change I can draft on request.
- **Status:** OPEN, owner-side (secrets/deploy).

---

## 🟡 DO NEXT — I can act (your pick of order)

### N1 · E2 — binance.us cross-venue data honesty  · **AGENT**
- **Fork:** the ingest fallback ends at `binance.us` (a *different* exchange); if the
  first two endpoints fail, its prints get labeled as the same symbol.
- **Options:** (a) tag the frame with its source + refuse to mix venues within a
  symbol's history (keep `.us` as a *tagged* last resort); (b) drop `.us` entirely
  (risk: it may be the only reachable endpoint on some runners); (c) leave it.
- **Recommended:** (a) — preserves reachability, kills the silent mislabel. Small, safe,
  testable; I'd commit it directly. **Status:** OPEN, ready when you say go. (Last
  data-honesty thread from the security review.)

### N2 · TradingView indicator suite  · **AGENT**
- **Fork:** you want to "get into creating indicators." Starting point exists:
  `pinescript/kudbee_confluence.pine`.
- **Options / phases:** (a) sync the Pine indicator to current engine state + add the
  ride-3R bracket display; (b) split standalone indicators (PVSRA candles, session/
  killzone boxes, M-levels/pivots, a confluence meter); (c) publish-quality polish.
- **Recommended:** start with (a) — smallest, highest-fidelity. Keep the Pine VWAP sign
  = momentum (§75 parity is test-pinned). **Status:** OPEN, queued.

### N3 · Go deeper on the brain map  · **AGENT**
- **Fork:** which region gets pushed down another level next (you asked for finer
  subsections). Candidates: split the Hippocampus into encoding/consolidation/retrieval
  as real modules; give the amygdala/risk region its own finer map; build the DMN into
  an open-ended idea generator (today it's a fixed candidate registry).
- **Recommended:** the **DMN generative layer** — it's the one region that's more
  metaphor than code, so deepening it adds real capability, not just documentation.
- **Status:** OPEN, creative direction.

---

## 🟢 WATCH — triggers that fire later (no decision yet)

### W1 · Post-fix forward record (the new era-3)  · **WATCH**
- After **50+ resolved 1h trades** post-2026-07-01, `journal-score` the momentum+ride-3R
  book (the §75/§76/§77 config — the first time the live bot has run the exact validated
  configuration) as its own era; do NOT pool across the 06-16→07-01 rotation era. Then
  the fork opens: keep / adjust.

### W2 · §70 24h deadline  · **RESOLVED (kept)**
- Checkpoint met, verdict KEEP (§73). No action; left here for continuity, remove next sweep.

---

## Recently decided (short memory, so the board shows momentum)
- **Ride-3R shipped** to the paper book (§76, PR #131) — geometry fork closed.
- **VWAP reverted to momentum** (§75, PR #130) — signal fork closed.
- **Forming-candle fix** (§77, PR #136) — the bot now reads closed bars only.
- **Security + engine review** (PRs #134/#135) — web surface hardened, safe engine fixes shipped.
- **Website redesign → The Journal** (PR #133) + SEO/mobile sweep (PR #132) — done.
- **Workflow → streaming** + **BRAIN.md** brain map — done (direct-to-main, 2026-07-02).
