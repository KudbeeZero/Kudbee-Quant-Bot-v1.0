# DSA Study Plan — using this repo as your practice material

> Companion to a beginner-friendly infographic, *"How to Master Data Structures and
> Algorithms Without Feeling Lost"*. Instead of leetcode-style drills, this plan sends
> you to **real, working code in this trading bot** (`kudbee_quant/`) for every
> structure that genuinely shows up here — and says so plainly where a structure
> does **not** show up, rather than forcing a fit. Consistent with this repo's own
> rule: don't claim something is "there" unless you can point at the file:line.

---

## 1. Understand — what the infographic actually says

The infographic lays out a **6-step method** for learning DSA without feeling lost:

1. **Understand** — read the book/concept.
2. **Visualize** — see it (the eye icon) — picture the structure, don't just read prose.
3. **Practice** — pencil-and-paper / hands-on repetition.
4. **Patterns** — recognize the small set of recurring shapes problems take.
5. **Revise** — cycle back (the loop icon) — spaced repetition, not one-and-done.
6. **Apply** — launch it (the rocket) — use it in a real problem/project.

It goes from a **"Confused Start"** (a stick figure surrounded by "?" — "Where do I
start?") through those 6 steps to **"Clarity / Mastery"** (a flag on a mountain).

It then diagrams the basic structures, exactly as drawn:

- **Array** — `[10, 20, 30, 40, 50]` indexed 0-4; "Index starts at 0."
- **Linked List** — `10 -> 20 -> 30 -> 40 -> NULL`; "Nodes connected one after another."
- **Stack (LIFO)** — a vertical box, TOP at 40, then 30, 20, 10 at the bottom; "Last In
  First Out."
- **Queue (FIFO)** — `10 20 30 40` in a row, Front on the left, Rear on the right;
  "First In First Out."
- **Binary Tree** — root `1`, children `2` and `3`, grandchildren `4`, `5` (under 2)
  and `6` (under 3).
- **Graph** — nodes A, B, C, D, E with directed edges (A→B, A→C, B→D, C→B, C→E, D→E).
- **Recursion** — `f(n) -> f(n-1) -> f(1)`; "Break down the problem into smaller
  instances."
- **Sorting (Bubble Sort walkthrough)** — unsorted `[5,1,4,2,8]` → Pass 1
  `[1,4,2,5,8]` → Pass 2 `[1,2,4,5,8]` → Pass 3 `[1,2,4,5,8]`; "Smaller elements move
  left, larger move right."

Closing principles, verbatim: **"Don't memorize — understand,"** **"Think in
steps,"** and under "Keep in Mind": focus on concepts not shortcuts, solve problems
regularly, learn from mistakes, be patient and consistent. Final line: **"Progress
over Perfection."**

---

## 2. Visualize — map each structure to where (if anywhere) it lives in this repo

Quick-reference table before the deep dive in section 3. "Real" means there is an
actual, working, non-toy instance of the structure/algorithm doing a real job in
`kudbee_quant/` — not a superficial name match.

| Infographic structure | Real example in this repo? | Where |
|---|---|---|
| Array / vectorized ops | **Yes — pervasive** | `kudbee_quant/levels/builder.py`, `kudbee_quant/backtest/engine.py` |
| Hashmap / dict | **Yes — several genuine uses** | `kudbee_quant/paper/paper.py`, `kudbee_quant/config/feature_toggles.py`, `kudbee_quant/ingest/cache.py`, `kudbee_quant/api_security.py` |
| Queue (FIFO) | **Yes — one clean example** | `kudbee_quant/api_security.py` (`deque` rate limiter) |
| Stack (LIFO) | **No genuine LIFO stack** | closest name-match, `confluence/stack.py`, is not actually a LIFO stack (see below) |
| Sorting / searching | **Yes — several** | `kudbee_quant/universe_rank.py`, `kudbee_quant/journal/journal.py`, `kudbee_quant/scorecard.py` |
| Recursion | **Yes — one clear, small example** | `kudbee_quant/api_runner.py`, `kudbee_quant/confluence/trace.py` (`_jsonable`) |
| Binary Tree / Trees | **No** | not present |
| Linked List | **No** | not present |
| Graph | **No** (as a data structure) | `daily_graph.py` is a chart, not a graph DS; see below |

---

## 3. Practice — the exercises, per structure

For each structure: whether it's real here, the exact citation, and a concrete
"go read/trace this" exercise (per the infographic's own "Practice" + "Apply" steps).

### Array — REAL, and the strongest match in this codebase

The whole backtest/levels engine is array processing: pandas `Series`/`DataFrame`
columns are just typed, labeled arrays, and the code leans on rolling windows,
cumulative scans, and elementwise vector ops instead of index loops.

- `kudbee_quant/levels/builder.py:47-62` (`_per_date_range_avg`) — a rolling-window
  average over a groupby, then a `shift`/`ffill` to keep it lookahead-safe.
- `kudbee_quant/levels/builder.py:120-126` — `cummax()`/`cummin()` running-extreme
  arrays (`day_hi`, `day_lo`) — literally the "running max so far" array pattern.
- `kudbee_quant/levels/builder.py:164-169` — a `for p in (5, 13, 50, 200, 800)` loop
  building 5 EMA arrays, then an elementwise `np.where` comparison across them.
- `kudbee_quant/backtest/engine.py:56-60` — position/price arrays clipped, reindexed,
  and shifted before the simulation loop runs.

**Exercise:** open `builder.py`, pick `_per_date_range_avg` (lines 47-62), and on
paper trace what `by_date`, `rng`, `incl`, and `prior` each look like for a tiny
5-row toy DataFrame. Confirm for yourself *why* `.shift(1)` is needed to keep the
array lookahead-safe — that's the array-indexing intuition the infographic's
"Array" box is trying to build, just at trading-bot scale.

### Hashmap / Dict — REAL, several genuine and well-motivated uses

- `kudbee_quant/paper/paper.py:234-262` — **the best citation for the task's
  "dedup-by-(symbol, timeframe, book)" idea.** `open_keys` is a `set` of
  `(symbol, timeframe, book)` tuples built from the open journal (line 237); a new
  scan candidate is dropped with a plain `in` hashmap/set lookup (line 261) instead
  of a linear scan of the whole journal.
- `kudbee_quant/alert_inbox.py:97-99` — the same dedup pattern, one key shorter
  (`(symbol, timeframe)`), guarding TradingView webhook alerts against double-entry.
- `kudbee_quant/config/feature_toggles.py:23-31` (`KNOWN_FLAGS` dict) and
  `:52-61` (`is_enabled`) — a small dict acting as a lookup table from a logical flag
  name to its env-var name, with a fallback chain (env → JSON-file dict → default).
- `kudbee_quant/ingest/cache.py:24-82` (`DataCache`) — an on-disk hashmap: cache keys
  are SHA-256-hashed (line 32) to safe filenames; `get`/`put` are the load/store half
  of a classic key→value cache with a TTL.
- `kudbee_quant/api_security.py:74` (`_HITS: dict[str, deque]`) — a dict mapping a
  rate-limit key to its queue of hit-timestamps (ties into the Queue example below).

**Exercise:** read `paper.py:234-262` end to end. Without running anything, answer:
why is the key a 3-tuple and not just the symbol? (Because more than one "book" —
baseline vs. an experiment flag — can each hold one open trade on the same
symbol+timeframe.) That's a hashmap doing real dedup/collision-avoidance work, not a
toy `dict.get()` example.

### Stack (LIFO) — NOT genuinely present; one honest false-friend to flag

Grepping the codebase for actual LIFO usage (`.pop()` off the end of a list, an
explicit stack class, `collections` stack idioms) turns up nothing. The one
tempting name-match is `kudbee_quant/confluence/stack.py` — but read its own
docstring (lines 1-8) and `confluence_score()` (lines 99-114): "stack" here means
**stacking up confluence votes** (summing several ±1 signals into one score,
`votes.sum(axis=1)`), a completely different sense of the word from the
push/pop LIFO structure in the infographic. Calling this a "stack" for DSA purposes
would be a fabricated fit.

**Honest recommendation:** skip a repo exercise for this one, or — if you want the
"Apply" step's satisfaction — write a *tiny* toy LIFO (a Python list with
`.append()`/`.pop()`, or `list` as `push`/`pop`) to parse matching brackets in one of
this repo's own config strings (e.g. balance the parens in a formula string). That
keeps the practice honest instead of pretending the trading code has one.

### Queue (FIFO) — REAL, one clean, textbook-quality example

- `kudbee_quant/api_security.py:74-99` (`RateLimiter`) — a genuine sliding-window
  rate limiter built on `collections.deque`: `dq.append(now)` (line 95) enqueues at
  the back, `dq.popleft()` (line 92) dequeues from the front once a hit ages out of
  the window. This *is* First-In-First-Out, doing real work (protecting the write
  API from abuse).
- Weaker/partial second example: `kudbee_quant/alert_inbox.py:145-172`
  (`ingest_inbox`) processes a batch of pending alert files with
  `for f in sorted(inbox_dir.glob("*.json"))` (line 155) — batch, in-order
  processing, but **be honest**: the sort key is the file's hash-derived id (line
  57-59 of the same file), not arrival time, so this is "process the whole batch in
  some fixed order," not a strict chronological FIFO queue. Don't oversell it.

