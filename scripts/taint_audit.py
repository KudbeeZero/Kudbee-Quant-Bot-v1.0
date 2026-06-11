"""Taint audit of pre-fix `_tradfi` journal entries (MEMORY §29/§30 follow-up).

Every TradFi trade logged before PR #5 merged (2026-06-10T14:59:38Z) was
signalled off levels computed WITHOUT the stub-day gate (`complete_period_mask`)
and WITH Yahoo's synthetic tick row at the live edge. This script replays each
pre-fix entry's signal bar through the confluence pipeline twice on the same
bars:

  FIXED   — the code as it is today (stub-day mask active).
  PRE-FIX — `complete_period_mask` monkeypatched to all-True at both import
            sites (levels/builder, context/mm_cycle), emulating the old
            level computation.

and reports which trades would NOT have signalled under fixed levels.

Replay limits (disclosed, not hidden):
  * The Yahoo tick row the old code scored on was a live last-quote pseudo-bar;
    it no longer exists in history and cannot be reconstructed. The replay
    scores the signal hour's bar in its FINAL form instead, under BOTH
    variants — so the comparison isolates the level-mask component only.
  * The journal is read-only here. Verdicts are a report, not journal edits
    (the hourly bot owns `data/journal.json`).

Usage:  python scripts/taint_audit.py            # human-readable report
        python scripts/taint_audit.py --markdown # markdown table (for docs)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kudbee_quant.confluence.stack import confluence_score, factor_votes  # noqa: E402
from kudbee_quant.ingest import RouterClient  # noqa: E402
from kudbee_quant.levels import build_levels  # noqa: E402

# PR #5 (the §29 fix) merged at 2026-06-10T14:59:38Z; entries created before
# this were signalled by pre-fix code.
PREFIX_CUTOFF = datetime(2026, 6, 10, 14, 59, 38, tzinfo=timezone.utc)
JOURNAL = Path(__file__).resolve().parents[1] / "data" / "journal.json"
MIN_PCT = 0.5          # the scan threshold the bot ran with
SCAN_LIMIT = 600       # bars the bot fed build_levels (paper.py)


def _all_full(counts: pd.Series, min_frac: float = 0.5) -> pd.Series:
    """Pre-fix emulation: every period counts as a full day (no stub gate)."""
    return pd.Series(True, index=counts.index)


class _mask_disabled:
    """Context manager: swap complete_period_mask out at both import sites."""

    def __enter__(self):
        import kudbee_quant.context.mm_cycle as mm
        import kudbee_quant.levels.builder as lb
        self._orig = lb.complete_period_mask
        lb.complete_period_mask = _all_full
        mm.complete_period_mask = _all_full

    def __exit__(self, *exc):
        import kudbee_quant.context.mm_cycle as mm
        import kudbee_quant.levels.builder as lb
        lb.complete_period_mask = self._orig
        mm.complete_period_mask = self._orig


def _score_at(bars: pd.DataFrame, trend_filter: bool) -> dict:
    """Run the paper_scan signal math on the LAST bar of ``bars``."""
    f = build_levels(bars.reset_index(drop=True))
    last = confluence_score(f).iloc[-1]
    votes = factor_votes(f).iloc[-1]
    pct, direction = float(last["confluence_pct"]), float(last["direction"])
    signals = pct >= MIN_PCT and direction != 0
    if signals and trend_filter and last["ema_800"] == last["ema_800"]:
        htf = 1.0 if last["close"] > last["ema_800"] else -1.0
        if direction != htf:
            signals = False
    return {"pct": pct, "direction": direction, "signals": signals,
            "votes": {k: float(v) for k, v in votes.items()}}


def replay(entry: dict, client: RouterClient) -> dict:
    created = pd.Timestamp(entry["created_at"])
    bars = client.klines(entry["symbol"], interval=entry["timeframe"], limit=10_000)
    # Bars the bot could have seen: everything up to (and including) the bar
    # whose hour contains the scan time, in its final form (see module note).
    cut = created.floor(entry["timeframe"])
    seen = bars[bars["timestamp"] <= cut].tail(SCAN_LIMIT)
    if seen.empty or seen["timestamp"].iloc[-1] != cut:
        return {"error": f"no bar at {cut} in fetched history"}
    trend_filter = "_tf" in entry["setup"]
    fixed = _score_at(seen, trend_filter)
    with _mask_disabled():
        prefix = _score_at(seen, trend_filter)
    changed = {k: (prefix["votes"][k], fixed["votes"][k])
               for k in fixed["votes"]
               if prefix["votes"][k] != fixed["votes"][k]}
    rec_dir = float(entry["direction"])
    reproduced = prefix["signals"] and prefix["direction"] == rec_dir
    if reproduced and (not fixed["signals"] or fixed["direction"] != rec_dir):
        verdict = "TAINTED"          # signal existed only because of stub levels
    elif fixed["signals"] and fixed["direction"] == rec_dir:
        verdict = "CLEAN"            # signal survives fixed levels
    else:
        verdict = "NOT_REPRODUCED"   # replay can't recreate the recorded signal
    return {"fixed": fixed, "prefix": prefix, "changed_votes": changed,
            "reproduced": reproduced, "verdict": verdict}


def main() -> None:
    markdown = "--markdown" in sys.argv
    preds = json.loads(JOURNAL.read_text())
    if isinstance(preds, dict):
        preds = preds["predictions"]
    pre_fix = [p for p in preds
               if "_tradfi" in (p.get("setup") or "")
               and datetime.fromisoformat(p["created_at"]) < PREFIX_CUTOFF]
    client = RouterClient()
    rows = []
    for p in sorted(pre_fix, key=lambda x: x["created_at"]):
        r = replay(p, client)
        rows.append((p, r))

    if markdown:
        print("| id | symbol | created (UTC) | status | R | pre-fix replay | fixed replay | changed votes | verdict |")
        print("|---|---|---|---|---|---|---|---|---|")
        for p, r in rows:
            if "error" in r:
                print(f"| {p['id']} | {p['symbol']} | {p['created_at'][:16]} | {p['status']} | "
                      f"{p.get('outcome_r')} | — | — | — | ERROR: {r['error']} |")
                continue
            fx, pf = r["fixed"], r["prefix"]
            cv = ", ".join(f"{k} {a:+.0f}→{b:+.0f}" for k, (a, b) in r["changed_votes"].items()) or "none"
            print(f"| {p['id']} | {p['symbol']} | {p['created_at'][:16]} | {p['status']} | "
                  f"{p.get('outcome_r')} | {pf['pct']:.0%} dir {pf['direction']:+.0f}"
                  f"{' ✓sig' if pf['signals'] else ''} | {fx['pct']:.0%} dir {fx['direction']:+.0f}"
                  f"{' ✓sig' if fx['signals'] else ''} | {cv} | **{r['verdict']}** |")
    else:
        for p, r in rows:
            print(f"\n{p['id']} {p['symbol']} {p['timeframe']} created {p['created_at']} "
                  f"status={p['status']} R={p.get('outcome_r')} setup={p['setup']}")
            if "error" in r:
                print(f"  ERROR: {r['error']}")
                continue
            fx, pf = r["fixed"], r["prefix"]
            print(f"  recorded: dir {p['direction']:+.0f} @ signal_price {p['signal_price']}")
            print(f"  pre-fix replay: pct {pf['pct']:.0%} dir {pf['direction']:+.0f} signals={pf['signals']}")
            print(f"  fixed   replay: pct {fx['pct']:.0%} dir {fx['direction']:+.0f} signals={fx['signals']}")
            if r["changed_votes"]:
                for k, (a, b) in r["changed_votes"].items():
                    print(f"    vote {k}: pre-fix {a:+.0f} -> fixed {b:+.0f}")
            print(f"  VERDICT: {r['verdict']}")
        n = len(rows)
        tainted = sum(1 for _, r in rows if r.get("verdict") == "TAINTED")
        clean = sum(1 for _, r in rows if r.get("verdict") == "CLEAN")
        other = n - tainted - clean
        print(f"\n{n} pre-fix _tradfi entries: {tainted} TAINTED, {clean} CLEAN, "
              f"{other} not reproduced / errored")


if __name__ == "__main__":
    main()
