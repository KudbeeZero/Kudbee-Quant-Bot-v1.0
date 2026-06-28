#!/usr/bin/env python3
"""Read-only journal report: print all five scorecards and snapshot them to JSON.

Calls, over the resolved trade journal, the five record surfaces —
``scorecard`` (per setup), ``venue_record`` (crypto vs tradfi),
``source_record`` (bot vs human), ``symbol_record`` (per instrument, worst
first) and ``session_record`` (London / NY Overlap / NY / Asia) — prints a
formatted table for each, and writes a machine-readable snapshot to
``data/reports/latest_report.json``.

READ-ONLY: this never mutates ``data/journal.json``; it only reads it (the
bot owns the journal). Run from the repo root::

    python scripts/journal_report.py
    python scripts/journal_report.py --journal data/journal.json --out data/reports/latest_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the package importable when run as a loose script (sys.path[0] is scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from kudbee_quant.journal.journal import TradeJournal  # noqa: E402

DEFAULT_OUT = Path("data/reports/latest_report.json")


def _df_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN/NaT become null via pandas)."""
    return json.loads(df.to_json(orient="records"))


def _print_df(title: str, df: pd.DataFrame) -> None:
    print(f"\n=== {title} ===")
    if df.empty:
        print("(no resolved trades)")
        return
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.float_format", lambda v: f"{v:.4f}"):
        print(df.to_string(index=False))


def _print_dict(title: str, rec: dict) -> None:
    print(f"\n=== {title} ===")
    if not rec:
        print("(no data)")
        return
    rows = []
    for key, vals in rec.items():
        row = {"group": key}
        row.update(vals)
        rows.append(row)
    df = pd.DataFrame(rows)
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.float_format", lambda v: f"{v:.4f}"):
        print(df.to_string(index=False))


def build_report(journal: TradeJournal) -> dict:
    """Compute the five scorecards (+ equity curves) as a JSON-safe snapshot."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scorecard": _df_records(journal.scorecard()),
        "venue_record": journal.venue_record(),
        "source_record": journal.source_record(),
        "symbol_record": _df_records(journal.symbol_record()),
        "session_record": _df_records(journal.session_record()),
        "equity_curve_by_book": journal.equity_curve_by_book(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", type=Path, default=None,
                    help="Path to journal.json (default: TradeJournal default).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"JSON snapshot output path (default: {DEFAULT_OUT}).")
    args = ap.parse_args(argv)

    journal = TradeJournal(path=args.journal) if args.journal else TradeJournal()

    _print_df("SCORECARD (per setup)", journal.scorecard())
    _print_dict("VENUE RECORD (crypto vs tradfi)", journal.venue_record())
    _print_dict("SOURCE RECORD (bot vs human)", journal.source_record())
    _print_df("SYMBOL RECORD (worst net_total_r first)", journal.symbol_record())
    _print_df("SESSION RECORD (UTC)", journal.session_record())

    report = build_report(journal)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(f"\nSnapshot written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
