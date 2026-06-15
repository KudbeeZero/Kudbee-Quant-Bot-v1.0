# PR #21 audit — Gated admin/investor dashboard (login, Tailwind, curated runner)

- **Verdict:** **PASS** (post-hoc — PR was merged from the UI before this gate ran)
- **Date:** 2026-06-15
- **Auditor:** independent `general-purpose` subagent (arm's-length; verified the diff, not the claims)
- **PR:** [#21](https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/21) — **MERGED** by KudbeeZero at `c4d9cd9`
- **Range audited:** `8568c03..c4d9cd9` (base.sha..head.sha from the GitHub API, not `main...branch`)
- **Tests:** `python -m pytest` → **322 passed**, 0 failed (1 deprecation warning). +17 new tests present and substantive (`test_api_auth.py` = 10, `test_api_runner.py` = 7).

## Why this is a post-hoc record
PR #21 was merged from the GitHub UI during a user-directed "get the PRs back on track"
cleanup, **without** the usual independent `/handoff-audit` gate. This report is the
arm's-length review the protocol owes it; it is a record, not a merge decision. Verdict
is PASS, so nothing to fix-forward.

## Findings (each with diff evidence)

### Fail-closed auth — SUPPORTED
- Unset password ⇒ 503: `api_auth.py:73-74` (`check_password` raises 503 when `_password()` is None); test `test_login_disabled_when_unset`.
- Wrong password ⇒ 401 via constant-time compare: `api_auth.py:75-76` uses `hmac.compare_digest`; test `test_login_rejects_bad_password`.
- Cookie HttpOnly/Secure/SameSite=Lax, 12h: `api.py:480-481` (`httponly=True, secure=True, samesite="lax"`), `DEFAULT_MAX_AGE = 12*3600` at `api_auth.py:35`.
- Login rate-limited 5/min: `api.py:77` (`RateLimiter(limit=5, window=60, scope="login")`) wired at `api.py:477`; test `test_login_rate_limited`.

### Gate is real — SUPPORTED
- `/` and `/dashboard` 302→/login without session: `api.py:504-510`; test `test_dashboard_redirects_without_cookie`.
- Gated APIs 401 without session: `/api/open-trades` (`api.py:359`), `/api/trade-history` (382), `/api/research` (399), `/api/run*` (431/437/452) all `Depends(require_session)`; tests `test_gated_api_requires_session` + `test_runner_requires_session`.

### HMAC session verification (security focus) — SOLID
- Signature actually recomputed and checked, not merely parsed: `api_auth.py:111-113` (`hmac.new(key, raw, sha256)` + `compare_digest`). Constant-time is real.
- Expiry + issuer enforced: `api_auth.py:117` (`exp > now`), `:115` (`iss`). Tests `test_expired_session_is_rejected`, `test_tampered_cookie_is_rejected`.
- Fail-closed key: no secret ⇒ `_signing_key()` returns `b""` ⇒ `verify_session` False (`api_auth.py:62,105`).
- Minor (not a defect): with no dedicated `KUDBEE_SESSION_SECRET`, the key derives from the password (`api_auth.py:58-61`), so a password rotation invalidates sessions — documented in `render.yaml`, acceptable.

### Runner is NOT RCE — SUPPORTED
- Fixed-dict whitelist dispatch `_ACTIONS` (`api_runner.py:235-242`); unknown action ⇒ **404** (`api.py:461-462`); test `test_runner_rejects_unknown_action`.
- Bad/OOB params ⇒ 422: pydantic bounds (`api_runner.py:69-118`), symbols via `parse_spec` whitelist (`_norm_spec`, 50-56) — guards SSRF/traversal; test `test_runner_rejects_bad_params` (`../../etc`, `limit:999999`).
- Busy ⇒ 429: `api_runner.py:287-288` + `api.py:463-464`; `ThreadPoolExecutor(max_workers=2)`. No shell/eval/exec anywhere — actions call importable engine functions only.

### Journal safety (load-bearing) — SUPPORTED
- `paper_scan(dry_run=True)` writes nothing: `paper/paper.py:140-141` (`p = pred if dry_run else j.add(pred)`); runner calls dry-run only (`api_runner.py:226`). Test `test_paper_scan_dry_run_never_writes_journal` asserts no Prediction added AND file not written, with a positive control that `dry_run=False` persists.

### No forbidden edits — SUPPORTED
- `config/validated_defaults.py` (§1), `data/journal.json`, `data/alert_inbox/` NOT in the diff. `FEE_PCT` only in docs prose, never code-edited. No hardcoded secrets; read via `get_secret` and declared `sync: false` in `render.yaml`.

### CSP / static — SUPPORTED
- Strict CSP `script-src 'self'` (no inline, no CDN): `api.py:54-56,60-68`. Dashboard/login JS externalized to `/static/app.js` + `/static/login.js`; zero inline `<script>` bodies / `onclick`/`onload`/`onsubmit` handlers.
- Tailwind compiled+committed: `kudbee_quant/static/app.css` (real compiled output) + `assets/css/app.css`; `node_modules/` gitignored.

### Scope — CLEAN
All changes dashboard-scoped (auth/runner/gating, static assets, Tailwind build, `render.yaml` env vars, robots.txt, docs). No unrelated engine/strategy changes.

## Minor nits (non-blocking)
- `api_runner.py:5` docstring says unknown action ⇒ 422; wired behavior + test are 404. Doc-only inconsistency.
- Job watchdog marks timed-out jobs failed but cannot kill the underlying thread — disclosed in the module docstring (acceptable for a single-operator tool).

## Caveats carried forward (not defects — they are open risks)
- **Never deployed to the real Render host** — verified locally only. (Partly addressed since by PR #25 deploy-prep; still no live smoke-test of the full login→dashboard→runner flow on a real host.)
- Runner results are **ephemeral** (in-memory; gone on redeploy).
- **Three CSP sources of truth** (`netlify.toml`, `_headers`, the FastAPI header) — keep in sync; Netlify CSP still has `unsafe-inline` on the marketing pages.