**Exercise:** trace `RateLimiter.__call__` (lines 86-99) by hand for `limit=3`,
`window=60`: three calls at t=0,10,20 (all allowed, deque has 3 entries), a 4th call
at t=30 (blocked, `len(dq) >= limit`), then a call at t=61 (the t=0 entry is now
`<= 61-60`, gets popped from the front, so this call is allowed). That's the
"Front/Rear, First In First Out" picture from the infographic, with real numbers.

### Binary Tree / Trees — NOT present

A search for any `class Node`, `self.left`/`self.right`/`self.children`, or nested
recursive-record structure across `kudbee_quant/` turns up nothing. `levels/builder.py`
(the file the task flagged as worth checking) builds many *related* level columns
(pivots, M-levels, ADR/AWR bands — see section 1 above), but they are **flat
DataFrame columns**, not a tree: there's no parent/child relationship encoded in the
data itself, only in the prose comments describing how one pivot derives from
another (e.g. `mlevel_m5 = (r2 + r3) / 2.0` at `builder.py:202`, a plain arithmetic
formula, not a tree traversal).

**Honest recommendation:** skip this one, or build a tiny standalone toy binary
tree (insert/search on integers) purely as a DSA warm-up — don't try to retrofit a
tree reading onto `builder.py`'s pivot formulas; that would overstate the fit.

