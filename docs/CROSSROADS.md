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

### X0 · App layer not wired end-to-end (root cause + repo-side fixes)  · **OWNER**
- **Found (2026-07-02, `docs/wiring-verification-2026-07-02.md`):** the marketing
  site is live + hardened, but three app-layer breaks surfaced. **Decided:** backend
  host = **Fly.io** (owner: "not using Render"); `render.yaml` retired.
- **Fixed in-repo:** `Dockerfile` + `fly.toml` + `.github/workflows/fly-deploy.yml`;
  Pages Function `functions/api/[[path]].js` (the `/api/*` proxy was Netlify-only,
  dead on Cloudflare Pages); Pages Function `functions/data/[[path]].js` (closed a
  **privacy leak** — raw `data/journal.json`, incl. open entry/stop/target, was
  publicly downloadable via Pages serving the repo root).
- **The remaining owner action (the Fly deploy) is now step 3 of the consolidated
  bring-up checklist → see X2.** Kept here only as the historical record of what
  broke and why; don't track the deploy step in two places.
- **Status:** repo-side fixes on `main`. Deploy tracked under X2.

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

### X2 · Full bring-up checklist: domain + API + mailboxes  · **OWNER**
- **Consolidated (2026-07-02):** everything left to flip the site from "live
  marketing page" to "fully wired product" in one ordered list. Phone-doable except
  the Fly deploy (needs `flyctl` on a machine).
  1. **DNS zone → Cloudflare** (free): owner OWNS `kudbeex.xyz` on **Namecheap** — no
     new domain needed. Cloudflare → Add site `kudbeex.xyz` (Free) → get 2 nameservers
     → Namecheap → Domain → Nameservers → Custom DNS → paste them.
  2. **Pages custom domain:** once Active, add **both** `kudbeex.xyz` **and** `www` —
     apex verified **200 live** 2026-07-02; `www` couldn't be confirmed from the agent
     container (proxy 502'd it while apex succeeded), so confirm both are attached.
  3. **Deploy the API to Fly.io** (X0, the app-layer blocker): `fly launch --no-deploy`
     → `fly secrets set …` → `fly deploy` (full steps `docs/HOSTING.md`). If the Fly
     app name isn't `kudbee-quant-api`, also set `API_ORIGIN` in Pages → Settings →
     Environment variables to `https://<your-app>.fly.dev` so `functions/api/[[path]].js`
     proxies to the right place.
  4. **Email Routing** (free, solves the mailbox need): Cloudflare → Email → forward
     `hello@/partners@/press@`.
  5. **Worker `TRIGGER_SECRET`:** `wrangler secret put TRIGGER_SECRET` (else the
     manual trigger URL 403s — the cron itself still runs without it).
- **Alt (step 1):** keep DNS on Namecheap + its free email forwarding — loses
  Cloudflare Email Routing and a clean Pages custom domain. **Recommended:** move
  nameservers.
- **Status:** OPEN, owner-side. Steps 1/2/4/5 are phone-doable; step 3 needs a
  machine with `flyctl`. Repo-side halves of steps 2–3 (the proxy Functions) are
  already committed to `main`.

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
- **Backend host → Fly.io** (§80, Render retired) + **`/api` proxy fix** + **`data/` privacy
  leak closed** — repo-side wiring done (direct-to-main); Fly deploy is X2 step 3, owner-side.
