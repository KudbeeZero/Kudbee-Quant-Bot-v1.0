# Audit — streaming commits `0b3560e..ea407a6` (Render→Fly migration + wiring fixes)

**Date:** 2026-07-02
**Scope:** no open PR existed to audit (repo runs the streaming/direct-to-main
workflow; `mcp__github__list_pull_requests(state=open)` returned empty, and
spot-checks of PR #127–#136 via `pull_request_read` confirmed all are genuinely
`merged: true`). This audit instead covers the most recent **unaudited**
direct-to-`main` commit range from this session — the highest-stakes work since
the last formal audit checkpoint (PR #127 / post-hoc #118+#117, 2026-07-01).
**Verdict: PASS** (independent subagent, fresh eyes, did not trust commit
messages — verified every claim against the diff and ran the suite).

## Commits audited
```
30c3a0f fix(site): mobile hero no longer collides the beta pill with the logo/nav
f380ed4 fix(site): wire /api on Cloudflare Pages + honest live-wiring verification
653b1d8 feat(host): move the API from Render to Fly.io + close the data/ privacy leak
ea407a6 board: consolidate Fly deploy + domain + Worker secret into one bring-up checklist
```
(`24841a1`, the bot-owned hourly journal commit interleaved in this range, was
excluded — telemetry only, not part of this session's work.)

## Findings (all confirmed real, not scope-creep, not overstated)
- **Mobile fix** — `assets/css/cinematic.css:97`'s `@media (max-width: 680px)`
  block genuinely overrides the base `.scene--hero` rule (line 66,
  `min-height: 100svh; align-items: center`) with top-aligned flow. Matches
  `index.html:196`.
- **`data/` privacy leak — real bug, real fix.** `functions/data/[[path]].js`
  returns an unconditional 404 for `/data/*`; Cloudflare Pages Functions take
  precedence over static assets by default, no `_routes.json` excludes it, so
  this genuinely shadows the static `data/*.json` files. Confirmed no site JS
  fetches `/data/*` directly (nothing breaks). Confirmed `/api/journal`
  (`kudbee_quant/api.py:246-271`) strips entry/stop/target from open positions
  and the FastAPI app has no route serving the raw file — the stop-hunt/
  front-running vector this closes is accurately characterized, not overstated.
- **`/api/*` proxy** — `functions/api/[[path]].js:24-47` forwards to
  `env.API_ORIGIN || DEFAULT_ORIGIN`, both server-side; not derived from the
  incoming request, so not attacker-controllable — no SSRF vector.
- **Fly deploy workflow is genuinely inert without the secret** —
  `.github/workflows/fly-deploy.yml:34-59` gates every real step on
  `FLY_API_TOKEN` being present via a plain `if/echo` (no `exit 1`), so it's a
  green no-op when unset, as claimed.
- **No scope creep** — every changed file (Dockerfile, fly.toml, .dockerignore,
  the workflow, 2 Pages Functions, netlify.toml, `render.yaml` deletion, 3 docs,
  1 CSS file) is plausibly part of "migrate hosting off Render + fix the two
  wiring gaps found while verifying it." No unrelated Python source touched.
- **MEMORY §80's "HARD-NEGATIVE" framing** (a static host publishing the repo
  root makes `data/` public by default; API-level stripping alone doesn't help)
  is an honest, non-overstated description of the actual bug.
- **Tests:** `python -m pytest -q` → **737 passed, 0 failed, 0 errors** —
  unchanged from the pre-existing count (consistent with this diff touching no
  `kudbee_quant/` Python source).

## Process finding (not a code defect — flagged for the baton reconciliation)
`docs/HANDOFF.md` had not been reconciled since **2026-06-27** despite the
2026-07-02 shift to the streaming workflow and roughly a dozen PRs (#122–#136)
plus several direct-to-`main` commits landing since. The baton still narrated
"this chat = website polish, PR #118" as the live state. Under streaming,
nothing forces a baton update the way a PR-per-chat merge gate did — this audit
reconciles it (see the same-turn `docs/HANDOFF.md` rewrite). No code was at
risk; MEMORY.md and CROSSROADS.md were kept current throughout, so the
narrative gap was in the baton file only.

## Bottom line
No corrective action needed. The commit range holds up under independent
verification — real fixes, accurately described, in scope, tests green.
