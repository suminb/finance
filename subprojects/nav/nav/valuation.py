"""The daily NAV series."""

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Iterable, List

import pandas as pd

from finance.ext.models import QUANTITY_EPSILON, Portfolio, is_cash

from nav.model import cash_ticker

COLUMNS = [
    "date",
    "nav_krw",
    "nav_usd",
    "holdings_krw",
    "cash_krw",
    "cash_usd",
    "fx_usdkrw",
    "stale",
]


def daily_dates(start: date_type, end: date_type) -> List[datetime]:
    """Every day from start to end inclusive, as UTC midnights."""
    days = (end - start).days
    return [
        datetime.combine(start + timedelta(days=i), time(0, 0, 0)).replace(
            tzinfo=timezone.utc
        )
        for i in range(days + 1)
    ]


def holdings_at(portfolio: Portfolio, when: datetime, prices: Dict[str, float]) -> List[dict]:
    """Open positions and cash at a point in time, with base-currency weights."""
    inventory = portfolio.eval_inventory(when)
    rows = []
    for ticker, quantity in inventory.items():
        if abs(quantity) < QUANTITY_EPSILON:
            continue
        value = prices[ticker] * quantity
        rows.append(
            {
                "ticker": ticker,
                "quantity": float(quantity),
                "price_krw": float(prices[ticker]),
                "value_krw": float(value),
                "is_cash": is_cash(ticker),
            }
        )
    total = sum(row["value_krw"] for row in rows)
    for row in rows:
        row["weight"] = row["value_krw"] / total if total else 0.0
    return sorted(rows, key=lambda r: -r["value_krw"])


def build(
    portfolio: Portfolio,
    dates: Iterable[datetime],
    prices_by_date: Dict[datetime, Dict[str, float]],
    stale_by_date: Dict[datetime, List[str]],
    base: str = "KRW",
    report_currency: str = "USD",
) -> pd.DataFrame:
    """NAV per day, in the base currency and in the reporting currency."""
    base_cash = cash_ticker(base)
    report_cash = cash_ticker(report_currency)

    rows = []
    for when in dates:
        prices = prices_by_date[when]
        inventory = portfolio.eval_inventory(when)
        rate = prices[report_cash]

        holdings = 0.0
        for ticker, quantity in inventory.items():
            if abs(quantity) < QUANTITY_EPSILON or is_cash(ticker):
                continue
            holdings += prices[ticker] * quantity

        nav = portfolio.eval_nav(when, prices)
        rows.append(
            {
                "date": when,
                "nav_krw": nav,
                "nav_usd": nav / rate,
                "holdings_krw": holdings,
                "cash_krw": float(inventory.get(base_cash, 0.0)),
                "cash_usd": float(inventory.get(report_cash, 0.0)),
                "fx_usdkrw": float(rate),
                "stale": ",".join(stale_by_date.get(when, [])),
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)
