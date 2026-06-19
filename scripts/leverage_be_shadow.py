"""Tier-1 shadow overlay for the lock+0.1R/≤10x/maker forward test (READ-ONLY).

Design: docs/research/leverage_be_forward_test.md (Tier 1). This is the
ZERO-engine-change, zero-risk first tier of the paper-forward test for the only
non-losing management lane found in docs/research/leverage_be_study.md:

    lock+0.1R @ first-green  ·  zero-fee/maker venue  ·  stop > 0.5%

It does NOT touch the engine, the live path, or data/journal.json. Each run it:
  1. loads the SAME resolved bracket trades the bot already logged,
  2. restricts to the pre-registered subset (zero-fee venue + wider stop),
  3. replays `lock+0.1R@first_green` vs the `original` management over the real
     post-fill bars — reusing scripts/leverage_be_study.py's path engine verbatim
     (no re-implementation, so the numbers can't silently diverge from the study),
  4. scores the rule PAIRED against original at the venue's maker friction, with
     bootstrap CIs, and renders a PASS / INCONCLUSIVE / KILL verdict against the
     PRE-REGISTERED thresholds below, and
  5. writes its report under data/shadow/ (never the journal) and appends one row
     to a history file so the out-of-sample track accumulates as new trades close.

What Tier 1 CAN settle: does the management rule beat original OUT-OF-SAMPLE as
new trades resolve, and does it stay solvent at the ≤10x liquidation band.
What it CANNOT settle (Tier 2 only): maker FILL feasibility (§42) — Tier 1 still
assumes the maker limit fills at ~0 fee. That assumption is the whole edge, so the
verdict here is necessary-but-not-sufficient and says so.

Run:  PYTHONPATH=. python scripts/leverage_be_shadow.py
      PYTHONPATH=. python scripts/leverage_be_shadow.py --csv pairs.csv --json out.json
      PYTHONPATH=. python scripts/leverage_be_shadow.py --crypto-maker   # +optimistic lane

Honesty rails (project thesis): pre-register success BEFORE looking; report the
n-gate honestly; never call it validated on Tier 1 alone.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

# Reuse the study's path-replay + simulation ENGINE verbatim (no duplication).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from leverage_be_study import (  # noqa: E402
    TF_MIN, VARIANTS, build_path, friction_r, liquidated, sim_policy,
)

from kudbee_quant.ingest import RouterClient            # noqa: E402
from kudbee_quant.journal.journal import (              # noqa: E402
    DEFAULT_PATH, Prediction, venue_of,
)

# ----------------------------------------------------------------------------
# PRE-REGISTRATION — fixed BEFORE collecting data (see the design doc). Changing
# these after seeing results is fitting; don't. They mirror the spec 1:1.
# ----------------------------------------------------------------------------
RULE = "lock+0.1R@first_green"   # the one candidate (be_trigger=first-green, be_level=+0.1R)
BASELINE = "original"            # stop stays at -1R, the engine's current management
STOP_MIN_PCT = 0.5               # exclude sub-0.5% scalps (friction eats them)
N_MIN = 150                      # below this -> INCONCLUSIVE, keep paper-collecting
CI_ALPHA = 0.10                  # 90% bootstrap CIs (matches the FDR alpha in events/study.py)
KILL_ROLLING_N = 100             # rolling window for the drawdown kill
KILL_ROLLING_R = -0.10           # rule net over any rolling-100 below this -> KILL
KILL_FILL_RATE = 0.60            # Tier-2 kill (maker fill rate); NOT measurable in Tier 1
MAX_LEVERAGE = 10                # leverage cap; the study (§8/10) found ~1% liq here, not 0
KILL_LIQ_PCT = 0.02              # KILL if liq rate MATERIALLY exceeds the study's ~1% baseline
MAKER_MODEL = "low"             # the zero-fee/maker friction model in leverage_be_study.FRICTION

SHADOW_DIR = os.path.join(os.path.dirname(DEFAULT_PATH), "shadow")
HISTORY_CSV = os.path.join(SHADOW_DIR, "leverage_be_shadow_history.csv")


def boot_ci(vals, alpha=CI_ALPHA, n_boot=5000, seed=11):
    """Mean and a (1-alpha) bootstrap CI of a sample (NaNs dropped)."""
    a = np.array([v for v in vals if v == v], dtype=float)
    if len(a) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = a[rng.integers(0, len(a), size=(n_boot, len(a)))].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(a.mean()), float(lo), float(hi)


def _resolved_sorted(trades):
    """Resolved bracket trades in resolution order (for the rolling-DD kill)."""
    res = [p for p in trades if p.status in ("hit", "miss") and p.kind == "bracket"]
    return sorted(res, key=lambda p: p.resolved_at or p.created_at or "")


def evaluate(lane_label, paths, hold_days):
    """Paired rule-vs-baseline net expectancy for one venue lane + verdict inputs."""
    rule_net, base_net, deltas, liq = [], [], [], 0
    for t in paths:
        hd = hold_days[id(t)]
        g_rule = sim_policy(t, **VARIANTS[RULE])
        g_base = sim_policy(t, **VARIANTS[BASELINE])
        fr = friction_r(t, MAKER_MODEL, hd)
        nr, nb = g_rule - fr, g_base - fr
        rule_net.append(nr)
        base_net.append(nb)
        deltas.append(nr - nb)
        if liquidated(t, MAX_LEVERAGE):
            liq += 1
    rule_mean, rule_lo, rule_hi = boot_ci(rule_net)
    d_mean, d_lo, d_hi = boot_ci(deltas)

    # rolling-100 worst window on the rule's net (resolution-ordered)
    worst_roll = float("nan")
    arr = np.array([v for v in rule_net if v == v])
    if len(arr) >= KILL_ROLLING_N:
        cs = np.cumsum(np.insert(arr, 0, 0.0))
        rolls = (cs[KILL_ROLLING_N:] - cs[:-KILL_ROLLING_N]) / KILL_ROLLING_N
        worst_roll = float(rolls.min())

    return {
        "lane": lane_label, "n": len(paths),
        "rule_net_mean": rule_mean, "rule_net_ci": [rule_lo, rule_hi],
        "base_net_mean": float(np.nanmean(base_net)) if base_net else float("nan"),
        "delta_mean": d_mean, "delta_ci": [d_lo, d_hi],
        "n_liquidated_at_cap": liq, "pct_liquidated": liq / len(paths) if paths else float("nan"),
        "worst_rolling100_net": worst_roll,
    }


def verdict(ev):
    """PASS / KILL / INCONCLUSIVE against the pre-registered thresholds."""
    reasons = []
    if ev["n"] < N_MIN:
        return "INCONCLUSIVE", [f"n={ev['n']} < pre-registered N_MIN={N_MIN}; keep collecting"]
    killed = False
    if ev["pct_liquidated"] == ev["pct_liquidated"] and ev["pct_liquidated"] > KILL_LIQ_PCT:
        killed = True
        reasons.append(f"liq rate {100*ev['pct_liquidated']:.1f}% at ≤{MAX_LEVERAGE}x "
                       f"> kill {100*KILL_LIQ_PCT:.0f}% (study baseline ~1%); risk model broken")
    wr = ev["worst_rolling100_net"]
    if wr == wr and wr < KILL_ROLLING_R:
        killed = True
        reasons.append(f"worst rolling-{KILL_ROLLING_N} net {wr:+.3f}R < kill {KILL_ROLLING_R:+.2f}R")
    if killed:
        return "KILL", reasons
    primary = ev["rule_net_ci"][0] > 0                 # rule net CI strictly > 0
    improve = ev["delta_ci"][0] > 0                    # paired improvement CI strictly > 0
    if primary and improve:
        return "PASS", ["rule net expectancy significantly > 0 AND beats original (paired CI excludes 0)"]
    if not primary:
        reasons.append(f"rule net CI lower bound {ev['rule_net_ci'][0]:+.3f}R not > 0")
    if not improve:
        reasons.append(f"paired improvement CI lower bound {ev['delta_ci'][0]:+.3f}R not > 0")
    return "INCONCLUSIVE", reasons


def main(argv):
    trades = [Prediction(**d) for d in json.loads(DEFAULT_PATH.read_text())]
    res = _resolved_sorted(trades)

    client = RouterClient()
    klcache: dict = {}
    print(f"[shadow] building paths for {len(res)} resolved bracket trades "
          f"(read-only; journal untouched)...", file=sys.stderr)
    paths = []
    for i, p in enumerate(res):
        tp = build_path(p, client, klcache)
        if tp is not None and tp.has_path and len(tp.rhi) > 0:
            paths.append(tp)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(res)}", file=sys.stderr)

    # ---- pre-registered subset: zero-fee venue + wider stop ----------------
    wide = [t for t in paths if t.stop_pct > STOP_MIN_PCT]
    tradfi = [t for t in wide if venue_of(t.p) == "tradfi"]   # genuinely ~0-fee book
    crypto_maker = [t for t in wide if venue_of(t.p) == "crypto"]  # ASSUMES maker fills

    hold_days = {id(t): (t.bars_to.get("1.00") or len(t.rhi)) * TF_MIN.get(t.p.timeframe, 60) / 1440
                 for t in paths}

    print("\n" + "=" * 78)
    print("TIER-1 SHADOW OVERLAY — lock+0.1R @ first-green, zero-fee/maker, stop>0.5%")
    print("=" * 78)
    print(f"\nPre-registered: RULE={RULE}  vs  {BASELINE}; stop>{STOP_MIN_PCT}%; "
          f"N_MIN={N_MIN}; {int((1-CI_ALPHA)*100)}% CIs; "
          f"kill if rolling-{KILL_ROLLING_N} net<{KILL_ROLLING_R:+.2f}R or liq>{100*KILL_LIQ_PCT:.0f}% at ≤{MAX_LEVERAGE}x.")
    print(f"Subset of {len(paths)} usable paths: {len(tradfi)} zero-fee (tradfi), "
          f"{len(crypto_maker)} crypto (maker-assumed), after stop>{STOP_MIN_PCT}% filter.")

    # ---- PRIMARY lane: the genuinely zero-fee book -------------------------
    lanes = [("zero-fee venue (tradfi, PRIMARY)", tradfi)]
    if "--crypto-maker" in argv:
        lanes.append(("crypto maker-assumed (SECONDARY, optimistic)", crypto_maker))

    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "lanes": [], "csv_pairs": None}
    primary_ev = None
    for label, lane in lanes:
        if not lane:
            print(f"\n[{label}] no trades in subset yet.")
            continue
        ev = evaluate(label, lane, hold_days)
        v, reasons = verdict(ev)
        ev["verdict"], ev["verdict_reasons"] = v, reasons
        out["lanes"].append(ev)
        if primary_ev is None:
            primary_ev = ev
        print(f"\n[{label}]  n={ev['n']}")
        print(f"    rule  net expectancy {ev['rule_net_mean']:+.3f}R  "
              f"90% CI [{ev['rule_net_ci'][0]:+.3f}, {ev['rule_net_ci'][1]:+.3f}]")
        print(f"    orig  net expectancy {ev['base_net_mean']:+.3f}R")
        print(f"    rule−orig (paired)   {ev['delta_mean']:+.3f}R  "
              f"90% CI [{ev['delta_ci'][0]:+.3f}, {ev['delta_ci'][1]:+.3f}]")
        print(f"    liquidations at ≤{MAX_LEVERAGE}x: {ev['n_liquidated_at_cap']} "
              f"({100*ev['pct_liquidated']:.0f}%)   worst rolling-{KILL_ROLLING_N} net: "
              f"{ev['worst_rolling100_net']:+.3f}R")
        print(f"    >>> VERDICT: {v}  — {'; '.join(reasons)}")

    print("\n" + "-" * 78)
    print("TIER-1 LIMITS (honest): this assumes the maker limit FILLS at ~0 fee — the "
          "make-or-break (§42) it cannot test. Maker fill rate (<{:.0f}% = kill) and real "
          "alt slippage are TIER-2 only. A PASS here is necessary, not sufficient."
          .format(KILL_FILL_RATE * 100))
    print("Not financial advice. Read-only shadow analysis — no live or journal changes.")

    # ---- artifacts: under data/shadow/, NEVER data/journal.json ------------
    os.makedirs(SHADOW_DIR, exist_ok=True)
    if "--csv" in argv:
        import csv
        cp = argv[argv.index("--csv") + 1]
        with open(cp, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "symbol", "venue", "timeframe", "stop_pct",
                        "rule_net_r", "orig_net_r", "delta_r", "liq_at_cap"])
            for t in tradfi + (crypto_maker if "--crypto-maker" in argv else []):
                hd = hold_days[id(t)]
                fr = friction_r(t, MAKER_MODEL, hd)
                nr = sim_policy(t, **VARIANTS[RULE]) - fr
                nb = sim_policy(t, **VARIANTS[BASELINE]) - fr
                w.writerow([t.p.id, t.p.symbol, venue_of(t.p), t.p.timeframe,
                            round(t.stop_pct, 4), round(nr, 4), round(nb, 4),
                            round(nr - nb, 4), liquidated(t, MAX_LEVERAGE)])
        out["csv_pairs"] = cp
        print(f"[shadow] wrote paired table -> {cp}", file=sys.stderr)

    if "--json" in argv:
        jp = argv[argv.index("--json") + 1]
    else:
        jp = os.path.join(SHADOW_DIR, "leverage_be_shadow.json")
    with open(jp, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[shadow] wrote report -> {jp}", file=sys.stderr)

    # append one history row so the OOS track accumulates run-over-run
    if primary_ev is not None:
        new = not os.path.exists(HISTORY_CSV)
        import csv
        with open(HISTORY_CSV, "a", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["generated_at", "lane", "n", "rule_net_mean", "rule_ci_lo",
                            "delta_mean", "delta_ci_lo", "pct_liquidated",
                            "worst_rolling100", "verdict"])
            w.writerow([out["generated_at"], primary_ev["lane"], primary_ev["n"],
                        round(primary_ev["rule_net_mean"], 4), round(primary_ev["rule_net_ci"][0], 4),
                        round(primary_ev["delta_mean"], 4), round(primary_ev["delta_ci"][0], 4),
                        round(primary_ev["pct_liquidated"], 4),
                        round(primary_ev["worst_rolling100_net"], 4), primary_ev["verdict"]])
        print(f"[shadow] appended OOS history row -> {HISTORY_CSV}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