### Graph — NOT present as a data structure

- `kudbee_quant/daily_graph.py` is **not** a graph data structure — read its own
  docstring (lines 1-18): it's a hand-built SVG line chart of the day's cumulative
  net-R equity curve. "Graph" here means "chart/picture," the colloquial sense, not
  nodes-and-edges.
- The confluence vote-combination logic the task flagged
  (`kudbee_quant/confluence/stack.py:99-114`, `confluence_score`) is a flat sum
  (`votes.sum(axis=1)`) of independent per-factor votes — there is no dependency
  graph between factors, no adjacency list/matrix, and no graph traversal (BFS/DFS/
  shortest-path) anywhere in `kudbee_quant/`.
- (Tangential, for completeness: `docs/research/graphify_evaluation.md` records a
  one-off evaluation of an unrelated third-party *code-mapping* tool called
  "Graphify" — that's about visualizing the codebase's module dependencies for an AI
  assistant's benefit, not a graph data structure used *by* the trading logic. Not a
  real citation for this category.)

**Honest recommendation:** skip a repo exercise for graphs entirely, or build a tiny
toy adjacency-list graph + BFS on made-up data if you want the practice rep. Forcing
this onto the confluence scorer would misrepresent how that code works.

### Recursion — REAL, one small, clean example (used twice)

