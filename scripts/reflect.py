"""Run the reflective memory layer (L6): regime state, multiple-testing ledger,
overfit alarms, and the failure rollup. Writes data/reflection.json and appends a
dated note to docs/MEMORY.md.

Usage:  python scripts/reflect.py            # uses BTCUSDT 1h as the regime proxy
        python scripts/reflect.py --no-memory   # don't append to MEMORY.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kudbee_quant.memory.reflection import reflect  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--no-memory", action="store_true", help="don't append to MEMORY.md")
    args = ap.parse_args()

    df = None
    try:
        from kudbee_quant.ingest import load_ohlcv
        from kudbee_quant.levels import build_levels
        df = build_levels(load_ohlcv(args.symbol, interval=args.interval, limit=1000))
    except Exception as exc:           # offline / network: still do the ledger
        print(f"(regime proxy unavailable: {exc})")

    report = reflect(df=df, write_memory=not args.no_memory)
    print(json.dumps({k: report[k] for k in ("generated_at", "regime",
                                             "ledger_summary", "overfit_alarms")}, indent=2))
    print("\nfailure rollup by theme:")
    for theme, c in report["failure_rollup"].items():
        print(f"  {theme:16s} failed={c['failed']}  winner={c['winner']}")


if __name__ == "__main__":
    main()
