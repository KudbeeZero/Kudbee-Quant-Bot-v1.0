# Research: is "Graphify" real, and would it help this project?

> Requested 2026-06-22 (owner saw a viral tweet about it). TL;DR: **the tool is real
> and legitimate; the viral "71.5× fewer tokens" number is NOT** — it's marketing, not
> in the project's own docs. For this repo it's a **low-risk, optional convenience**,
> not a needle-mover. Recommendation: a one-off read-only trial, no adoption commitment.

## What it is (verified)
**Graphify** — `safishamsi/graphify` on GitHub (MIT license, ~63K stars, very active,
first released ~Apr 2026). An AI-coding-assistant *skill* that turns a folder of code
(also SQL/docs/PDFs/images/video) into a queryable **knowledge graph** the assistant
reads instead of grepping. Author: Safi Shamsi, a London/Birmingham AI engineer whose
MSc thesis was on knowledge-graph RAG — so the pedigree is real, not vaporware.

- **PyPI package:** `graphifyy` (double-y). *The README explicitly warns other
  `graphify*` packages are unaffiliated* — easy to typo into the wrong/malicious one.
- **Install:** `uv tool install graphifyy` (or `pipx install graphifyy` / `pip install graphifyy`).
- **Claude Code:** `graphify install` (or `graphify claude install`), then `/graphify .`.
- **Output:** `graphify-out/` → `graph.html` (interactive), `GRAPH_REPORT.md`
  (key concepts / surprising links / suggested questions), `graph.json` (queryable).
  Optional exports: Obsidian vault (`--obsidian`), markdown wiki, Neo4j Cypher, SVG/GraphML.
- **Languages:** 36 tree-sitter grammars incl. **Python** (this repo's language).

## What's TRUE vs HYPE (honesty check — our standing rule)
| Claim (from the tweet) | Verdict |
|---|---|
| Real tool, MIT, builds a code knowledge graph, Claude-Code skill, Obsidian export | ✅ TRUE (confirmed in the repo README) |
| **"Up to 71.5× fewer tokens per query"** | ⚠️ **UNVERIFIED** — this number is **not in the repo's README**; no benchmark or methodology is published. Treat as marketing until independently measured. |
| 63K stars "in days" | Real, but rapid-viral star growth is itself a mild caution flag — popularity ≠ fit. |

## Would it help *this* project?
**Marginally — it's a nice-to-have, not a fix for anything we have.**
- **Against it:** this repo already has unusually strong AI-context scaffolding —
  `CLAUDE.md`, `docs/MEMORY.md`, `docs/HANDOFF.md`, `docs/SESSION_PROTOCOL.md`. That's
  exactly the "second brain" job Graphify pitches, and ours is curated + honest. The
  codebase is also modest in size (one `kudbee_quant` package), so grep/Read already
  work fine and cheaply.
- **Where it *could* help:** a one-shot **map of `kudbee_quant/` + `scripts/`** to see
  cross-module structure (e.g. how `paper.py` ↔ `confluence/stack.py` ↔ `backtest/
  bracket.py` ↔ `scorecard.py` connect) for onboarding a new session faster, and the
  `GRAPH_REPORT.md`'s "surprising connections" can surface coupling worth refactoring.
- **It does NOT touch the trading edge.** It's a developer-navigation aid only.

## Caveats / risks (do these before trusting it)
- **Supply chain:** it's a third-party tool you'd install with `uv`/`pipx`. Vet it; pin
  a version; install the correct `graphifyy` package (the typo-squat warning is real).
- **Privacy:** query logging is **on by default** to `~/.cache/graphify-queries.log` —
  disable it. Never point it at anything with secrets (our `TELEGRAM_*`, journal, etc.).
- **Cost:** code-only graphs run **offline/free**; graphing **docs/PDFs/images needs an
  LLM API key** ($). For us, run code-only.
- **Don't commit its output:** `graphify-out/` (esp. `cost.json`) must stay out of git —
  this PR adds it to `.gitignore` preemptively.

## Recommendation
**Try it once, read-only, no adoption.** If the `GRAPH_REPORT.md` reveals something the
existing docs don't, keep it as an ad-hoc tool; otherwise drop it. Do **not** wire it
into the workflow or the bot — it has zero bearing on the strategy/PnL (which is where
the actual problem is: the book's negative expectancy, per the scorecard).

### Exact trial steps (code-only, offline, free)
```bash
pipx install graphifyy            # or: uv tool install graphifyy
graphify --version                # confirm it's the real 'graphifyy'
cd Kudbee-Quant-Bot-v1.0
graphify kudbee_quant scripts --no-log   # map code only; skip docs (no API key/cost)
open graphify-out/GRAPH_REPORT.md graphify-out/graph.html
# graphify-out/ is gitignored by this PR — nothing gets committed
```
(Flag names like `--no-log` are illustrative — confirm against `graphify --help`; the
README's logging/offline switches are the source of truth.)

## Sources
- https://github.com/safishamsi/graphify (repo README — the authoritative source)
- https://github.com/safishamsi (author)
- https://graphify.net/ (project site)
- Secondary/marketing (treat claims skeptically): augmentcode.com, medium.com, emelia.io, knightli.com
