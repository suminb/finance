from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from finance.ext.models import Portfolio
from nav import check
from nav.seed import Seed


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def portfolio():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "_KRW", 1000.0),
    ]
    return Portfolio({}, {}, legs, base_currency="KRW")


def statement(**kwargs):
    defaults = dict(
        seed_date=date(2026, 9, 2),
        positions={"AAPL": Decimal("10")},
        cash={"KRW": Decimal("1000")},
    )
    defaults.update(kwargs)
    return Seed(**defaults)


def test_no_differences_when_everything_agrees():
    assert check.compare(portfolio(), statement(), utc(2)) == []


def test_reports_a_quantity_mismatch():
    diffs = check.compare(portfolio(), statement(positions={"AAPL": Decimal("20")}), utc(2))
    assert len(diffs) == 1
    assert diffs[0].ticker == "AAPL"
    assert diffs[0].computed == 10.0
    assert diffs[0].actual == 20.0
    assert diffs[0].delta == 10.0


def test_reports_a_cash_mismatch():
    diffs = check.compare(portfolio(), statement(cash={"KRW": Decimal("900")}), utc(2))
    assert [d.ticker for d in diffs] == ["_KRW"]
    assert diffs[0].delta == -100.0


def test_reports_a_position_missing_from_the_statement():
    diffs = check.compare(portfolio(), statement(positions={}), utc(2))
    assert diffs[0].ticker == "AAPL"
    assert diffs[0].actual == 0.0


def test_reports_a_position_missing_from_the_replay():
    diffs = check.compare(
        portfolio(), statement(positions={"AAPL": Decimal("10"), "TSLA": Decimal("5")}), utc(2)
    )
    assert [d.ticker for d in diffs] == ["TSLA"]
    assert diffs[0].computed == 0.0


def test_tiny_rounding_differences_are_ignored():
    diffs = check.compare(
        portfolio(), statement(cash={"KRW": Decimal("1000.0000001")}), utc(2)
    )
    assert diffs == []


HISTORICAL = pd.DataFrame(
    [
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-01"), "close": 100.0},
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-02"), "close": 25.0},
        {"symbol": "TSLA", "date": pd.Timestamp("2026-09-01"), "close": 100.0},
        {"symbol": "TSLA", "date": pd.Timestamp("2026-09-02"), "close": 103.0},
    ]
)


def test_suspicious_moves_flags_a_probable_split():
    moves = check.suspicious_moves(HISTORICAL, ["AAPL", "TSLA"])
    assert [m["symbol"] for m in moves] == ["AAPL"]
    assert moves[0]["ratio"] < -0.7


def test_suspicious_moves_ignores_ordinary_days():
    assert check.suspicious_moves(HISTORICAL, ["TSLA"]) == []
