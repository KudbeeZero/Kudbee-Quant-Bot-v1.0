"""Dynamic volume universe (§B) — an OPT-IN selector that ranks a candidate pool
by recent traded USD volume and returns the most-liquid top-N.

Status / honesty: this is a NET-NEW, self-contained implementation built from the
descriptive name ("dynamic volume universe"). The owner has referenced a §B spec
that lives outside this repo; this module does NOT claim to be that spec and may
differ from it — it's easy to reconcile once the reference is provided. It is OFF
by default and is NOT wired into the validated forward workflow (paper-trade.yml);
the validated book still trades the static ``universe.TOP_10_CRYPTO``. Use it via
``cli universe-rank`` or by importing :func:`volume_ranked_universe`.

Ranking metric: mean ``quote_volume`` (exchange-reported USD volume) over the last
``lookback_bars`` of ``interval`` bars — a direct, robust liquidity proxy. Symbols
whose data can't be fetched are skipped, not fatal.
"""
from __future__ import annotations

from .ingest.router import RouterClient
from .universe import CRYPTO_CANDIDATES


def rank_by_volume(candidates: list[str] | None = None, *, interval: str = "1h",
                   lookback_bars: int = 168, client: RouterClient | None = None,
                   ) -> list[tuple[str, float]]:
    """Return ``[(symbol, avg_quote_volume), ...]`` sorted most-liquid first.

    ``lookback_bars`` defaults to 168 (one week of 1h bars). Unfetchable / empty
    symbols are dropped. ``avg_quote_volume`` is the mean exchange USD volume per
    bar over the window.
    """
    client = client or RouterClient()
    cands = candidates if candidates is not None else list(CRYPTO_CANDIDATES)
    scored: list[tuple[str, float]] = []
    for sym in cands:
        try:
            df = client.klines(sym, interval=interval, limit=lookback_bars)
        except Exception:  # noqa: BLE001 — a bad/delisted ticker must not abort the rank
            continue
        if df is None or getattr(df, "empty", True) or "quote_volume" not in df:
            continue
        qv = df["quote_volume"].tail(lookback_bars).dropna()
        if qv.empty:
            continue
        avg = float(qv.mean())
        if avg > 0:
            scored.append((sym, avg))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def volume_ranked_universe(candidates: list[str] | None = None, *, top_n: int = 10,
                           interval: str = "1h", lookback_bars: int = 168,
                           min_quote_volume: float = 0.0,
                           client: RouterClient | None = None) -> list[str]:
    """The dynamic universe: the ``top_n`` candidates by mean USD volume.

    ``min_quote_volume`` drops anything below an absolute liquidity floor before
    taking the top-N. Returns just the symbols, most-liquid first.
    """
    ranked = rank_by_volume(candidates, interval=interval,
                            lookback_bars=lookback_bars, client=client)
    return [s for s, qv in ranked if qv >= min_quote_volume][:top_n]