- `kudbee_quant/api_runner.py:124-145` (`_jsonable`) — converts an arbitrary nested
  value (dataclass / dict / list / pandas / numpy) into plain JSON-safe Python.
  It recurses on itself at lines 130, 132, 134, 140, and 142 — e.g. line 132:
  `{str(k): _jsonable(v) for k, v in x.items()}` recursively jsonifies every value
  of a dict.
- `kudbee_quant/confluence/trace.py:203-216` — the same pattern, independently
  implemented for the confluence-trace API response (recurses at lines 206 and 208).
- **Honest caveat:** this is the *only* real recursion found in `kudbee_quant/` (a
  repo-wide scan of every function for a self-call turned up just these two). The
  backtest resolver (`kudbee_quant/backtest/resolver.py`), which might look like a
  tree-walk candidate, is actually a plain iterative `for` loop over bars, not
  recursive. Don't assume recursion is common here — it isn't; this is a small,
  honest example, not a rich vein.

**Exercise:** trace `_jsonable({"a": [1, {"b": 2.0}]})` by hand through
`api_runner.py:124-145` — write down each recursive call and its return value, in
order, until you hit a base case (`None`/`bool`/`int`/`str`/`float` at lines 125-128).
That IS the infographic's `f(n) -> f(n-1) -> f(1)` picture, just on nested JSON
instead of a number.

### Sorting / Searching — REAL, several genuine, purposeful uses

- `kudbee_quant/universe_rank.py:47` — `scored.sort(key=lambda x: x[1],
  reverse=True)` ranks candidate symbols by mean traded volume, most-liquid first
  (feeds `volume_ranked_universe`, `universe_rank.py:51-62`).
- `kudbee_quant/journal/journal.py:320` — `scorecard()` sorts per-setup rows by
  sample size (`sort_values("n", ascending=False)`).
- `kudbee_quant/journal/journal.py:411-413` — `symbol_record()` sorts per-symbol
  rows by net R **ascending** (worst symbols first, by design — the comment at
  line 384 says so directly).
- `kudbee_quant/scorecard.py:174-178` (`book_regime_breakdown`) — a genuine
  "sort, then index into the sorted list" percentile computation: `known =
  sorted(...)` then `lo_cut = known[len(known)//3]` / `hi_cut = known[2*len(known)//3]`
  to split trades into low/mid/high volatility terciles.

**Exercise:** read `universe_rank.py` end to end (only 63 lines) — `rank_by_volume`
(lines 22-48) builds an unsorted `(symbol, volume)` list while fetching data, then
sorts it once at line 47. Compare that to the infographic's bubble-sort walkthrough:
this uses Python's built-in Timsort instead of hand-rolled bubble sort, but the
*idea* — "put the elements in order by some key, largest first" — is identical.
Then look at `scorecard.py:174-178` for the second idea: once a list is sorted, you
can find any percentile by simple index arithmetic — no separate search needed.

---

## 4. Patterns — the recurring shapes, once you've done section 3

Across the citations above, a small number of patterns keep reappearing — spotting
them is the infographic's "Patterns" step:

- **"Sort once, then just index."** `universe_rank.py:47` and
  `scorecard.py:174-178` both sort a list once and then read off what they need by
  position — no repeated searching.
- **"Set/dict membership instead of a linear scan."** `paper.py:234-262` and
  `alert_inbox.py:97-99` both build a `set` of keys up front so a "is this already
  open?" check is O(1) instead of re-scanning the whole journal per candidate.
- **"Sliding window via evict-from-the-front."** `api_security.py:86-99` is the
  clearest example: keep appending to the back, and periodically drop from the
  front whatever fell outside the window — same shape a naive
  `[x for x in dq if x > cutoff]` would do, but O(1) amortized instead of O(n).
