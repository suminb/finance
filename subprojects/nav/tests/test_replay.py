from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from nav import categories, replay
from nav.model import Transaction
from nav.seed import Seed

CATEGORIES_YAML = """
- {category: 현금매수, handler: buy}
- {category: 배당금, handler: dividend}
"""


@pytest.fixture
def category_map(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(CATEGORIES_YAML, encoding="utf-8")
    return categories.load(str(path))


SEED = Seed(
    seed_date=date(2026, 9, 10),
    positions={"AAPL": Decimal("10")},
    cash={"KRW": Decimal("1000000"), "USD": Decimal("500")},
)


def txn(day, category="현금매수", **kwargs):
    defaults = dict(
        date=datetime(2026, 9, day, tzinfo=timezone.utc),
        seq=1,
        category=category,
        name="애플",
        ticker="AAPL",
        currency="USD",
        amount=Decimal("300"),
        unit_price=Decimal("150"),
        quantity=Decimal("2"),
        fees=Decimal("1"),
        tax=Decimal("0"),
        raw="[]",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_seed_legs_cover_positions_and_every_currency():
    legs = replay.seed_legs(SEED)
    assert {(leg.ticker, leg.quantity) for leg in legs} == {
        ("AAPL", 10.0),
        ("_KRW", 1000000.0),
        ("_USD", 500.0),
    }


def test_seed_legs_are_dated_at_the_seed_date():
    assert all(
        leg.date == datetime(2026, 9, 10, tzinfo=timezone.utc)
        for leg in replay.seed_legs(SEED)
    )


def test_transactions_on_or_before_the_seed_date_are_dropped(category_map):
    legs = replay.transaction_legs([txn(9), txn(10)], category_map, after=SEED.seed_date)
    assert legs == []


def test_transactions_after_the_seed_date_are_kept(category_map):
    legs = replay.transaction_legs([txn(11)], category_map, after=SEED.seed_date)
    assert [(leg.ticker, leg.quantity) for leg in legs] == [
        ("AAPL", 2.0),
        ("_USD", -301.0),
    ]


def test_portfolio_replays_seed_plus_transactions(category_map):
    pf = replay.build_portfolio(SEED, [txn(11)], category_map)
    inventory = pf.eval_inventory(datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 12.0
    assert inventory["_USD"] == pytest.approx(199.0)
    assert inventory["_KRW"] == 1000000.0


def test_portfolio_before_a_transaction_shows_only_the_seed(category_map):
    pf = replay.build_portfolio(SEED, [txn(11)], category_map)
    inventory = pf.eval_inventory(datetime(2026, 9, 10, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 10.0
    assert inventory["_USD"] == 500.0


def test_dividend_credits_cash_without_touching_the_position(category_map):
    pf = replay.build_portfolio(
        SEED,
        [txn(11, category="배당금", amount=Decimal("12.30"), tax=Decimal("1.84"),
             quantity=Decimal("0"))],
        category_map,
    )
    inventory = pf.eval_inventory(datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 10.0
    assert inventory["_USD"] == pytest.approx(510.46)


def test_base_currency_is_krw_by_default(category_map):
    assert replay.build_portfolio(SEED, [], category_map).cash_ticker == "_KRW"
