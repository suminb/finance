import decimal

from finance.providers.miraeasset import Miraeasset

SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"


def records():
    return list(Miraeasset().read_records(SAMPLE))


def test_reads_every_row():
    assert len(records()) == 4


def test_parses_comma_separated_amount():
    assert records()[0].amount == decimal.Decimal("1500.00")


def test_parses_fractional_quantity():
    rs = records()
    assert rs[0].quantity == decimal.Decimal(10)
    assert isinstance(rs[0].quantity, decimal.Decimal)


def test_parses_category_and_currency():
    r = records()[0]
    assert r.category == "현금매수"
    assert r.currency == "USD"


def test_parses_date():
    assert records()[0].created_at.strftime("%Y-%m-%d") == "2026-09-01"


def test_keeps_raw_columns():
    assert len(records()[0].raw_columns) == 25
