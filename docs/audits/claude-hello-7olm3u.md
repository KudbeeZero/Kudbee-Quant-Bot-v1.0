# Audit: PR #9 — `claude/hello-7olm3u`

- **Verdict:** **PASS** (post-hoc — PR was already merged when this audit ran)
- **Date:** 2026-06-12
- **PR:** https://github.com/KudbeeZero/Kudbee-Quant-Bot-v1.0/pull/9 — state **MERGED**
  (2026-06-12T01:48:09Z, by KudbeeZero), base `b28c483a`, head `6c8116b4`,
  10 files, +1082/−75.
- **Auditor:** independent subagent (fresh eyes; verified against the diff and
  live code, not the PR body).
- **Tests:** **191 passed, 0 failed** — reproduced live (`python -m pytest -q`;
  needed `pip install pytest fastapi httpx psutil` + `-r requirements.txt` in
  the sandbox; suite total verified by progress dots + exit 0 because the final
  summary line was suppressed). 183 inherited + 8 new arithmetic checks out.

## Process anomalies (recorded, not blocking)

1. **The gate half-fired.** The merge commit (`8b1677e`) claims "Independent
   audit gate PASS — report to follow in `docs/audits/claude-hello-7olm3u.md`",
   but that report was never committed and the baton was left at
   `AWAITING_AUDIT`. The prior audit session evidently merged and then died
   before landing its artifacts. THIS file is the report, produced by a fully
   independent re-audit (not a recovery of the lost one).
2. **No CI on the head commit.** `6c8116b` is a `[skip ci]` baton commit —
   0 check runs, 0 statuses — so the "CI green" leg of the gate had no
   evidence at merge time. Mitigated post-hoc by the live 191/191 run above.

## Claim-by-claim findings (evidence = diff `b28c483a..6c8116b4` + live code)

1. **PR #7 post-hoc audit file — CONFIRMED.** `docs/audits/claude-hello-1lje1b-posthoc.md`
   new (65 lines, PASS verdict on PR #7).
2. **MEMORY §32 — CONFIRMED.** `docs/MEMORY.md:956-986`: 0 unique trade IDs
   across 11 branches; exactly 7 delete-safe + 4 held, matching the claim.
3. **Dashboard salvage + fixes — CONFIRMED, every sub-claim.** Origin zcash
   `6632c48` verified. The "imagined fields" claim is real: the old file used
   `n_resolved`/`n_wins` (old:405-407,438), `counts.win/loss` (old:415-416),
   numeric `resolved_series` (old:499-504), `tag-${t.status}` injection
   (old:476), and zero `esc(` calls. The new
   `kudbee_quant/static/dashboard.html` uses the real contract
   (`counts.hit/miss/cancelled` :422-424; `n/hits/total_r/net_total_r`
   :413-416; `v.r` :512-513 — matching `kudbee_quant/journal/journal.py:262-276,
   149, 206, 322-328` and `kudbee_quant/exposure.py:42`), `esc()` :398,
   `statusCls` allowlist :400, net-of-fee headline :429-431, bot-vs-human
   chips :449-454. ZEC pieces NOT brought over (no universe/workflow/backtest/
   CSV in the diff; WATCHLIST :577-580 is 10 symbols, no ZEC).
4. **`api.py` scope — CONFIRMED** (nit: "2 imports" undercounts — 4 import
   lines touched, plus the `token` field on `AlertPayload`; all within the
   stated units). Nothing else in the `api.py` diff.
5. **`api_security.py` — CONFIRMED.** `check_token` extracted; `require_token`
   delegates to it; `hmac.compare_digest` and 503-when-unconfigured retained
   verbatim.
6. **Triple-channel alert auth — CONFIRMED.** `check_token(x_api_token or
   token or a.token)` (`api.py:144`); `/api/paper/scan` still header-only via
   `Depends(require_token)`, unchanged.
7. **Provenance + zero-direction — CONFIRMED.** `source="human"` (`api.py:158`);
   at the base SHA `direction: 0` coerced to SHORT and `Prediction.source`
   defaulted to `"bot"` (`journal.py:61`); now `direction == 0` → 422
   (`api.py:145-146`).
8. **Alert tests — CONFIRMED.** Exactly +4; the secret-leak assertion
   genuinely re-reads the journal file (`"testtoken" not in jpath.read_text()`)
   and asserts `predictions[-1].source == "human"`.
9. **Dashboard tests — CONFIRMED with one honesty nit.** 4 items; cited line
   numbers accurate. Nit: `test_dashboard_reads_real_journal_fields` is a
   string-pin on the served HTML (asserts `net_total_r` present,
   `n_resolved`/`n_wins` absent) — it does not execute against `journal.py`
   output, so "guarding the contract" is slightly generous. It does prevent
   the exact regression described.
10. **Deps — CONFIRMED.** `requirements.txt` +psutil only; `pyproject.toml`
    +package-data for `static/*.html`.
11. **Journal — CONFIRMED, stronger than claimed.** Zero commits in the PR
    range touch `data/journal.json` (not even bot commits).
12. **Tests — REPRODUCED.** 191/191, see header.

## Security review (new surface)

- **Token in query string:** real but disclosed risk — the endpoint docstring
  (`api.py:131-133`) warns query strings hit access logs and recommends the
  body channel. Accepted, documented TradingView trade-off. (HTTPS hosting —
  next chat's scope — is the real mitigation.)
- **XSS:** `esc()` coverage genuinely complete for journal-derived strings.
  One defense-in-depth gap: `dashboard.html:614` interpolates `e.message`
  into innerHTML unescaped (low risk — `apiFetch` throws `Error(r.status)`,
  numeric, never server-body-derived), so the absolute "every server-derived
  string" claim has this one inconsistency.
- **Constant-time / fail-closed:** retained; 401 paths covered by tests.
- **`/api/metrics` unauthenticated:** exposes host CPU/mem/disk to anyone
  reaching the API (read-rate-limited only). Minor info disclosure, consistent
  with the other read endpoints; worth a thought when hosting.
- **Pre-existing (NOT this PR):** `/api/journal` (`api.py:84`) has no
  rate-limit dependency, while the new GET routes do.
- **No secrets in the diff** (only the `"testtoken"` test literal and a
  placeholder).

## Scope creep

None. Only other file is `docs/HANDOFF.md` (protocol baton). The TV-webhook
unit being absorbed into this PR was user-directed and disclosed in both the
PR body and the head commit message.

## Rationale

Every claim reproduced from the diff and live code — including the
unflattering parts (query-token risk, salvage provenance) being disclosed
rather than hidden — with 191/191 tests passing; the only findings are a
one-line escaping inconsistency and slightly generous wording on the test
"guard," neither of which would have blocked merge.
