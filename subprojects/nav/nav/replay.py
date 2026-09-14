"""Seed plus transactions into a replayable Portfolio."""

from datetime import date as date_type
from datetime import datetime, time, timezone
from typing import Iterable, List

from finance.ext.models import Portfolio

from nav.categories import CategoryMap
from nav.model import Transaction, cash_ticker
from nav.seed import Seed


def _at_utc(value: date_type) -> datetime:
    return datetime.combine(value, time(0, 0, 0)).replace(tzinfo=timezone.utc)


def seed_legs(seed: Seed) -> List[Portfolio.Transaction]:
    """Opening balances as transactions dated at the seed date."""
    when = _at_utc(seed.seed_date)
    legs = [
        Portfolio.Transaction(when, ticker, float(quantity))
        for ticker, quantity in seed.positions.items()
    ]
    legs += [
        Portfolio.Transaction(when, cash_ticker(currency), float(amount))
        for currency, amount in seed.cash.items()
    ]
    return legs


def transaction_legs(
    transactions: Iterable[Transaction], category_map: CategoryMap, after: date_type
) -> List[Portfolio.Transaction]:
    """Legs for transactions dated strictly after the seed date.

    The seed states the closing 잔고 of its date, so that day's transactions are
    already reflected in it.
    """
    legs = []
    for transaction in transactions:
        if transaction.date.date() <= after:
            continue
        for leg in category_map.legs_for(transaction):
            legs.append(
                Portfolio.Transaction(transaction.date, leg.ticker, float(leg.quantity))
            )
    return legs


def build_portfolio(
    seed: Seed,
    transactions: Iterable[Transaction],
    category_map: CategoryMap,
    base_currency: str = "KRW",
) -> Portfolio:
    legs = seed_legs(seed) + transaction_legs(
        transactions, category_map, after=seed.seed_date
    )
    legs.sort(key=lambda leg: leg.date)
    return Portfolio({}, {}, legs, base_currency=base_currency)
