"""Tests for the top-100 crypto universe loader (no network)."""
import textwrap

import pytest

from kudbee_quant.universe_loader import (
    DEFAULT_UNIVERSE_PATH,
    UniverseEntry,
    load_universe,
    normalize_pair,
    universe_specs,
)


def _write(tmp_path, body: str):
    p = tmp_path / "u.yaml"
    p.write_text(textwrap.dedent(body))
    return p


# --- the shipped config -----------------------------------------------------

def test_ships_a_large_enabled_universe():
    enabled = load_universe()                       # default path, enabled_only
    assert len(enabled) >= 90                        # ~100 majors+alts
    pairs = {e.pair for e in enabled}
    assert "BTCUSDT" in pairs and "ETHUSDT" in pairs
    assert all(e.timeframe == "1h" for e in enabled)        # 1h-only foundation
    assert all(e.pair.endswith("USDT") for e in enabled)

def test_disabled_symbols_are_skipped():
    all_entries = load_universe(DEFAULT_UNIVERSE_PATH, enabled_only=False)
    enabled = load_universe(DEFAULT_UNIVERSE_PATH, enabled_only=True)
    disabled = {e.symbol for e in all_entries} - {e.symbol for e in enabled}
    assert "LUNA" in disabled                        # shipped disabled example
    assert "BTC" not in disabled

def test_universe_specs_are_router_ready():
    specs = universe_specs()
    assert "BTCUSDT" in specs and len(specs) == len(set(specs))   # no dupes


# --- normalization ----------------------------------------------------------

def test_normalize_pair():
    assert normalize_pair("BTC") == "BTCUSDT"
    assert normalize_pair("btc") == "BTCUSDT"
    assert normalize_pair("BTCUSDT") == "BTCUSDT"            # idempotent
    assert normalize_pair("ETH", quote="USDC") == "ETHUSDC"

def test_normalize_pair_rejects_garbage():
    with pytest.raises(ValueError):
        normalize_pair("../evil")                            # SSRF charset guard
    with pytest.raises(ValueError):
        normalize_pair("")


# --- fail-safe paths --------------------------------------------------------

def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_universe(tmp_path / "nope.yaml")

def test_malformed_yaml_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("symbols: [unclosed\n")
    with pytest.raises(ValueError):
        load_universe(p)

def test_missing_symbols_key_raises(tmp_path):
    p = _write(tmp_path, "quote: USDT\n")
    with pytest.raises(ValueError):
        load_universe(p)

def test_invalid_symbol_fails_safe(tmp_path):
    p = _write(tmp_path, """
        symbols:
          - {symbol: "../../evil"}
    """)
    with pytest.raises(ValueError):
        load_universe(p)

def test_duplicate_pair_raises(tmp_path):
    p = _write(tmp_path, """
        symbols:
          - {symbol: BTC}
          - {symbol: BTC}
    """)
    with pytest.raises(ValueError):
        load_universe(p)

def test_non_1h_timeframe_rejected(tmp_path):
    p = _write(tmp_path, """
        symbols:
          - {symbol: BTC, timeframe: 5m}
    """)
    with pytest.raises(ValueError):
        load_universe(p)

def test_bad_position_size_rejected(tmp_path):
    p = _write(tmp_path, """
        symbols:
          - {symbol: BTC, max_position_usd: 0}
    """)
    with pytest.raises(ValueError):
        load_universe(p)

def test_entry_fields_and_defaults(tmp_path):
    p = _write(tmp_path, """
        quote: USDT
        default_max_position_usd: 50
        symbols:
          - {symbol: BTC, max_position_usd: 250, risk_label: major, notes: hi}
          - {symbol: ZIL}
    """)
    entries = load_universe(p)
    btc = next(e for e in entries if e.symbol == "BTC")
    zil = next(e for e in entries if e.symbol == "ZIL")
    assert isinstance(btc, UniverseEntry)
    assert btc.pair == "BTCUSDT" and btc.max_position_usd == 250 and btc.notes == "hi"
    assert zil.max_position_usd == 50                       # default applied
