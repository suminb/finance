from datetime import date
from decimal import Decimal

import pytest

from nav import seed, symbols

SYMBOLS_YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""

SEED_YAML = """
seed_date: 2026-09-14
positions:
  - {ticker: AAPL, quantity: 10}
  - {ticker: 005930.KS, quantity: 100}
cash:
  KRW: 1234567
  USD: 890.12
"""


@pytest.fixture
def symbol_map(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(SYMBOLS_YAML, encoding="utf-8")
    return symbols.load(str(path))


def write(tmp_path, text):
    path = tmp_path / "seed.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_loads_positions_and_cash(tmp_path, symbol_map):
    s = seed.load(write(tmp_path, SEED_YAML), symbol_map)
    assert s.seed_date == date(2026, 9, 14)
    assert s.positions == {"AAPL": Decimal("10"), "005930.KS": Decimal("100")}
    assert s.cash == {"KRW": Decimal("1234567"), "USD": Decimal("890.12")}


def test_cash_amounts_are_exact(tmp_path, symbol_map):
    s = seed.load(write(tmp_path, SEED_YAML), symbol_map)
    assert s.cash["USD"] == Decimal("890.12")


def test_unknown_ticker_is_rejected(tmp_path, symbol_map):
    text = "seed_date: 2026-09-14\npositions:\n  - {ticker: NOPE, quantity: 1}\ncash: {KRW: 0}\n"
    with pytest.raises(ValueError, match="NOPE"):
        seed.load(write(tmp_path, text), symbol_map)


def test_missing_seed_date_is_rejected(tmp_path, symbol_map):
    text = "positions: []\ncash: {KRW: 0}\n"
    with pytest.raises(ValueError, match="seed_date"):
        seed.load(write(tmp_path, text), symbol_map)


def test_empty_positions_are_allowed(tmp_path, symbol_map):
    text = "seed_date: 2026-09-14\npositions: []\ncash: {KRW: 100}\n"
    assert seed.load(write(tmp_path, text), symbol_map).positions == {}


def test_example_file_loads(symbol_map):
    seed.load("subprojects/nav/seed.example.yaml", symbol_map)
