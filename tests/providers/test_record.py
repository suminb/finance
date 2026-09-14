import decimal

import pytest

from finance.providers.record import Decimal as DecimalField
from finance.providers.record import Integer as IntegerField


class Holder:
    amount = DecimalField()
    count = IntegerField()


def test_decimal_field_accepts_thousands_separators():
    h = Holder()
    h.amount = "1,500.00"
    assert h.amount == decimal.Decimal("1500.00")


def test_decimal_field_accepts_plain_values():
    h = Holder()
    h.amount = "42.5"
    assert h.amount == decimal.Decimal("42.5")


def test_decimal_field_accepts_numeric_types():
    h = Holder()
    h.amount = 7
    assert h.amount == decimal.Decimal(7)


def test_decimal_field_treats_blank_as_zero():
    h = Holder()
    h.amount = ""
    assert h.amount == decimal.Decimal(0)


def test_integer_field_accepts_thousands_separators():
    h = Holder()
    h.count = "1,200"
    assert h.count == 1200


def test_integer_field_rejects_garbage():
    h = Holder()
    with pytest.raises(decimal.InvalidOperation):
        h.count = "abc"
