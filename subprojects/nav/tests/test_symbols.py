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
    assert "- {name: 없는종목1, ticker: ???, currency: ???}" in excinfo.value.stub


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
