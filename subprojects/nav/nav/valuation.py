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


class UnrepresentableCurrencyError(ValueError):
    """A cash balance the fixed output columns cannot show.

    COLUMNS carries exactly two cash columns, cash_krw and cash_usd, while
    nav_krw sums the whole inventory. A balance in any third currency would
    therefore be counted in the total and missing from the breakdown, so the
    two would not agree -- a report that does not sum to its own total is
    precisely the silent wrongness this design exists to prevent.

    A holding priced in a third currency is fine and needs no error: it is
    converted into the base currency and lands in holdings_krw with the rest.
    Only *cash* has a per-currency column to fall out of.
    """


def daily_dates(start: date_type, end: date_type) -> List[datetime]:
    """Every day from start to end inclusive, as UTC midnights.

    An empty range is a hard error rather than an empty list. The only way to
    reach one is a seed_date after today -- a mistyped year in hand-authored
    YAML -- and returning [] let `sync` persist an empty nav_daily.parquet and
    only then die on `frame.iloc[-1]`, leaving a file on disk that made every
    later `nav show` fail its way past the friendly "run `nav sync` first".
    """
    if end < start:
        raise ValueError(
            "empty date range: end {} is before start {}".format(end, start)
        )
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
    representable = {base_cash, report_cash}

    rows = []
    for when in dates:
        prices = prices_by_date[when]
        inventory = portfolio.eval_inventory(when)
        rate = prices[report_cash]

        unrepresentable = sorted(
            ticker
            for ticker, quantity in inventory.items()
            if is_cash(ticker)
            and ticker not in representable
            and abs(quantity) >= QUANTITY_EPSILON
        )
        if unrepresentable:
            raise UnrepresentableCurrencyError(
                "Cash held in {} on {}, but the daily series has columns only "
                "for {} and {}. That balance would be counted in nav_{} and "
                "missing from the breakdown, so the two would not agree. "
                "Convert it, or add a column for it to valuation.COLUMNS and "
                "build().".format(
                    ", ".join(t.lstrip("_") for t in unrepresentable),
                    pd.Timestamp(when).date(),
                    base,
                    report_currency,
                    base.lower(),
                )
            )

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
