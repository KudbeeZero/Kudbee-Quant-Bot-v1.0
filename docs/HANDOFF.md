# HANDOFF — the baton

> Updated by `/closeout` at the end of each chat; read by `/handoff-audit` (and
> the SessionStart hook) at the start of the next. See `docs/SESSION_PROTOCOL.md`.
> Keep this SHORT — it's a baton, not a log. History lives in git + `docs/audits/`.

## Current baton

- **Protocol status:** `ACTIVE`.
- **Last branch:** `claude/hello-3vl2b8` (PR #16) + `claude/near-miss-autopsy` (PR #17).
- **Last PR:** #16 + #17 — both **MERGED** into `main` at `8b92ba5`.
- **Audit status:** `MERGED (audit PASS)` — both gated this session (user-invoked
  `/handoff-audit`) by independent arm's-length subagents in isolated worktrees.
  **#16** (live order-placement): PASS — maker-only `LIMIT_MAKER` (no market method),
  double gate intact, no-keys submit safely rejected, kill-switch math correct,
  venue-clock fills, no secret leakage, 259 passed/5 skipped, ruff/scope clean
  (`docs/audits/pr-16-audit.md`). **#17** (near-miss autopsy): PASS — no live-config
  change, replay reconciles 118/118 @3R, IS-vs-OOS separated, OVERFIT verdict
  OOS-driven, honest caveats (`docs/audits/pr-17-audit.md`). Self-audit caveat
  recorded in both. Gate streak: #5,#6,#7,#9,#11,#12,#13,#14,#16,#17.
- PR #14 CLOSED OUT: **`MERGED (post-hoc CONCERNS)`** — human-merged from the UI
  2026-06-14T00:19Z at `c2bf507`→head `d295eed`; green CI. Independent audit
  (`docs/audits/claude-hello-3vl2b8.md`): 9/10 claims diff-verified, ruff clean,
  no scope/secret/forbidden issues, live-gate contract real+tested. ONE cosmetic
  concern: "254 passed (210+44)" headline inflated — measured base=193/head=237.

## What this chat did (for the auditor to verify against the diff)

- **PR #14 audit gate → post-hoc CONCERNS (cosmetic), recorded** — independent
  arm's-length subagent vs the real `c2bf507..d295eed` diff; report
  `docs/audits/claude-hello-3vl2b8.md`. (Already merged from UI; nothing to merge.)
- **Live order-placement subsystem (PR #16)** — replaces the `LiveExecutor` stub
  with a real, still-double-gated path (user-confirmed scope 2026-06-13/14). NEW:
  `execution/exchange.py` (`ExchangeClient` Protocol + native HMAC-signed
  `BinanceBrokerClient`, **maker-only `LIMIT_MAKER`, no market method**, env-only
  keys, testnet, SSRF-safe symbols); `execution/killswitch.py` (`MAX_DAILY_LOSS_USD`,
  honest R→USD bridge, today's live losses only); rewrote `execution/live.py`
  (`submit` = gate→kill-switch→cap→size→rest maker limit→journal live/pending w/
  `exchange_order_id`; `poll` stamps `filled_at` from the VENUE clock not bar time;
  `cancel`/`reconcile`). `journal/__init__` exports `net_outcome_r`/`fee_r_of`.
  Rewrote `docs/LIVE_TRADING_SETUP.md`. **259 passed, 5 skipped** (+24 new hermetic
  fake-exchange tests). Ruff clean. §1/`FEE_PCT`/journal/alert_inbox untouched; no
  secrets. NOT wired into the hourly Action. MEMORY §38 added.
- **NOTE (honest):** the live path has **never placed a real order in production** —
  logic-tested only; treat as unproven live. ccxt deliberately not taken (native
  client sits behind the Protocol; ccxt can slot in later).

## NEXT chat

- **Slug hint (ADVISORY only):** `claude/min-pct-shadow-or-live-wiring` — harness
  assigns the real name; the *scope* below is what binds.
- **DECISION PENDING (user): the autopsy's `--min-pct 0.6` recommendation.** The
  near-miss autopsy (PR #17, `docs/research/near_miss_autopsy.md`) concluded: do NOT
  drop the 60% band and do NOT lower the target — both are **in-sample-only / OVERFIT**
  (the OOS walk-forward refutes them; 3R is correct, the 60% gate is net-positive OOS).
  The only OOS-supported tweak is tightening the hourly scan `--min-pct 0.5 → 0.6`,
  and even that is modest (frac-positive 55%, one correlated-majors window) — RECOMMEND
  a forward shadow-test (journal 0.5 vs 0.6 in parallel), NOT a hard flip. **Awaiting
  user approval before any live-config change.** The fixes the autopsy DID validate
  (trend-filter on, 5m paused) are already live.
- **Scope options for the next chat (pick one):**
  (a) **`--min-pct 0.6` shadow-test** — if the user approves, wire a parallel 0.6 gate
  (or A/B label) without disturbing the live 0.5 book, and compare forward;
  (b) **wire the live executor (PR #16) into a CLI / the hourly Action** — still the
  opt-in decision; start with a `BINANCE_TESTNET=true` smoke-test
  (`docs/LIVE_TRADING_SETUP.md`) before any mainnet key;
  (c) **top-100 universe flip** decision (opt-in; 10× API load, floods the bot-owned
  journal — `docs/TOP100_1H_UNIVERSE.md`).
- **FIRST (carryover): verify the 5m pause landed** — confirm the hourly Action
  logs NO new `5m` signals (§37 still unverified in production).
- **Live deploy walkthrough (also queued):** once the user creates the Render
  service (`docs/HOSTING.md`), smoke-test the live host — health, dashboard, a
  real `/api/alert` with `"inbox": true`, the alert commit appearing in
  `data/alert_inbox/` and ingested by the next hourly run.
- **Open risks / watch-items:**
  - **Live execution EXISTS but is UNPROVEN live (PR #16):** real maker-only,
    double-gated order path, logic-tested only — has NEVER placed a real order in
    production. Paper still default; both flags + real keys required. Start on
    testnet, tiny size. Not wired into the hourly Action.
  - **Top-100 membership UNPROVEN forward (§31):** only the top-10 majors are
    walk-forward validated; the long tail in `config/crypto_universe.yaml` is a
    static fallback snapshot, forward-test only. The hourly Action still runs top-10.
  - **5m pause UNVERIFIED in production (§37):** the workflow edit was tested
    locally (YAML + 254/254) but not yet confirmed on the hourly Action — confirm
    the next run logs no new 5m signals.
  - **Deployment UNPROVEN:** render.yaml + inbox tested locally only; no live
    Render service exists yet (user action: create Blueprint via `docs/HOSTING.md`;
    set `KUDBEE_API_TOKEN` / `KUDBEE_SITE_ORIGIN` / `KUDBEE_GH_TOKEN`).
  - **Possible edge decay on 1h crypto book** (§36 addendum: orig −91.9R / fade
    +89.8R over ~4 months OOS; §37 check: only −2R/2 trades since 06-12, too small
    to read) — re-check as forward data accrues before action.
  - **Branch deletions pending (user action, §32):** safe to delete via GitHub UI:
    handoff-audit-hvuuab, hello-1lje1b, overnight-algo-research-plan-hyqzf6,
    sol-short-position-0eytax, fable-5-release-review-mow58s,
    handoff-audit-fee-scoring-p0yg4n, handoff-audit-xtn2bz,
    zcash-backtest-orderbook-shjg5o (salvage PR #9 merged).
  - **Accepted disclosures (HOSTING.md):** public `/api/metrics`, `?token=`
    supported for TV compatibility.
  - **§33:** replay pct ≠ live-edge pct — never use a replay's confluence pct
    to re-verify the entry gate; caveat ships in every replay response/CLI footer.
  - **§31:** 11 added TradFi symbols UNPROVEN forward; watch softs.
  - **§29/§30 standing caveats** + maker-vs-taker fee contradiction (one real
    LIMIT fill settles it); scorecard still not an edge readout.
- **Off-limits:** validated strategy defaults (§1) and `FEE_PCT`;
  `data/journal.json` (bot-owned — no session commits); **`data/alert_inbox/`
  (host+Action-owned — no manual session commits there either)**; crypto
  daily grouping stays calendar-dated; held salvage branches only with explicit
  user OK.

## Baton history

- `BOOTSTRAP` — relay protocol introduced (PR #2).
- `2026-06-09` — PR #2 merged from UI pre-audit; post-hoc audit PASS. Protocol
  hardened on `claude/handoff-audit-xtn2bz`: baton hands off scope (not a branch
  name), `/handoff-audit` checks real PR state + post-hoc path, status reconciled.
- `2026-06-10` — PR #4 merged (user-authorized, CI green): net-of-fee scoring (§26
  DONE) + protocol hardening. Duplicate PR #3 closed as superseded (§28). Next scope:
  TradFi session/RTH level verification.
- `2026-06-10` — PR #5 opened (`claude/fable-5-release-review-mow58s`): PR #4
  post-hoc audit PASS + TradFi session fixes (§29) — stub-day levels, Yahoo tick
  row, pending false-fills; 183 tests.
- `2026-06-10` — PR #5 **audited (PASS) and merged** by `claude/handoff-audit-hvuuab`
  (gate held). §28 recurred: that chat's duplicate trade-date fix reverted as
  superseded (§30). PR #6 opened (docs-only). Next scope: `_tradfi` taint audit +
  universe expansion (+11 assets); Jarvis dashboard queued after.
- `2026-06-11` — PR #6 **audited (PASS) and merged** at `dd809c9` by
  `claude/hello-1lje1b` (gate held again). Blemish: §30 Monday-flip lower bound
  ~33%, not 40%.
- `2026-06-11` — PR #7 opened (`claude/hello-1lje1b`): PR #6 audit + taint-audit
  verdict (pre-fix `_tradfi` book CLEAN, §31) + universe +11. Next scope: Jarvis
  dashboard.
- `2026-06-11` — PR #7 **audited (PASS) and merged** — SELF-AUDIT (user-invoked
  in the authoring session; independent subagent + live `/verify`; caveat in
  the report). Gate streak: #5, #6, #7.
- `2026-06-12` — PR #7 post-hoc spot-check **PASS** by `claude/hello-7olm3u`
  (arm's-length; caveat discharged). Branch sweep: no journal data off `main`
  (§32). PR #9 opened: dashboard salvaged from zcash `6632c48` + fixed (real
  API fields, XSS escaping) + §32; TV-webhook scope then PULLED FORWARD into
  the same PR (user-directed, disclosed in the PR body) — `/api/alert` made
  TV-usable + `source="human"`. 191 tests. Next scope: hosting.
- `2026-06-12` — PR #9 **audited (PASS) and merged** at `8b1677e` by
  `claude/handoff-audit-tradingview-6sswe1` (gate held; arm's-length). Nits
  carried to hosting: `/api/metrics` public host-info disclosure, `?token=`
  log exposure. Gate streak: #5, #6, #7, #9.
- `2026-06-12` — PR #10 opened (`claude/trade-viz-draggable-indicators-yncx2t`):
  Trade Flow visualizer (trace/sandbox/replay + CLI, §33), 201 tests,
  AWAITING_AUDIT. Parallel chat opened PR #9 (dashboard + webhook, §32 claim)
  mid-session — next scope: audit + land BOTH, #9 first, resolve conflicts.
- `2026-06-12` — PR #11 opened (`claude/handoff-audit-tradingview-6sswe1`):
  PR #9 gate report + hosting unit (Render Starter blueprint + TV alert inbox,
  §34; 200 tests; deployment UNPROVEN until the Render service exists). Next
  scope: audit PR #10 + live deploy walkthrough.
- `2026-06-12` — PR #11 **audited (post-hoc PASS) + PR #10 audited (PASS) and
  merged** at `8c1927b` by `claude/handoff-audit-4t6op3` (gate held; arm's-length
  subagent for both). Conflict resolution: all 3 conflicted files resolved, both
  feature sets preserved, MEMORY.md §32-§36 renumbered correctly. 210/210 tests.
  Gate streak: #5, #6, #7, #9, #11.
- `2026-06-13` — PR #12 **audited (post-hoc PASS)** by
  `claude/live-trades-check-plan-5y27i8` (already merged from UI; arm's-length
  subagent, docs-only diff, 210/210). Same chat ran a read-only live-trades check
  and **paused the 5m crypto book (§37)** — forward-confirmed fee drag (net −3.2R,
  gross-flat). PR opened. Gate streak: #5, #6, #7, #9, #11, #12. Next scope:
  verify the 5m pause landed, then Execution Lab.
- `2026-06-14` — PR #13 **audited (PASS) + merged** at `c2bf507` by
  `claude/live-trades-5m-pause-a1wuk3` (gate held; arm's-length subagent, 210/210).
  Same chat built the **top-100 1h trading FOUNDATION + trade-review skills**
  (PR #14): paper-first, live double-gated + stubbed, universe loader, review
  reports (MFE/MAE), Kestra scaffold, docs; **254 passed**. Gate streak: #5, #6,
  #7, #9, #11, #12, #13. Next scope: the live order-placement subsystem.
- `2026-06-14` — PR #14 post-hoc audit **CONCERNS (cosmetic)** recorded by
  `claude/hello-3vl2b8` (already merged from UI). Same chat built the **live
  order-placement subsystem** (PR #16): maker-only `LIMIT_MAKER`, double-gated,
  `MAX_DAILY_LOSS_USD` kill-switch, venue-clock fills; **259 passed**. Gate streak
  through #14. Next scope: near-miss autopsy + scenario re-sim (research, OOS).
- `2026-06-14` — Same chat then ran the **near-miss autopsy** (PR #17): IS said
  "drop 60% / lower target", OOS **refuted it as OVERFIT** (3R correct, 60% gate
  net-positive OOS); only OOS-supported tweak is `--min-pct 0.5→0.6` (modest, shadow-
  test recommended, NOT applied). **User-invoked `/handoff-audit` gate → BOTH #16 and
  #17 PASS** (independent arm's-length subagents in isolated worktrees) and **merged**
  at `8b92ba5`. Self-audit caveat recorded. Gate streak: …#14,#16,#17. Next:
  `--min-pct 0.6` decision (pending user) OR live-executor wiring/testnet OR top-100.
