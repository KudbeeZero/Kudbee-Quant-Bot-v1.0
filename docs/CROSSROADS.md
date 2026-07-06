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
> fires later, no decision yet. Updated 2026-07-06 (N4 shipped; branch ledger stood up).

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
  6. **`KUDBEE_API_TOKEN` repo secret** (found missing by the §86 Telegram audit): repo
     Settings → Secrets → Actions → `KUDBEE_API_TOKEN` = the same write token set as a
     Fly secret. Without it `telegram-register.yml` can never self-register the webhook,
     so slash commands stay dead even after step 3 deploys the API.
- **Alt (step 1):** keep DNS on Namecheap + its free email forwarding — loses
  Cloudflare Email Routing and a clean Pages custom domain. **Recommended:** move
  nameservers.
- **Status:** OPEN, owner-side. Steps 1/2/4/5 are phone-doable; step 3 needs a
  machine with `flyctl`. Repo-side halves of steps 2–3 (the proxy Functions) are
  already committed to `main`.

### X3 · Transparency posture: the whole repo is public (GitHub + Pages)  · **OWNER**
- **Found (2026-07-05, Fable-5 review §83):** the GitHub repo is **public**, and
  Cloudflare Pages publishes the repo root, so `docs/MEMORY.md`, `docs/audits/`,
  `research/`, and the engine source are all world-readable on BOTH surfaces. Yet we
  block `/data/*` on the site (§80 "privacy leak" fix) — an inconsistent posture:
  the journal that Function hides is public on GitHub anyway.
- **Options:** (a) **embrace transparency** (it fits the "honest quant" thesis) —
  keep everything public, accept that strategy internals/ops playbooks are readable,
  optionally still blocking `/data/*` as a courtesy speed-bump; (b) **go private** —
  make the GitHub repo private + restrict Pages to an allowlist of site files (needs
  a build step or a catch-all Function); (c) middle: keep the repo public but strip
  the site publish surface to HTML/assets only.
- **Recommended:** (a) — the site already markets radical honesty, the edge is
  execution not secrecy (§2), and (b) breaks the public journal/lab pages. Decide
  deliberately rather than by accident.
- **Status:** OPEN, owner call. No action taken.

### X5 · Branch cleanup: approve the dead-branch deletion list  · **OWNER**
- **From the 2026-07-06 Branch Execution Ledger** (`docs/AGENT_ORCHESTRATION_LEDGER.md`,
  bottom section): of 135 remote branches, **102 are dead** (66 fully merged + 36
  patch-equivalent squash leftovers — section D), **16 more are superseded** (section C,
  deletable after two small verdict-harvests), **12 carry unique value** (section B —
  each with its own recommended action; `zcash-…` stays SALVAGE-HOLD per MEMORY).
- **Owner APPROVED (2026-07-06): delete D now, C after the N7 harvests.** But the agent
  container **cannot delete remote refs** (the git credential proxy 403s `push --delete`;
  the GitHub MCP toolset has no delete-branch tool) — so the approved deletion is packaged
  as **`scripts/delete_dead_branches.sh`**: re-verifies every branch is still
  merged/patch-equivalent against fresh `origin/main` immediately before deleting it,
  skips loudly otherwise; dry-run by default (`--run` to execute). Dry-run verified
  2026-07-06: 102/102 verified dead, 0 skipped.
- **Remaining action (owner, one command):** `bash scripts/delete_dead_branches.sh --run`
  from any machine with push rights (or delete from the GitHub branches UI). Section C's
  16 get appended to the script after the N7 harvests land.
- **Status:** APPROVED — execution owner-side (script ready).

### X4 · Core-engine fixes from the §83 review (change-gated code)  · **OWNER**
- **Fork:** the review found real defects in the levels/backtest core, which is
  off-limits without your sign-off: the **London Brinks box lookahead** +
  `ny_open` leak + AWR/AMR stub-period gap (`levels/builder.py`), the
  **entry-bar fill blind spot** in the maker-entry backtests (`backtest/bracket.py`
  — entry-bar stop-outs impossible by construction, optimistic bias), the
  `bracket_excursions` MFE/stop-bar accounting, and never-clearing FVG zones
  (semantics differ from the docstring the `v_fvg` vote was validated under).
