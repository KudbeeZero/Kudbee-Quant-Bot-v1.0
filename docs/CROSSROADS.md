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

### X0 · Deploy the API to Fly.io (host decided; deploy pending)  · **OWNER**
- **Found (2026-07-02, `docs/wiring-verification-2026-07-02.md`):** the marketing
  site is live + hardened, but the **app layer is not wired end-to-end**. Three
  things surfaced; two are fixed in-repo, one is the owner's deploy.
- **Decided (2026-07-02):** backend host = **Fly.io** (owner: "not using Render").
  `render.yaml` retired; added `Dockerfile`, `fly.toml`, `.github/workflows/fly-deploy.yml`.
- **Fixed in-repo:** (a) `/api/*` proxy was Netlify-only (dead on Cloudflare Pages)
  → Pages Function `functions/api/[[path]].js` proxies `/api/*` → Fly same-origin
  (`API_ORIGIN`-overridable); (b) **privacy leak** — raw `data/journal.json` (open
  entry/stop/target) was public at `kudbeex.xyz/data/*` → Pages Function
  `functions/data/[[path]].js` 404s the whole tree at the edge.
- **Owner action (the blocker):** `fly launch --no-deploy` → `fly secrets set …`
  → `fly deploy` (full runbook `docs/HOSTING.md`). Optionally add the `FLY_API_TOKEN`
  repo secret to turn on the hourly auto-deploy freshness workflow. Then the
  dynamic pages (Live Signals / Trade Flow / Lab) light up.
- **Status:** OPEN, owner-side (Fly deploy). Proxy + leak fixes committed to `main`.

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

### X2 · Domain + mailboxes on kudbeex.xyz  · **OWNER**
- **Fact (2026-07-02):** owner OWNS `kudbeex.xyz` on **Namecheap**. No need to buy a
  new domain. Registrar stays Namecheap; move the DNS **zone** to Cloudflare (free).
- **Path (phone, ~10 min):** (1) Cloudflare → Add site `kudbeex.xyz` (Free) → get 2
  nameservers; (2) Namecheap → Domain → Nameservers → Custom DNS → paste them; (3) once
  Active: Pages custom domain (`kudbeex.xyz` + `www`) + **Email Routing** forwarding
  `hello@/partners@/press@` (free — solves the mailbox need) + Worker `TRIGGER_SECRET` (X3).
- **Alt:** keep DNS on Namecheap and use its free email forwarding — but then no
  Cloudflare Email Routing / clean Pages custom domain. **Recommended:** move nameservers.
- **Wiring note (2026-07-02):** apex `kudbeex.xyz` verified **200 live**; `www` could
  not be confirmed from the agent container (proxy 502'd `www` while apex succeeded) —
  when setting the Pages custom domain, add **both** `kudbeex.xyz` and `www`.
- **Status:** OPEN, owner-side (all doable from a phone browser; no repo change).

### X3 · Deploy secrets for the security hardening  · **OWNER**
- **Fork:** the Worker's manual trigger now needs `TRIGGER_SECRET`; the API rate-limiter
  wants a trusted-proxy config to key on the real client IP behind Render/Cloudflare.
- **Recommended:** `wrangler secret put TRIGGER_SECRET` (else the manual URL 403s — cron
  still runs); the proxy-IP config is a deploy-config change I can draft on request.
- **Status:** OPEN, owner-side (secrets/deploy).

---

## 🟡 DO NEXT — I can act (your pick of order)

### N1 · E2 — binance.us cross-venue data honesty  · ✅ **DONE (2026-07-02, §78)**
- **Chosen:** option (a) — frames tagged with `source_venues`, loud warning on any
  `.us` fallback, `.us` kept as a tagged last resort. `/code-review` caught that the tag
  was lost on cache reuse → `DataCache` now persists+restores `df.attrs` and re-warns on
  every cache hit. Tests cover miss / clean-path / reuse. Direct commit to `main`.

### N2 · TradingView indicator suite  · phase (a) ✅ **DONE (2026-07-02, §78)**
- **Done:** synced `pinescript/kudbee_confluence.pine` to the current engine — VWAP
  momentum (§75), ride-3R default (§76), and `barstate.isconfirmed` closed-bar gating on
  the bracket + webhook + both alertconditions (§77 parity, no intrabar repaint).
- **Still open (phases b/c):** split standalone indicators (PVSRA candles, session/
  killzone boxes, M-levels/pivots, confluence meter) + publish-quality polish. Queued.

### N3 · Deepen the brain — DMN generative layer  · ✅ **DONE (2026-07-02, §79)**
- **Done:** `scripts/idea_generator.py` — the DMN now COMPOSES new candidates
  (regime-gate × execution-override), dedups vs tested history + hand-written registry,
  and feeds the significance gate. `--list`/`--emit N`. 3 new tests.
- **Still open (creative direction, future):** split the Hippocampus into
  encoding/consolidation/retrieval modules; give the amygdala/risk region a finer map.

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
- **N1 binance.us data honesty + N2 Pine sync** (§78, /code-review'd) — done (direct-to-main).
- **BRAIN.md Part II** (creative + decision council) + **this board** — done.
- **N3 DMN idea generator** (§79) — the registry is now generative; done (direct-to-main).
