"""One-time, idempotent retirement of stale-timeframe (2h/4h) zombie positions.

WHY: the 2026-06-19 revert to 1h-only (PR #39) left filled 2h/4h paper positions
open. They predate the breakeven fix (``tp1=None``), get re-managed into stop/
target every hour, and — because ``journal-score`` buckets by ``setup`` (which is
timeframe-agnostic: ``confluence_r_50pct_tf`` is the same label on 1h and 4h) —
they drag the 1h-only forward record once they resolve to hit/miss.

WHAT: mark ONLY the OPEN 2h/4h positions with status ``"flattened"`` — a status no
scoring or equity surface counts. ``scorecard()`` / ``venue_record()`` /
``source_record()`` / ``resolved_series()`` all filter to ``status in ("hit","miss")``,
and ``check_open()`` only re-evaluates ``open``/``pending`` — so a flattened record is
invisible to the record AND is never managed again. ``Prediction.__post_init__``
validates only ``kind`` and rewrites only ``open``->``pending``, so the new status
survives load untouched.

The at-mark R (what each position is worth if closed now) is captured in
``reason_closed`` for the audit trail; ``outcome_r`` stays ``None`` so a mark figure
can never leak into a scored bucket.

HONESTY / SAFETY:
- Deletes nothing; the record count is preserved.
- Idempotent: a second run finds no OPEN 2h/4h positions and writes nothing.
- Edits ``data/journal.json`` as raw JSON (NOT via ``TradeJournal.save``, whose
  ``__post_init__`` + ``check_open`` side-effects would rewrite untouched records),
  so every non-target record stays byte-for-byte identical. The file round-trips
  through ``json.dumps(indent=2)`` with no trailing newline, matching the bot's
  ``save()``.
- Touches ONLY status=="open" AND timeframe in {2h, 4h}. The 6 open 1h positions
  (the active strategy) and all resolved records are left alone.

Usage:
    python -m scripts.flatten_stale_tf            # apply
    python -m scripts.flatten_stale_tf --dry-run  # preview, write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the package importable however this script is invoked (path or -m).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JOURNAL = Path("data/journal.json")
STALE_TFS = {"2h", "4h"}
FLATTEN_TAG = "flatten_stale_tf_2026-06-21"
NEW_STATUS = "flattened"


def _mark_r(client, rec: dict) -> tuple[float | None, float | None]:
    """Return (mark_price, mark_r) for a filled bracket at the current mark, or
    (None, None) if price can't be fetched. mark_r = unrealized R if closed now."""
    try:
        df = client.klines(rec["symbol"], interval=rec["timeframe"], limit=2)
        mark = float(df["close"].iloc[-1])
    except Exception:
        return (None, None)
    entry, stop, direction = rec.get("entry"), rec.get("stop"), rec.get("direction", 0.0)
    if entry is None or stop is None:
        return (mark, None)
    risk = abs(entry - stop)
    if risk <= 0:
        return (mark, None)
    return (mark, direction * (mark - entry) / risk)


def flatten(dry_run: bool = False) -> int:
    """Retire OPEN 2h/4h positions in place. Returns the number changed."""
    records = json.loads(JOURNAL.read_text())
    targets = [r for r in records
               if r.get("status") == "open" and r.get("timeframe") in STALE_TFS]

    if not targets:
        print("No OPEN 2h/4h positions to flatten — already clean (0 changes).")
        return 0

    # Read-only mark fetch (same data path journal-check uses; not live trading).
    from kudbee_quant.ingest import RouterClient
    client = RouterClient()

    now = datetime.now(timezone.utc).isoformat()
    n_mark = 0
    for r in targets:
        mark, mark_r = _mark_r(client, r)
        if mark_r is not None:
            n_mark += 1
            audit = f"mark_r={mark_r:+.3f} @ {mark:.6g}"
        elif mark is not None:
            audit = f"mark={mark:.6g} (risk unavailable)"
        else:
            audit = "mark unavailable"
        r["status"] = NEW_STATUS
        r["resolved_at"] = now
        r["reason_closed"] = (
            f"{FLATTEN_TAG}: retired stale {r['timeframe']} book after 1h-only "
            f"revert (PR #39); excluded from scoring; {audit}")
        # outcome_r intentionally left None — no strategy result is claimed.

        side = "LONG" if r.get("direction", 0) > 0 else "SHORT"
        print(f"  flatten {r['id']} {r['symbol']:<12} [{r['timeframe']}] {side}  {audit}")

    if dry_run:
        print(f"\nDRY RUN — would flatten {len(targets)} positions "
              f"({n_mark} with a mark-R snapshot). Nothing written.")
        return len(targets)

    # Targeted write: re-dump with indent=2 and NO trailing newline (matches the
    # bot's save()), so only the changed records differ in the diff.
    JOURNAL.write_text(json.dumps(records, indent=2))
    print(f"\nFlattened {len(targets)} stale 2h/4h positions "
          f"({n_mark} with a mark-R snapshot). Records preserved: {len(records)}.")
    return len(targets)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="preview the changes without writing the journal")
    args = ap.parse_args()
    flatten(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