- **Know:** none of these touch the live 3.0R/1.5-ATR/1h defaults directly, but the
  Brinks/FVG items affect research-layer scores, and the entry-bar item means every
  maker-entry backtest (incl. §42's) is somewhat flattered. Fixes are localized and
  test-pinnable; changing them will shift research numbers, so it earns a PR.
- **Options:** (a) authorize a reviewed PR fixing all of the above with regression
  tests + a before/after impact table; (b) fix only the causality bugs (Brinks/
  ny_open/FVG) and leave fill simulation for later; (c) leave as documented caveats.
- **Recommended:** (a) — one honest PR, since the whole point of the harness is that
  its numbers are trustworthy. **Not merge-on-green — backtest core.**
- **Status:** OPEN, awaiting owner.

---

## 🟡 DO NEXT — I can act (your pick of order)

### N7 · Ledger harvests (small, docs/research-honesty)  · **AGENT**
- From the Branch Execution Ledger section B: record the **conf_70 high-conviction
  result** (Δ+0.195R p=0.035, `handoff-audit-rk3gn7`, with a predates-§75/§77 caveat),
  the **psych-1h HARD NEGATIVE** and the **VAH-trap REJECT** verdicts into MEMORY;
  copy the **#102/#14 audit reports** into `docs/audits/`; re-test the **no-JS
  white-screen site fix** (`kudbeex-blank-page-q6pdql`) against the current site.
- All tiny, all sharpen the record; unblocks section C deletions under X5.

### N6 · Research-honesty fixes (ML/audit/overnight)  · **AGENT**
- **From §83:** purge by label-END (`entry_time >= test_start - horizon`) in
  `ml/cv.py`; sample meta-label features at the signal bar, not the fill bar
  (`ml/labels.py`); `scenarios/audit.py` must not report clean on zero checks;
  stamp/refuse stale overnight caches (`overnight_research.py`); drop the trailing
  partial bucket in `ingest/resample.py`; registry import failure should be loud.
- None touch the live path; all sharpen the significance gate the project's claims
  rest on. Do before the next research campaign.

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


---

## Recently decided (short memory, so the board shows momentum)
- **N5 deploy/CI hardening SHIPPED** (2026-07-06, direct-to-main, §85): flyctl action
  SHA-pinned (=1.6) + `permissions: contents: read` on both workflows; `requirements.lock`
  (full transitive pin, Docker image installs from it — the hourly rebuild can't drift);
  `api.py` webhook base-URL now `?url=` → `API_ORIGIN` → `FLY_APP_NAME` → request base
  (dead `RENDER_EXTERNAL_URL` removed) + uvicorn `--proxy-headers`; MATIC dropped
  (delisted); Kestra flows now scan TOP_10 like the Action; `/summary` copy honest
  ("across all books"). 747/747 tests (1 new). Fly deploy itself is still X2 step 3.
- **N4 journal durability SHIPPED** (2026-07-06, PR #140 merged, owner-authorized):
  atomic saves (journal/chart_reviews/control), per-symbol isolation in `check_open()`,
  NaN guards on the paper path, JSON-validated `commit_journal.sh`; 746/746 (6 new tests).
  Closes the "bot silently stopped trading" failure class from §83.
- **PR #138 merged** (2026-07-06, owner-authorized) — the parallel `/handoff-audit` of
  #137 (`docs/audits/pr-137.md`, PASS ×2 with #139's) + baton reconciliation; its baton
  collision with #139 resolved. **Branch Execution Ledger stood up** the same turn
  (`docs/AGENT_ORCHESTRATION_LEDGER.md`): 135 branches classified, deletions gated on X5.
  (§82) — the "test it properly" fork closed; do not re-test without a new angle.
- **W2 (§70 24h deadline)** — resolved KEPT (§73); row removed this sweep as planned.
- **Fable-5 full-codebase review** (§83, 2026-07-05) — findings triaged into X3/X4/N4–N6
  above; docs/memory layers reconciled the same session.
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
