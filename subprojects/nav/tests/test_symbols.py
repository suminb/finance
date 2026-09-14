import pytest

from nav import symbols

YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: Advanced Micro Devic, ticker: AMD, currency: USD}
- {name: AMD, ticker: AMD, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""


@pytest.fixture
def symbol_map(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(YAML, encoding="utf-8")
    return symbols.load(str(path))


def test_resolves_a_known_name(symbol_map):
    assert symbol_map.resolve("애플").ticker == "AAPL"
    assert symbol_map.resolve("애플").currency == "USD"


def test_many_names_map_to_one_ticker(symbol_map):
    assert symbol_map.resolve("AMD").ticker == "AMD"
    assert symbol_map.resolve("Advanced Micro Devic").ticker == "AMD"


def test_unknown_name_raises(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError):
        symbol_map.resolve("없는종목")


def test_resolve_all_reports_every_miss_at_once(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError) as excinfo:
        symbol_map.resolve_all(["애플", "없는종목1", "없는종목2"])
    assert excinfo.value.names == ["없는종목1", "없는종목2"]


def test_error_carries_a_paste_ready_stub(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError) as excinfo:
        symbol_map.resolve_all(["없는종목1"])
    # The stub should be valid YAML that can be appended to symbols.yaml.
    # ??? needs to be quoted because it's a YAML indicator character.
    assert "- {name: 없는종목1, ticker: '???', currency: '???'}" in excinfo.value.stub


def test_currency_of_ticker(symbol_map):
    assert symbol_map.currency_of("005930.KS") == "KRW"


def test_conflicting_currency_for_one_ticker_is_rejected(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(
        "- {name: A, ticker: X, currency: USD}\n- {name: B, ticker: X, currency: KRW}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conflicting currency"):
        symbols.load(str(path))


def test_shipped_symbols_file_loads():
    symbols.load("subprojects/nav/symbols.yaml")


def test_stub_with_adversarial_names_is_parseable(tmp_path):
    """Verify stubs with special YAML characters can be appended to symbols.yaml."""
    import yaml

    path = tmp_path / "symbols.yaml"
    path.write_text("", encoding="utf-8")
    smap = symbols.SymbolMap([])

    # Test names with various special YAML characters
    adversarial_names = [
        "Series A: Class B",          # colon
        "Foo, Inc.",                  # comma
        "Test # Fund",                # hash/comment character
        "  Leading Space",            # leading space
        "Trailing Space  ",           # trailing space
        "Korean 종목",                 # Korean name
        "Mixed: Korean, 종목",         # multiple special chars with Korean
    ]

    for name in adversarial_names:
        try:
            smap.resolve(name)
        except symbols.UnknownSymbolError as e:
            # Try to parse the generated stub
            parsed = yaml.safe_load(e.stub)
            assert parsed is not None, f"Stub failed to parse for name: {name}"
            assert len(parsed) == 1, f"Stub should have one entry for name: {name}"
            # Most important: verify the name roundtrips exactly
            assert parsed[0]["name"] == name, (
                f"Name was mangled. Original: {name!r}, "
                f"parsed: {parsed[0]['name']!r}"
            )
            assert parsed[0]["ticker"] == "???", "Ticker placeholder should be quoted"
            assert parsed[0]["currency"] == "???", "Currency placeholder should be quoted"


def test_duplicate_name_with_different_ticker_is_rejected(tmp_path):
    """Verify that the same name cannot map to different tickers."""
    path = tmp_path / "symbols.yaml"
    path.write_text(
        "- {name: Ambiguous, ticker: X, currency: USD}\n"
        "- {name: Ambiguous, ticker: Y, currency: USD}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate name.*Ambiguous"):
        symbols.load(str(path))


def test_duplicate_name_with_different_currency_is_rejected(tmp_path):
    """Verify that the same name cannot map to different currencies."""
    path = tmp_path / "symbols.yaml"
    path.write_text(
        "- {name: BadMerge, ticker: X, currency: USD}\n"
        "- {name: BadMerge, ticker: X, currency: KRW}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate name.*BadMerge"):
        symbols.load(str(path))


def test_exact_duplicate_name_is_allowed(tmp_path):
    """Verify that exact duplicates (same name, ticker, currency) are allowed."""
    path = tmp_path / "symbols.yaml"
    path.write_text(
        "- {name: Apple, ticker: AAPL, currency: USD}\n"
        "- {name: Apple, ticker: AAPL, currency: USD}\n",
        encoding="utf-8",
    )
    # Should not raise
    smap = symbols.load(str(path))
    assert smap.resolve("Apple").ticker == "AAPL"
