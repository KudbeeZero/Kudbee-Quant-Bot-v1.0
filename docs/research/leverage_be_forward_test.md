# Paper-forward test spec — `lock+0.1R @ first-green`, ≤10x, maker/zero-fee venue

**Status:** DESIGN ONLY (no code, no live changes). Derived from
`docs/research/leverage_be_study.md`. Implementation waits until PR #35 merges
(serial rule). Paper-only; never enables real-money trading; never touches the
§1 validated defaults or `bracket.py`/`resolver.py` live path.

## What we're testing (the one candidate)

The study's only non-losing lane:

> **Management:** move stop to **+0.1R (small locked profit)** the moment price
> first ticks green (the favourable move is near-immediate — median ~0h).
> **Leverage:** **≤10x** (the only level where liquidation ≈ 1% instead of 55%).
> **Venue:** **zero-fee / maker** — the TradFi/Yahoo book, or **maker-only** crypto
> (no taker entries; the entire +0.038R hinges on ~0% effective fee, §42).
> **Selection:** prefer **short-side** and **wider-stop (>0.5%)** setups; exclude
> sub-0.5% scalps (friction = cost_R = roundtrip% / stop% destroys them).

The brief's safety line stands: expectancy + drawdown decide this, not % green.

## Why a forward test at all (what the backtest can't tell us)

The study is an **offline replay** of trades the engine already took. Three things
it cannot answer, and that only forward testing can:

1. **Maker-fill feasibility (§42, the make-or-break).** The +0.038R assumes we get
   filled at ~0 fee. If the maker limit doesn't fill (price runs without us) or we
   cross to taker, the edge is gone. This is the #1 thing to measure.
2. **Real slippage/spread on alts at micro size** (the study used a flat assumption).
3. **Forward (out-of-sample) stability** — the sample pools the §44 flip regime; is
   the short-side skew real or an artifact?

## Pre-registration (commit to this BEFORE collecting data)

To avoid fitting the result after the fact:

- **Primary metric:** net-of-fee expectancy (R/trade) of the BE-managed rule on the
  **maker/zero-fee subset**, vs the original management on the same trades (paired).
- **Success:** primary metric **> 0** AND its improvement over original is
  **FDR-significant** (reuse `events/study.py`, the same Wilson+BH harness) at
  **n ≥ 150** resolved maker-venue trades. Below that n → "inconclusive," keep paper.
- **Kill criteria (any one → stop, revert to original):** maker **fill rate < 60%**;
  realized net expectancy **< −0.10R** over any rolling 100 trades; **liquidation rate
  at the capped ≤10x sizing materially above the study's ~1% baseline** (kill if **>2%**
  — the study found ≈1% at 10x, so 0 is the wrong bar; a spike means the risk model broke).
- **Horizon:** min 2 weeks of the hourly Action OR n≥150, whichever is later.
- **Drawdown guard:** report max consecutive losing streak + peak-to-trough R; this
  is a survivability test, not a win-rate test.

## Implementation — two tiers, cheapest/safest first

### Tier 1 — Shadow overlay (ZERO engine change, start first)

A periodic **read-only** report that, each run, takes the live `data/journal.json`,
filters to the maker/zero-fee venue + (>0.5% stop) subset, and replays the
`lock+0.1R@first-green` management over the real bars — i.e. exactly what
`scripts/leverage_be_study.py` already does, packaged as a recurring
`losing-clusters`-style CLI sub-command (e.g. `be-shadow`) or a scheduled script.

- **Builds on:** `scripts/leverage_be_study.py` (path replay + `sim_policy`).
- **Writes nothing** to the journal; emits its own report/CSV under `docs/research/`
  or a `data/shadow/` artifact (NOT `data/journal.json`).
- **Answers:** does the BE rule beat original *out-of-sample* as new trades resolve?
  (It still assumes maker fills — so it validates management, not fill feasibility.)
- **Cost:** ~an afternoon; no risk to the live bot.

### Tier 2 — Real parallel paper book (needs a small, ISOLATED engine add)

To test **fill feasibility** we must actually place the maker limits and BE-manage:

- **New, default-OFF management mode** on `Prediction` (e.g. `be_trigger="first_green"`
  / `be_level=0.1`) + resolver support to move the stop on the trigger. Gated behind
  a flag so the **validated default path is untouched** (mirrors how PR #20 flags
  stay OFF until forward-validated).
- **Separate paper track:** a distinct scan (`--maker-only`, `--max-leverage 10`,
  venue+stop filters) logging to a **separate shadow journal**, so it never races or
  contaminates the bot-owned `data/journal.json`.
- **Records the fill question:** for each signal, did the maker limit fill at the
  intended price, partial, or cancel/cross? This is the data Tier 1 can't produce.
- **Still paper** (`dry_run=True`) — no live orders, no real money.

## Decision flow

1. Merge #35. 2. Build **Tier 1** shadow overlay; let it run until n≥150 maker-venue
trades. 3. If primary metric clears the pre-registered bar → build **Tier 2** to
settle the fill question. 4. Only if BOTH clear, with liquidation ≈ 0 at ≤10x, does
this graduate from "candidate" to "validated" — and even then, micro stake only,
never full account risk.

*Not financial advice. Design artifact; no live trading changes.*
