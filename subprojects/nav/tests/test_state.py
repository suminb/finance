"""nav.state: where the files are, and which currencies are in play."""

from datetime import datetime, timezone
from decimal import Decimal

import click
import pytest
import yaml

from nav import state
from nav.model import Transaction
from nav.seed import Seed
from nav.symbols import Symbol, SymbolMap

SYMBOL_MAP = SymbolMap(
    [
        Symbol(name="애플", ticker="AAPL", currency="USD"),
        Symbol(name="삼성전자보통주", ticker="005930.KS", currency="KRW"),
        Symbol(name="넥슨 일본", ticker="3659.T", currency="JPY"),
    ]
)


def seed(positions=None, cash=None, seed_date=None):
    return Seed(
        seed_date=seed_date or datetime(2026, 9, 1).date(),
        positions={t: Decimal(str(q)) for t, q in (positions or {}).items()},
        cash={c: Decimal(str(a)) for c, a in (cash or {}).items()},
    )


def transaction(ticker="", currency="KRW", seq=1):
    return Transaction(
        date=datetime(2026, 9, 2, tzinfo=timezone.utc),
        seq=seq,
        category="입금",
        name="",
        ticker=ticker,
        currency=currency,
        amount=Decimal("1"),
        unit_price=Decimal("0"),
        quantity=Decimal("0"),
        fees=Decimal("0"),
        tax=Decimal("0"),
        raw="[]",
    )


def test_base_and_report_currencies_are_always_present():
    """Even an account with nothing in it needs KRW and USD priced."""
    assert state.account_currencies(seed(), [], SYMBOL_MAP) == ["KRW", "USD"]


def test_seed_cash_currencies_feed_the_set():
    """A three-currency seed. extra_currencies=["USD"] was hardcoded, so a

    JPY balance had no rate fetched at all.
    """
    account = seed(cash={"KRW": 1000000, "USD": 500, "JPY": 30000})
    assert state.account_currencies(account, [], SYMBOL_MAP) == ["JPY", "KRW", "USD"]


def test_the_currency_of_a_held_ticker_feeds_the_set():
    """symbols.yaml ships 넥슨 일본 -> 3659.T, JPY; holding it needs JPYKRW=X."""
    account = seed(positions={"3659.T": 100})
    assert state.account_currencies(account, [], SYMBOL_MAP) == ["JPY", "KRW", "USD"]


def test_a_ledger_row_in_a_third_currency_feeds_the_set():
    """A 입금 in JPY creates a _JPY balance with no JPY ticker held anywhere."""
    assert state.account_currencies(
        seed(), [transaction(currency="JPY")], SYMBOL_MAP
    ) == ["JPY", "KRW", "USD"]


def test_a_held_ticker_missing_from_symbols_yaml_is_a_clean_error():
    account = seed(positions={"GONE": 5})
    with pytest.raises(click.ClickException, match="no longer listed"):
        state.account_currencies(account, [], SYMBOL_MAP)


def test_required_symbols_follows_the_derived_set():
    """End of the chain: a JPY holding actually gets its rate fetched."""
    from nav import prices

    account = seed(positions={"3659.T": 100}, cash={"KRW": 1})
    currencies = state.account_currencies(account, [], SYMBOL_MAP)
    assert prices.required_symbols(
        ["3659.T"], SYMBOL_MAP, state.BASE_CURRENCY, extra_currencies=currencies
    ) == ["3659.T", "JPYKRW=X", "USDKRW=X"]


def test_paths_are_all_under_the_root(tmp_path):
    p = state.paths(str(tmp_path))
    assert set(p) == {"symbols", "categories", "seed", "transaction", "nav_daily"}
    assert all(v.startswith(str(tmp_path)) for v in p.values())


def test_read_historical_names_what_creates_the_file(tmp_path):
    with pytest.raises(click.ClickException, match="nav sync"):
        state.read_historical(str(tmp_path / "absent.parquet"))


def test_require_file_passes_an_existing_path_through(tmp_path):
    path = tmp_path / "there.yaml"
    path.write_text(yaml.safe_dump([]), encoding="utf-8")
    assert state.require_file(str(path), "there.yaml", "hint") == str(path)
