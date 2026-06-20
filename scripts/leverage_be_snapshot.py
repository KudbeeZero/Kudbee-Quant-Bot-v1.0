"""Up-to-date snapshot for the break-even report panels (READ-ONLY).

Reuses the leverage_be_study engine (build_path / sim_policy / VARIANTS) to
recompute, on the CURRENT journal, exactly the two figures the report shows:

  Panel A  "BE-ONLY — at +1R move stop to breakeven": total book R under the
           original management vs. moving the stop to BE once a trade is +1R.
  Panel B  "WERE WE EVER IN THE GREEN? — how far stop-outs ran first": the MFE
           distribution of the trades that ULTIMATELY STOPPED OUT (status==miss,
           with a usable bar path).

Writes a JSON blob to the path given by --json (default: stdout). No journal,
engine, or live-path writes. All fetches are read-only OHLCV path rebuilds.

Run:  PYTHONPATH=. python scripts/leverage_be_snapshot.py --json data/be_snapshot.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from kudbee_quant.ingest import RouterClient
from kudbee_quant.journal.journal import DEFAULT_PATH, Prediction

# Reuse the study's engine so the numbers are identical to the full report.
sys.path.insert(0, "scripts")
from leverage_be_study import VARIANTS, build_path, market_class, sim_policy  # noqa: E402

THRESHOLDS = [("green at all", 1e-9), ("> +0.25R", 0.25), ("> +0.50R", 0.50),
              ("> +1.00R", 1.00), ("> +1.50R", 1.50), ("> +2.00R", 2.00)]


def main(argv):
    trades = [Prediction(**d) for d in json.loads(DEFAULT_PATH.read_text())]
    resolved = [p for p in trades
                if p.status in ("hit", "miss") and p.kind == "bracket"]
    client = RouterClient()
    klcache: dict = {}

    print(f"Rebuilding paths for {len(resolved)} resolved bracket trades "
          f"({len(set((p.symbol, p.timeframe) for p in resolved))} series)...",
          file=sys.stderr)
    paths = []
    for i, p in enumerate(resolved):
        tp = build_path(p, client, klcache)
        if tp is not None:
            paths.append(tp)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(resolved)}", file=sys.stderr)

    withp = [t for t in paths if t.has_path and len(t.rhi) > 0]
    n_res, n_path = len(paths), len(withp)
    n_hit = sum(1 for t in withp if t.p.status == "hit")

    # ---- Panel A: BE-only book swing (gross R, summed across the book) -------
    orig = [sim_policy(t, **VARIANTS["original"]) for t in withp]
    be1r = [sim_policy(t, **VARIANTS["BE@+1.00R"]) for t in withp]
    book_orig = float(sum(r for r in orig if r == r))
    book_be1r = float(sum(r for r in be1r if r == r))

    # ---- Panel B: how far did the ultimate stop-outs run first? --------------
    losers = [t for t in withp if t.p.status == "miss"]
    n_lose = len(losers)
    panel_b = []
    for label, thr in THRESHOLDS:
        c = sum(1 for t in losers if t.mfe_r >= thr)
        panel_b.append({"label": label, "count": c, "n": n_lose,
                        "pct": (c / n_lose) if n_lose else None})

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "journal_records": len(trades),
        "resolved_bracket": n_res,
        "with_path": n_path,
        "lacked_coverage": n_res - n_path,
        "win_rate": (n_hit / n_path) if n_path else None,
        "hits": n_hit,
        "panel_a": {
            "book_orig_R": round(book_orig, 1),
            "book_be1r_R": round(book_be1r, 1),
            "per_trade_orig_R": round(book_orig / n_path, 3) if n_path else None,
            "per_trade_be1r_R": round(book_be1r / n_path, 3) if n_path else None,
            "delta_R": round(book_be1r - book_orig, 1),
        },
        "panel_b": {"n_stopped_out": n_lose, "rows": panel_b},
    }

    blob = json.dumps(out, indent=2)
    if "--json" in argv:
        p = argv[argv.index("--json") + 1]
        with open(p, "w") as fh:
            fh.write(blob)
        print(f"Wrote {p}", file=sys.stderr)
    print(blob)


if __name__ == "__main__":
    main(sys.argv[1:])