- **"Recurse over the *shape* of the data, not a count."** Both `_jsonable`
  functions recurse on "is this a dict / list / dataclass," not on a numeric
  countdown like the infographic's `f(n)→f(n-1)` — a good contrast to notice.
- **Absence is a pattern too.** No linked lists, trees, or graphs anywhere in
  `kudbee_quant/` is itself informative: this is a pandas/dict/set-shaped codebase,
  not a pointer-and-node-shaped one. That's normal for a data-pipeline/trading bot,
  not a gap in the code.

---

## 5. Revise — cheap ways to re-test yourself against this repo later

Revisit (don't just re-read) these citations after a few days, closed-book:

1. Without looking, write from memory what key `open_keys` uses in
   `paper.py:234-262` and why — then check yourself against the file.
2. Redraw the `RateLimiter` deque state (front/back) for a made-up sequence of
   request times, then re-read `api_security.py:86-99` to check your trace.
3. Re-derive, from memory, why `_jsonable` needs a base case before it can recurse
   on dict/list/dataclass — then diff your answer against
   `api_runner.py:124-134`.
4. Quiz yourself: which 3 structures are **absent** from this repo (linked list,
   binary tree, graph) and why calling `confluence/stack.py` a "stack" or
   `daily_graph.py` a "graph" would be wrong. If you can explain the false-friend
   in one sentence each, you've actually understood the naming, not just memorized
   it — which is the infographic's "don't memorize, understand" principle.

---

## 6. Apply — put it to (small, safe, non-trading) use

The infographic's last step is "launch it" — use the structure somewhere real. Two
low-risk ways to do that against *this* repo, both purely additive and **not**
touching any trading/execution/journal logic:

- **Read-and-extend, safely:** write a short, throwaway script (outside
  `kudbee_quant/`, e.g. in a scratch file) that calls `rank_by_volume()`
  (`universe_rank.py:22-48`) against a small hardcoded list of `(symbol, volume)`
  pairs you make up, and confirms the sort behaves as expected. This exercises
  "Apply" without going anywhere near money-path code.
- **Fill an honest gap, as a toy, not a repo change:** since Stack, Linked List,
  Binary Tree, and Graph are all genuinely absent here, write four small, separate,
  standalone toy scripts (a LIFO stack for bracket-matching, a singly linked list,
  a binary search tree with insert/search, a tiny graph with BFS) purely for your
  own practice. Keep them outside `kudbee_quant/` — the point is personal practice,
  not adding unused data structures to a production trading bot.

---

## Summary table (the honest scorecard)

| Category | Real in this repo? | Best citation |
|---|---|---|
| Array / vectorized ops | Strong yes | `kudbee_quant/levels/builder.py:47-62, 118-126` |
| Hashmap / dict | Strong yes | `kudbee_quant/paper/paper.py:234-262` |
| Stack (LIFO) | **No** (name-only false friend) | `kudbee_quant/confluence/stack.py` is vote-summation, not LIFO |
| Queue (FIFO) | Yes, one clean example | `kudbee_quant/api_security.py:74-99` |
| Binary Tree / Trees | **No** | not present anywhere |
| Graph | **No** (as a data structure) | `daily_graph.py` is a chart, not a graph |
| Recursion | Yes, small/thin | `kudbee_quant/api_runner.py:124-145`, `kudbee_quant/confluence/trace.py:203-216` |
| Sorting / searching | Strong yes | `kudbee_quant/universe_rank.py:47`, `kudbee_quant/journal/journal.py:320,411-413` |
| Linked List | **No** | not present anywhere |

This repo is genuinely strong practice material for **arrays/vectorization,
hashmaps, and sorting/ranking** — the bread and butter of a pandas-based trading
bot — genuinely thin on **recursion**, and honestly absent for **stacks, queues
(beyond one example), linked lists, trees, and graphs**. That split is expected for
this kind of codebase and is not a flaw in the bot.
