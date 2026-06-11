# Taint audit: pre-fix `_tradfi` journal entries (§29/§30 follow-up)

- **Date:** 2026-06-11 · **Branch:** `claude/hello-1lje1b`
- **Tool:** `scripts/taint_audit.py` (committed; rerunnable)
- **Question:** which TradFi trades logged before PR #5 merged
  (2026-06-10T14:59:38Z) would NOT have signalled under fixed (stub-gated)
  levels?
- **Journal untouched** — this is a report; the hourly bot owns
  `data/journal.json`.

## Method

Each pre-fix entry's signal bar is replayed through the live pipeline
(`build_levels` → `confluence_score` → 50% threshold → `_tf` HTF gate) twice on
the SAME bars (history truncated to the signal hour):

- **FIXED** — today's code (`complete_period_mask` active).
- **PRE-FIX** — the mask monkeypatched to all-True at both import sites
  (`levels/builder`, `context/mm_cycle`), emulating pre-§29 level math.

**Patch sanity check (it really bites):** on the same GC=F 600-bar window the
pre-fix variant changes `pivot_pp` on 92/600 bars — exactly the Monday bars
(2026-05-11/18, 06-01/08) — and biases ADR −2.1% (105.90 vs 108.16). The
mask-off emulation is provably active; null results below are real.

**Replay limit (disclosed):** the Yahoo synthetic tick row the old code scored
on was a live last-quote pseudo-bar; it no longer exists in history. The replay
scores the signal hour's bar in its final form under BOTH variants, so the
comparison isolates the level-mask component; live-edge effects (tick row +
mid-hour bar state) show up as NOT_REPRODUCED instead.

## Result: 0 TAINTED · 5 CLEAN · 3 NOT_REPRODUCED (of 8)

| id | symbol | created (UTC) | status | R | pre-fix replay | fixed replay | changed votes | verdict |
|---|---|---|---|---|---|---|---|---|
| 2780a262 | YAHOO:GC=F | 2026-06-09T16:07 | cancelled | None | 60% dir -1 ✓sig | 60% dir -1 ✓sig | none | **CLEAN** |
| fb05eb7b | YAHOO:SI=F | 2026-06-09T16:07 | hit | 3.0 | 50% dir -1 ✓sig | 50% dir -1 ✓sig | none | **CLEAN** |
| 3ad76ca0 | YAHOO:CL=F | 2026-06-09T16:07 | miss | -1.0 | 50% dir -1 ✓sig | 50% dir -1 ✓sig | none | **CLEAN** |
| 9738b4de | YAHOO:BZ=F | 2026-06-09T16:07 | miss | -1.0 | 50% dir -1 ✓sig | 50% dir -1 ✓sig | none | **CLEAN** |
| 0486656e | YAHOO:BZ=F | 2026-06-10T03:55 | miss | -1.0 | 40% dir -1 | 40% dir -1 | none | **NOT_REPRODUCED** |
| bcb4fbe4 | YAHOO:CL=F | 2026-06-10T08:11 | miss | -1.0 | 40% dir -1 | 40% dir -1 | none | **NOT_REPRODUCED** |
| 7d2cce27 | YAHOO:GC=F | 2026-06-10T12:23 | miss | -1.0 | 60% dir -1 ✓sig | 60% dir -1 ✓sig | none | **CLEAN** |
| 013d82a2 | YAHOO:NG=F | 2026-06-10T12:23 | miss | -1.0 | 40% dir +1 | 40% dir +1 | none | **NOT_REPRODUCED** |

## Reading

1. **No entry was level-tainted.** At all 8 signal bars the mask changes ZERO
   votes — pre-fix and fixed replays are vote-for-vote identical. This is
   exactly what §30's mechanism predicts: the stub poisoning feeds **Monday**
   pivots/PDH-PDL (from the Sunday Globex stub), and all 8 pre-fix entries were
   logged on **Tuesday 06-09 / Wednesday 06-10**, whose prior-day levels come
   from full sessions. The 33–75% Monday-flip hotspot (§30) never coincided
   with a logged trade — the bot's TradFi book only started 06-09 (a Tuesday).
   ADR was biased on those days too (−2.1% on GC=F here; −6–17% in §29/§30
   measurements), but ADR feeds `adr_high/low` levels, not any confluence vote,
   so it could not flip a signal.
2. **The 3 NOT_REPRODUCED entries are live-edge artifacts, not level taint.**
   Replayed on completed bars they score 40% — below the 50% gate — under BOTH
   variants. Their recorded signals existed only in the bot's live view:
   the §29 synthetic tick row (then present) and/or the in-progress hour bar's
   mid-hour state. The tick-row component is fixed; mid-hour scanning on the
   in-progress bar is still the bot's behavior today (by design — signals fire
   intra-hour). All 3 were `miss` (−1R each), consistent with sub-threshold
   signals having no edge, but n=3 proves nothing.
3. **Scorecard impact: none worth adjusting.** The only profitable pre-fix
   trade (SI=F +3R) is CLEAN — it would have signalled under fixed levels too.
   The 4 losses among CLEAN/NOT_REPRODUCED stay in the record as-is; we do not
   retro-edit outcomes (§ journal is bot-owned, and removing reproducible-loss
   entries would be exactly the kind of survivorship cleanup the project
   forbids).
4. **§29's `filled_at` caveat stands** (visible in the data: e.g. `2780a262`
   is `cancelled` yet carries a `filled_at` seconds after creation — a pre-fix
   false-fill stamp). Statuses/outcomes fine, fill TIMES unreliable ≤
   2026-06-10.

## Verdict

The pre-fix `_tradfi` book is **untainted at the signal level**: no trade owes
its existence to stub-poisoned levels. The taint window closed before any
Monday trade was logged. The forward record can be read without exclusions;
the three sub-threshold live-edge entries are noted, not excised.
