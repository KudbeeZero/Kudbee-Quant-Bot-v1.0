"""Load the configurable top-100 crypto trading universe (1h timeframe).

The top-10 majors live as a Python constant in ``universe.py`` (the validated
forward set, MEMORY §1). The broader top-100 is data, not code, so it lives in
``config/crypto_universe.yaml`` and is loaded + validated here. Membership beyond
the majors is UNPROVEN forward (§31) — this loader is plumbing, not a claim of edge.

Design goals (acceptance criteria):
  * load the top-100 universe from YAML (or a caller-supplied path);
  * skip ``enabled: false`` symbols;
  * normalize a ticker to its exchange pair (BTC -> BTCUSDT) and a router spec;
  * FAIL SAFE — a missing file, malformed YAML, an invalid/duplicate symbol, or a
    non-1h timeframe raises a clear error rather than silently trading garbage.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .ingest.router import parse_spec

# Repo-root config (this file is kudbee_quant/universe_loader.py -> parents[1] = root).
DEFAULT_UNIVERSE_PATH = Path(__file__).resolve().parents[1] / "config" / "crypto_universe.yaml"

# This foundation is 1h-only by design (no 5m — §37 paused the fee-poisoned 5m book).
ALLOWED_TIMEFRAMES = {"1h"}


@dataclass(frozen=True)
class UniverseEntry:
    """One tradable symbol in the universe, fully resolved + validated."""
    symbol: str            # ticker, e.g. "BTC"
    pair: str              # exchange pair / router spec, e.g. "BTCUSDT"
    enabled: bool
    timeframe: str         # "1h"
    max_position_usd: float
    risk_label: str
    notes: str

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol, "pair": self.pair, "enabled": self.enabled,
            "timeframe": self.timeframe, "max_position_usd": self.max_position_usd,
            "risk_label": self.risk_label, "notes": self.notes,
        }


def normalize_pair(symbol: str, quote: str = "USDT") -> str:
    """Ticker -> exchange pair: ``BTC`` -> ``BTCUSDT``. Idempotent if the quote is
    already present (``BTCUSDT`` stays ``BTCUSDT``). Validated against the router's
    strict charset so it is safe to interpolate into request URLs (no SSRF)."""
    sym = str(symbol).strip().upper()
    if not sym:
        raise ValueError("empty symbol in universe config")
    quote = quote.strip().upper()
    pair = sym if sym.endswith(quote) else f"{sym}{quote}"
    # parse_spec raises ValueError on anything outside [A-Za-z0-9._=^-]{1,20}.
    source, validated = parse_spec(pair)
    if source != "binance":
        raise ValueError(f"universe symbol {symbol!r} must be a bare/binance pair, not {source!r}")
    return validated


def load_universe(
    path: str | Path = DEFAULT_UNIVERSE_PATH,
    enabled_only: bool = True,
) -> list[UniverseEntry]:
    """Parse + validate the universe YAML into a list of :class:`UniverseEntry`.

    Raises ``FileNotFoundError`` if the config is missing and ``ValueError`` on any
    structural problem (malformed YAML, missing ``symbols``, bad timeframe, an
    invalid symbol, or a duplicate pair). With ``enabled_only`` (default) the
    ``enabled: false`` rows are dropped from the result.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"universe config not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:                      # malformed YAML -> fail safe
        raise ValueError(f"could not parse universe config {p}: {e}") from e
    if not isinstance(raw, dict) or "symbols" not in raw:
        raise ValueError(f"universe config {p} must be a mapping with a 'symbols' list")
    rows = raw.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"universe config {p} has no 'symbols' entries")

    quote = str(raw.get("quote", "USDT")).strip().upper()
    default_tf = str(raw.get("default_timeframe", "1h"))
    default_max = float(raw.get("default_max_position_usd", 100))

    entries: list[UniverseEntry] = []
    seen_pairs: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or "symbol" not in row:
            raise ValueError(f"universe entry #{i} must be a mapping with a 'symbol'")
        symbol = str(row["symbol"]).strip().upper()
        pair = str(row["pair"]).strip().upper() if row.get("pair") else normalize_pair(symbol, quote)
        # validate any explicitly-supplied pair too
        normalize_pair(pair, quote)
        timeframe = str(row.get("timeframe", default_tf))
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise ValueError(
                f"universe entry {symbol!r} timeframe {timeframe!r} not allowed "
                f"(this foundation is {sorted(ALLOWED_TIMEFRAMES)}-only)"
            )
        if pair in seen_pairs:
            raise ValueError(f"duplicate pair {pair!r} in universe config")
        seen_pairs.add(pair)
        max_usd = float(row.get("max_position_usd", default_max))
        if max_usd <= 0:
            raise ValueError(f"universe entry {symbol!r} max_position_usd must be > 0")
        entries.append(UniverseEntry(
            symbol=symbol, pair=pair, enabled=bool(row.get("enabled", True)),
            timeframe=timeframe, max_position_usd=max_usd,
            risk_label=str(row.get("risk_label", "")), notes=str(row.get("notes", "")),
        ))

    if enabled_only:
        entries = [e for e in entries if e.enabled]
    return entries


def universe_specs(entries: list[UniverseEntry] | None = None) -> list[str]:
    """Router specs (pairs) for the enabled universe — feed straight to
    ``paper-scan`` / ``RouterClient``. Defaults to loading the on-disk universe."""
    if entries is None:
        entries = load_universe()
    return [e.pair for e in entries]
