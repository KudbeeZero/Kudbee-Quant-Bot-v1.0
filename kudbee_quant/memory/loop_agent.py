"""L7 — the self-improving decision loop (the layer that grades its own calls).

The other six layers OBSERVE and JUDGE a snapshot; none of them run on a cadence
and then CHECK, later, whether their own judgments held up. ``scorecard.py`` will
tell you a book is REVERT *today*; ``reflection.py`` will tell you the regime
*today* — but neither remembers what it said last hour, so neither can learn which
of its signals actually predict anything. This module closes that loop.

Each CYCLE the agent:
  1. OBSERVE   — snapshot the per-book forward verdicts (``scorecard.book_scorecard``)
                 plus, when a feature frame is supplied, the regime + overfit state
                 (``reflection``).
  2. GRADE     — re-judge the PREVIOUS cycle's predictive proposals against what has
                 actually happened since (did the flagged book keep bleeding, or
                 recover?), and fold the result into a per-signal-type CALIBRATION.
  3. DETECT    — emit fresh, concrete PROPOSALS (revert this book, watch that decay),
                 each annotated with how RELIABLE that signal type has proven to be.
  4. PERSIST   — append the cycle + the running calibration to ``data/loop_agent.json``,
                 so the learning survives the ephemeral container (the whole point of
                 git-versioned memory).

It is strictly READ-ONLY over the journal and the other memory layers; it writes
only its own ledger. Nothing here touches the trading path — it is meant to be
invoked on its own cadence (the ``/loop`` skill, or a cron) *after* the bot has
logged trades, never inside the scan.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..journal import TradeJournal
from ..scorecard import book_scorecard

STATE_PATH = Path("data/loop_agent.json")

# Expectancy (R/trade) a still-positive book must shed between cycles to count as
# DECAYING — small enough to catch real slippage, large enough to ignore noise.
DECAY_DROP = 0.05

# Only these proposal types make a falsifiable PREDICTION about the future, so only
# these feed the reliability calibration. The rest are observations (reported, not graded).
CALIBRATED_TYPES = ("book_negative", "book_decay")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _reliability(cal: dict, ptype: str) -> float | None:
    """Vindicated / (vindicated + false_alarm) for a signal type — None if untested."""
    c = cal.get(ptype)
    if not c:
        return None
    decided = c.get("vindicated", 0) + c.get("false_alarm", 0)
    return round(c["vindicated"] / decided, 3) if decided else None


class LoopAgent:
    """The self-improving decision loop over the live paper/live books."""

    def __init__(self, journal: TradeJournal | None = None,
                 state_path: Path | str = STATE_PATH,
                 mode: str | None = "paper", since: str | None = None):
        self.journal = journal or TradeJournal()
        self.state_path = Path(state_path)
        self.mode = mode
        self.since = since

    # ----- persistence -------------------------------------------------------
    def load_state(self) -> dict:
        if not self.state_path.exists():
            return {"version": 1, "cycles": [], "calibration": {}}
        state = json.loads(self.state_path.read_text())
        state.setdefault("cycles", [])
        state.setdefault("calibration", {})
        return state

    def save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2))

    # ----- observe -----------------------------------------------------------
    def observe(self, regime: dict | None = None, overfit: dict | None = None) -> dict:
        """Snapshot the current per-book verdicts (+ optional regime/overfit).

        ``regime``/``overfit`` are injected (not fetched) so the agent stays offline
        and deterministic; the caller supplies them from ``reflection`` when a live
        feature frame is available.
        """
        card = book_scorecard(self.journal, mode=self.mode, since=self.since)
        books = {
            b: {"n": st["n"], "expectancy_r": st["expectancy_r"],
                "total_r": st["total_r"], "win_rate": st["win_rate"],
                "verdict": st["verdict"]}
            for b, st in card.get("books", {}).items()
        }
        return {"books": books, "overall": card.get("overall", {}),
                "regime": regime, "overfit": overfit}

    # ----- grade the previous cycle's predictions ----------------------------
    def grade_prior(self, prev: dict | None, snap: dict, calibration: dict) -> list[dict]:
        """Re-judge the previous cycle's predictive proposals against ``snap`` and
        fold terminal verdicts into ``calibration`` (mutated in place)."""
        graded: list[dict] = []
        if not prev:
            return graded
        for pr in prev.get("proposals", []):
            ptype = pr.get("type")
            if ptype not in CALIBRATED_TYPES:
                continue
            book = pr.get("book")
            cur = snap["books"].get(book)
            old = pr.get("metric", {})
            row = {"key": pr.get("key"), "type": ptype, "book": book,
                   "old_expectancy_r": old.get("expectancy_r"),
                   "new_expectancy_r": (cur or {}).get("expectancy_r")}
            if cur is None or cur["n"] == old.get("n"):
                # No new resolved trades (or the book vanished) — can't judge yet.
                row["verdict"] = "pending"
                graded.append(row)
                continue
            if ptype == "book_negative":
                vindicated = cur["expectancy_r"] < 0          # still bleeding net
            else:  # book_decay — predicted "keeps slipping"
                vindicated = cur["expectancy_r"] <= old.get("expectancy_r", 0.0)
            row["verdict"] = "vindicated" if vindicated else "false_alarm"
            c = calibration.setdefault(ptype, {"vindicated": 0, "false_alarm": 0})
            c["vindicated" if vindicated else "false_alarm"] += 1
            graded.append(row)
        return graded

    # ----- detect fresh proposals -------------------------------------------
    def detect(self, snap: dict, prev: dict | None, calibration: dict) -> list[dict]:
        """Turn the current snapshot (vs the previous one) into concrete proposals."""
        proposals: list[dict] = []
        prev_books = (prev or {}).get("books", {})

        def add(ptype: str, book: str | None, severity: str, why: str, metric: dict):
            proposals.append({
                "key": f"{ptype}::{book or 'global'}", "type": ptype,
                "book": book, "severity": severity, "why": why,
                "metric": metric, "reliability": _reliability(calibration, ptype),
            })

        for book, st in snap["books"].items():
            exp, n, verdict = st["expectancy_r"], st["n"], st["verdict"]
            prevb = prev_books.get(book)
            metric = {"expectancy_r": exp, "n": n}
            if verdict == "REVERT":
                add("book_negative", book, "act",
                    f"{book} is net-negative ({exp:+.3f}R/t over {n} trades) — revert/pause it.",
                    metric)
            elif (prevb and verdict in ("KEEP", "WAIT")
                  and n > prevb.get("n", 0)
                  and prevb.get("expectancy_r", 0.0) - exp >= DECAY_DROP):
                add("book_decay", book, "watch",
                    f"{book} expectancy slipped {prevb['expectancy_r']:+.3f}→{exp:+.3f}R/t "
                    f"as n grew {prevb['n']}→{n} — watch for decay.", metric)
            elif prevb and prevb.get("verdict") == "WAIT" and verdict == "KEEP":
                add("book_proven", book, "watch",
                    f"{book} crossed into KEEP ({exp:+.3f}R/t over {n}) — newly proven.", metric)

        # Regime shift (only when both cycles carry a regime).
        cur_reg, prev_reg = snap.get("regime"), (prev or {}).get("regime")
        if cur_reg and prev_reg:
            changed = [k for k in ("trend", "vol_regime")
                       if cur_reg.get(k) != prev_reg.get(k)]
            if changed:
                add("regime_shift", None, "watch",
                    "regime changed (" + ", ".join(
                        f"{k}: {prev_reg.get(k)}→{cur_reg.get(k)}" for k in changed)
                    + ") — book edges were measured in the prior regime.",
                    {"from": prev_reg, "to": cur_reg})

        # Overfit alarm — naive winners but nothing survives family-wide FDR.
        of = snap.get("overfit")
        if of and of.get("fdr_survivors", 0) == 0 and of.get("naive_winners", 0) > 0:
            add("overfit", None, "watch",
                f"{of['naive_winners']} naive winners but 0 survive family-wide FDR — "
                "treat them as unproven.", {k: of.get(k) for k in
                ("n_candidates", "naive_winners", "fdr_survivors")})
        return proposals

    # ----- one full cycle ----------------------------------------------------
    def run_cycle(self, regime: dict | None = None, overfit: dict | None = None,
                  persist: bool = True) -> dict:
        """Grade the prior cycle, detect fresh proposals, persist, and return the cycle."""
        state = self.load_state()
        prev = state["cycles"][-1] if state["cycles"] else None
        snap = self.observe(regime=regime, overfit=overfit)
        graded = self.grade_prior(prev, snap, state["calibration"])   # updates calibration
        proposals = self.detect(snap, prev, state["calibration"])     # reads updated calibration
        cycle = {"t": _now(), **snap, "graded": graded, "proposals": proposals}
        state["cycles"].append(cycle)
        self.last_calibration = state["calibration"]   # readable even on a dry run
        if persist:
            self.save_state(state)
        return cycle


def format_cycle(cycle: dict, calibration: dict | None = None) -> str:
    """Compact human/Telegram digest of one loop-agent cycle."""
    sev_emoji = {"act": "🛑", "watch": "👀"}
    lines = [f"🔁 Loop agent — {cycle.get('t', '')}"]
    ov = cycle.get("overall") or {}
    if ov:
        lines.append(f"Overall: {ov.get('expectancy_r', 0):+.3f}R/t over {ov.get('n', 0)} "
                     f"({ov.get('total_r', 0):+.1f}R)")

    graded = cycle.get("graded", [])
    decided = [g for g in graded if g["verdict"] in ("vindicated", "false_alarm")]
    if decided:
        lines.append("Graded last cycle: " + ", ".join(
            f"{g['book']} {g['type']}→{g['verdict']}" for g in decided))

    props = cycle.get("proposals", [])
    if not props:
        lines.append("No drift — all books holding.")
    else:
        for p in props:
            rel = p.get("reliability")
            rel_s = f"  [signal {rel:.0%} reliable]" if rel is not None else ""
            lines.append(f"{sev_emoji.get(p['severity'], '•')} {p['why']}{rel_s}")

    if calibration:
        cal_bits = []
        for t, c in sorted(calibration.items()):
            d = c.get("vindicated", 0) + c.get("false_alarm", 0)
            if d:
                cal_bits.append(f"{t} {c['vindicated']}/{d}")
        if cal_bits:
            lines.append("Calibration (vindicated/decided): " + ", ".join(cal_bits))
    return "\n".join(lines)
