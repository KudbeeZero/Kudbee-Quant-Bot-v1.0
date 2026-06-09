"""L6 — the multiple-testing ledger: re-grade every "winner" under the multiplicity
of everything we have ever tried.

After ~60+ candidate filters, a few will clear "ΔR > +0.015 in both halves" by
LUCK alone. This is the deflated-Sharpe / false-discovery problem (López de Prado;
Benjamini-Hochberg). This module reads the experiment log (L3,
``data/overnight_results.json``), computes for each candidate an approximate
two-sample significance of its expectancy edge over the baseline, applies
family-wide BH-FDR control, and reports how many "winners" survive multiplicity.

HONEST APPROXIMATION (stated loudly): the experiment log stores per-candidate
expectancy, win-rate and trade count — NOT the full per-trade R arrays. We
therefore estimate each per-trade R variance from its win-rate under a two-point
{-1R, +target_r} model (a known approximation that ignores mark-to-close and
partial exits). The resulting p-values are indicative, not exact; the honest use
is RELATIVE — "do the winners survive when the whole family is accounted for?" —
not a precise p. For an exact test, recompute from pooled trade arrays.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..events.study import benjamini_hochberg

RESULTS_PATH = Path("data/overnight_results.json")
DEFAULT_TARGET_R = 3.0


def _two_point_var(win_rate: float, target_r: float, mean: float) -> float:
    """Variance of a per-trade R under the two-point {-1, +target_r} model."""
    w = min(max(win_rate, 1e-6), 1 - 1e-6)
    return w * (target_r - mean) ** 2 + (1 - w) * (-1.0 - mean) ** 2


def _norm_sf(z: float) -> float:
    """Upper-tail standard-normal survival (two-sided p = 2*sf(|z|))."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def family_ledger(results_path: Path | str = RESULTS_PATH,
                  target_r: float = DEFAULT_TARGET_R, alpha: float = 0.10) -> dict:
    """Re-grade the experiment family. Returns a dict with per-candidate rows
    (approx p-value, BH significance) and a family summary."""
    path = Path(results_path)
    if not path.exists():
        return {"error": f"no experiment log at {path}", "rows": [], "summary": {}}
    data = json.loads(path.read_text())
    latest = {r["name"]: r for r in data.get("results", [])}   # last record per name

    rows = []
    for name, r in latest.items():
        n_c, n_b = r.get("n_trades", 0), r.get("base_n", 0)
        if not n_c or not n_b:
            continue
        delta = r.get("delta", 0.0)
        var_c = _two_point_var(r.get("cand_win", 0.0), target_r, r.get("cand_exp", 0.0))
        var_b = _two_point_var(r.get("base_win", 0.0), target_r, r.get("base_exp", 0.0))
        se = math.sqrt(var_c / n_c + var_b / n_b) or 1e-9
        z = delta / se
        p = 2 * _norm_sf(abs(z))
        rows.append({"name": name, "delta": round(delta, 4), "n": n_c,
                     "z": round(z, 3), "p": round(p, 4),
                     "naive_verdict": r.get("verdict")})

    # Family-wide BH-FDR over every candidate's one-sided-ish edge test.
    pvals = [row["p"] for row in rows]
    flags = benjamini_hochberg(pvals, alpha=alpha) if pvals else []
    for row, sig in zip(rows, flags):
        row["fdr_significant"] = bool(sig) and row["delta"] > 0

    rows.sort(key=lambda x: x["p"])
    naive_winners = [r for r in rows if r["naive_verdict"] == "WINNER"]
    survivors = [r for r in rows if r.get("fdr_significant")]
    # Expected #false discoveries among naive winners if all were null ~ alpha*N.
    summary = {
        "n_candidates": len(rows),
        "naive_winners": len(naive_winners),
        "fdr_survivors": len(survivors),
        "fdr_alpha": alpha,
        "survivor_names": [r["name"] for r in survivors],
        "note": ("Approximate two-point-variance p-values; relative use only. "
                 "A candidate 'survives' if its expectancy edge clears family-wide "
                 "BH-FDR — i.e. it is unlikely to be one of the lucky few among all "
                 f"{len(rows)} tries."),
    }
    return {"rows": rows, "summary": summary}
