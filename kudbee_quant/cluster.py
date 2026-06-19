"""Losing-cluster analyzer — do losing trades CLUSTER, or is it just variance?

Read-only study over ``data/journal.json``. For each context dimension
(time-of-day, day-of-week, confluence gate strength, ATR/volatility regime,
timeframe, direction) it asks: is this bucket's win rate **significantly
different from the book's own baseline** win rate? — using the same
significance-gated harness as the confluence study (``conditional_table``:
Wilson CIs + Benjamini-Hochberg FDR control).

The honesty rules that make this trustworthy:

  * **Win = net-of-fee R > 0** (``net_outcome_r``), over *resolved* trades only
    (status hit/miss). Open/pending/cancelled are excluded.
  * **The null is the OVERALL win rate, not 0.5.** This system wins ~1 in 5 by
    design (asymmetric payoff). Testing each bucket against a coin flip would
    flag *everything*. We test against the book's own unconditional rate, so a
    "losing cluster" means: meaningfully *worse than the system's own average*.
  * **A bucket is flagged ONLY if** it has enough samples (``sufficient``) AND
    survives FDR across all buckets in its dimension (``significant_fdr``) AND
    sits below baseline. If nothing survives, the honest read is **variance, not
    a regime mismatch** — losing streaks are the cost of doing business.
  * **ATR/volatility regime is a PROXY.** We don't refetch OHLCV (offline by
    design); the strategy's stop is ATR-scaled, so stop-distance-% is a faithful
    stand-in for the entry-time volatility regime. Labelled as a proxy, not ATR.

No journal writes. No network. Not financial advice.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from .events.study import StudyConfig, conditional_table
from .journal.journal import DEFAULT_PATH, Prediction, net_outcome_r

_RESOLVED = ("hit", "miss")
_GATE_RE = re.compile(r"(\d+)pct")

# The context dimensions we slice losses by, in report order. Each maps a
# Prediction to a coarse, interpretable bucket label.
DIMENSIONS = ("session", "hour", "day_of_week", "strength", "vol_regime",
              "timeframe", "direction")


def _load_resolved(path: Path) -> list[Prediction]:
    """Resolved bracket predictions, loaded offline (no RouterClient/network)."""
    if not Path(path).exists():
        return []
    preds = [Prediction(**d) for d in json.loads(Path(path).read_text())]
    return [p for p in preds if p.status in _RESOLVED]


def _session(hour: int) -> str:
    """Coarse 6h UTC blocks, labelled by the session that dominates them."""
    return {0: "00-06 Asia", 1: "06-12 Europe", 2: "12-18 US",
            3: "18-24 Late"}[hour // 6]


def _gate_strength(setup: str) -> str:
    """Confluence gate strength parsed from the setup label (50/60/70 pct)."""
    m = _GATE_RE.search(setup or "")
    return f"gate {int(m.group(1)) / 100:.2f}" if m else "other"


def _events_frame(preds: list[Prediction]) -> pd.DataFrame:
    """One row per resolved trade with the context buckets + a boolean ``win``."""
    rows = []
    for p in preds:
        ts = pd.Timestamp(p.created_at)
        net_r = net_outcome_r(p)
        if net_r is None:
            continue
        stop_pct = (abs(p.entry - p.stop) / p.entry * 100.0
                    if p.entry and p.stop and p.entry != 0 else None)
        rows.append({
            "win": bool(net_r > 0),
            "net_r": net_r,
            "session": _session(ts.hour),
            "hour": f"{ts.hour:02d}h",
            "day_of_week": ts.day_name(),
            "strength": _gate_strength(p.setup),
            "timeframe": p.timeframe,
            "direction": "long" if p.direction > 0 else "short" if p.direction < 0 else "flat",
            "_stop_pct": stop_pct,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Volatility-regime PROXY: tercile of ATR-scaled stop distance (% of entry).
    sp = df["_stop_pct"]
    if sp.notna().sum() >= 3 and sp.nunique() >= 3:
        try:
            df["vol_regime"] = pd.qcut(
                sp, 3, labels=["vol:low", "vol:med", "vol:high"], duplicates="drop"
            ).astype("object")
        except ValueError:
            df["vol_regime"] = "vol:n/a"
    else:
        df["vol_regime"] = "vol:n/a"
    df["vol_regime"] = df["vol_regime"].where(sp.notna(), "vol:n/a")
    return df


def losing_cluster_report(
    path: str | Path = DEFAULT_PATH,
    *,
    min_n: int = 20,
    mode: str | None = None,
    fdr_alpha: float = 0.10,
) -> dict:
    """Test whether losing trades cluster by context vs. the book's own baseline.

    Returns a dict: overall stats, one table per dimension (bucket records with
    n, win_rate, Wilson CI, p-value vs baseline, sufficient, significant_fdr,
    lift, mean_net_r, is_losing_cluster), a flat list of flagged losing clusters,
    and honest caveats.
    """
    preds = _load_resolved(Path(path))
    if mode:
        preds = [p for p in preds if p.mode == mode]
    df = _events_frame(preds)

    n_total = len(df)
    if n_total == 0:
        return {"overall": {"n": 0}, "dimensions": {}, "losing_clusters": [],
                "caveats": ["No resolved trades in the journal for this filter."]}

    overall_win_rate = float(df["win"].mean())
    cfg = StudyConfig(min_n=min_n, fdr_alpha=fdr_alpha, null_rate=overall_win_rate)

    dimensions: dict[str, list[dict]] = {}
    clusters: list[dict] = []
    for dim in DIMENSIONS:
        table = conditional_table(df, "win", [dim], cfg)
        if table.empty:
            continue
        means = df.groupby(dim, dropna=False)["net_r"].mean()
        table["mean_net_r"] = table[dim].map(means)
        table["lift"] = table["win_rate"] - overall_win_rate
        table["is_losing_cluster"] = (
            table["sufficient"] & table["significant_fdr"] & (table["lift"] < 0)
        )
        recs = []
        for r in table.to_dict("records"):
            rec = {"dimension": dim, "bucket": r[dim], "n": int(r["n"]),
                   "wins": int(r["wins"]), "win_rate": float(r["win_rate"]),
                   "ci_low": float(r["ci_low"]), "ci_high": float(r["ci_high"]),
                   "p_value": float(r["p_value"]), "lift": float(r["lift"]),
                   "mean_net_r": float(r["mean_net_r"]),
                   "sufficient": bool(r["sufficient"]),
                   "significant_fdr": bool(r["significant_fdr"]),
                   "is_losing_cluster": bool(r["is_losing_cluster"])}
            recs.append(rec)
            if rec["is_losing_cluster"]:
                clusters.append(rec)
        dimensions[dim] = recs

    clusters.sort(key=lambda r: r["lift"])
    caveats = [
        "Win = net-of-fee R > 0; resolved (hit/miss) trades only.",
        f"Null tested = the book's own win rate ({overall_win_rate:.1%}), not 0.5.",
        "vol_regime is a PROXY: terciles of ATR-scaled stop distance %, not refetched ATR.",
        f"Buckets with n < {min_n} are 'insufficient' and never flagged.",
        "A cluster must survive Benjamini-Hochberg FDR across its dimension; "
        "if none do, losses are NOT clustering — it's variance, not a regime mismatch.",
        "FDR is controlled WITHIN each dimension, not across all dimensions — "
        "treat the cross-dimension cluster count as exploratory.",
        "Dimensions overlap (hour/day/direction are correlated), so clusters are "
        "not independent findings; and the journal pools the pre/post VWAP-flip "
        "regimes — these are descriptive associations, not causal claims.",
    ]
    return {
        "overall": {"n": n_total, "win_rate": overall_win_rate,
                    "wins": int(df["win"].sum()), "total_net_r": float(df["net_r"].sum()),
                    "mode": mode or "all", "min_n": min_n, "fdr_alpha": fdr_alpha},
        "dimensions": dimensions,
        "losing_clusters": clusters,
        "caveats": caveats,
    }


def render_cluster_text(rep: dict) -> str:
    """Human-readable report (honest; leads with the variance-vs-mismatch verdict)."""
    o = rep["overall"]
    if o["n"] == 0:
        return "Losing-cluster study: " + (rep["caveats"][0] if rep["caveats"] else "no data.")
    lines = [
        f"Losing-cluster study ({o['n']} resolved, {o['mode']} mode):",
        f"  baseline win rate {o['win_rate']:.1%}  ({o['wins']}/{o['n']})   "
        f"total {o['total_net_r']:+.1f}R net",
    ]
    clusters = rep["losing_clusters"]
    if clusters:
        lines.append(f"\n  VERDICT: {len(clusters)} significant losing cluster(s) "
                     f"— losses concentrate (regime mismatch), not pure variance:")
        for c in clusters:
            lines.append(
                f"    • {c['dimension']}={c['bucket']:<12} n={c['n']:<4} "
                f"win {c['win_rate']:.0%} (base {o['win_rate']:.0%}, "
                f"{c['lift']:+.0%})  mean {c['mean_net_r']:+.2f}R  p={c['p_value']:.3f}")
    else:
        lines.append("\n  VERDICT: no bucket survives FDR — losses do NOT cluster "
                     "beyond chance. This looks like normal variance, not a regime mismatch.")

    for dim, recs in rep["dimensions"].items():
        lines.append(f"\n  [{dim}]  (n / win% / CI / mean R / flag)")
        for r in recs:
            flag = " *LOSING*" if r["is_losing_cluster"] else (
                "" if r["sufficient"] else "  (insufficient)")
            sig = "+" if r["significant_fdr"] else " "
            lines.append(
                f"    {sig} {str(r['bucket']):<14} n={r['n']:<4} "
                f"{r['win_rate']:.0%}  [{r['ci_low']:.0%}-{r['ci_high']:.0%}]  "
                f"{r['mean_net_r']:+.2f}R{flag}")

    lines.append("\nHonest read:")
    for c in rep["caveats"]:
        lines.append(f"  - {c}")
    lines.append("Not financial advice.")
    return "\n".join(lines)
