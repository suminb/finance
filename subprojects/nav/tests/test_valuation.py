from datetime import date, datetime, timezone

import pytest

from finance.ext.models import Portfolio
from nav import valuation


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def portfolio():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "_USD", 500.0),
        Portfolio.Transaction(utc(1), "_KRW", 1000000.0),
    ]
    return Portfolio({}, {}, legs, base_currency="KRW")


PRICES = {
    utc(2): {"AAPL": 150.0 * 1300.0, "_USD": 1300.0, "_KRW": 1.0},
    utc(3): {"AAPL": 150.0 * 1400.0, "_USD": 1400.0, "_KRW": 1.0},
}
STALE = {utc(2): [], utc(3): ["AAPL"]}


def test_daily_dates_is_inclusive_of_start_and_end():
    dates = valuation.daily_dates(date(2026, 9, 1), date(2026, 9, 3))
    assert dates == [utc(1), utc(2), utc(3)]


def test_nav_krw_sums_holdings_and_cash():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    row = frame.iloc[0]
    assert row["holdings_krw"] == pytest.approx(10 * 150.0 * 1300.0)
    assert row["cash_krw"] == pytest.approx(1000000.0)
    assert row["cash_usd"] == pytest.approx(500.0)
    assert row["nav_krw"] == pytest.approx(1950000.0 + 1000000.0 + 650000.0)


def test_nav_usd_is_nav_krw_over_the_rate():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    row = frame.iloc[0]
    assert row["nav_usd"] == pytest.approx(row["nav_krw"] / 1300.0)


def test_fx_only_move_changes_nav_without_changing_positions():
    frame = valuation.build(portfolio(), [utc(2), utc(3)], PRICES, STALE)
    assert frame.iloc[1]["nav_krw"] > frame.iloc[0]["nav_krw"]
    assert frame.iloc[1]["holdings_krw"] == pytest.approx(10 * 150.0 * 1400.0)


def test_stale_symbols_are_recorded():
    frame = valuation.build(portfolio(), [utc(2), utc(3)], PRICES, STALE)
    assert frame.iloc[0]["stale"] == ""
    assert frame.iloc[1]["stale"] == "AAPL"


def test_columns_are_exactly_as_declared():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    assert list(frame.columns) == valuation.COLUMNS


def test_holdings_at_reports_weights():
    holdings = valuation.holdings_at(portfolio(), utc(2), PRICES[utc(2)])
    by_ticker = {h["ticker"]: h for h in holdings}
    assert by_ticker["AAPL"]["quantity"] == pytest.approx(10.0)
    assert by_ticker["AAPL"]["value_krw"] == pytest.approx(1950000.0)
    assert sum(h["weight"] for h in holdings) == pytest.approx(1.0)


def test_holdings_at_omits_closed_positions():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "AAPL", -10.0),
        Portfolio.Transaction(utc(1), "_KRW", 100.0),
    ]
    pf = Portfolio({}, {}, legs, base_currency="KRW")
    tickers = {h["ticker"] for h in valuation.holdings_at(pf, utc(2), {"_KRW": 1.0})}
    assert tickers == {"_KRW"}
