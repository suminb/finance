import decimal

from finance.providers.miraeasset import Miraeasset, Record

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


def test_quantity_descriptor_accepts_fractional_strings():
    """Verify that a fractional quantity string is converted to Decimal, not truncated."""
    r = Record(
        created_at="2026/09/01",
        seq=1,
        category="현금매수",
        amount="1500.00",
        currency="USD",
        code="AAPL",
        name="애플",
        unit_price="150.00",
        quantity="0.5",
        fees="0",
        tax="0",
        raw_columns=[""] * 25,
    )
    assert r.quantity == decimal.Decimal("0.5")
    assert isinstance(r.quantity, decimal.Decimal)


def test_values_exports_fractional_quantity_as_number():
    """Verify that Record.values() exports fractional quantity as a number, not a string."""
    r = Record(
        created_at="2026/09/01",
        seq=1,
        category="현금매수",
        amount="1500.00",
        currency="USD",
        code="AAPL",
        name="애플",
        unit_price="150.00",
        quantity="0.5",
        fees="0",
        tax="0",
        raw_columns=[""] * 25,
    )
    values_list = list(r.values())
    # Find the quantity value in the values list (should be at the same index as 'quantity' in attributes)
    quantity_index = r.attributes.index("quantity")
    quantity_value = values_list[quantity_index]
    assert quantity_value == decimal.Decimal("0.5")
    assert not isinstance(quantity_value, str)
