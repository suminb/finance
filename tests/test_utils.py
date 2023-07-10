import os
import re
import types
from datetime import datetime, timedelta

import pytest
from finance.models import Asset
from finance.utils import (
    DictReader,
    date_range,
    date_to_datetime,
    extract_numbers,
    insert_stock_record,
    parse_date,
    parse_datetime,
    parse_decimal,
    parse_dollar_value,
    parse_int,
    parse_stock_code,
    parse_stock_records,
    serialize_datetime,
)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, ".."))


def test_date_range():
    start, end = parse_date("2016-01-01"), parse_date("2016-01-15")
    r = date_range(start, end)
    assert isinstance(r, types.GeneratorType)

    r = list(r)
    assert 14 == len(r)
    assert r[0] == parse_date("2016-01-01")
    assert r[13] == parse_date("2016-01-14")


@pytest.mark.parametrize(
    "start, end, count",
    [
        (0, 0, 0),
        (-1, 0, 1),
        (-10, 0, 10),
        (-1, -1, 0),
        (-10, -5, 5),
    ],
)
def test_date_range_relative(start, end, count):
    r = date_range(start, end)

    try:
        prev_date = next(r)
    except StopIteration:
        n = 0
    else:
        n = 1

    for date in r:
        assert prev_date < date
        n += 1

    assert n == count


@pytest.mark.parametrize(
    "start, end",
    [
        ("2016-01-01", "2015-01-01"),
        (0, -1),
    ],
)
def test_date_range_exceptions(start, end):
    with pytest.raises(ValueError):
        list(date_range(start, end))

    with pytest.raises(NotImplementedError):
        list(date_range(start, end, 2))


def test_date_to_datetime():
    date = parse_date("2018-01-13")
    dt_beginning = parse_datetime("2018-01-13 00:00:00")
    dt_end = parse_datetime("2018-01-13 23:59:59")

    assert date_to_datetime(date) == dt_beginning
    assert date_to_datetime(date, True) == dt_end


def test_dict_reader():
    d = DictReader({"key": "value"})
    assert d["key"] == "value"
    assert d.key == "value"


def test_extract_numbers():
    assert "160" == extract_numbers("160")
    assert "1694" == extract_numbers("1,694")
    assert "1806" == extract_numbers("1,806 원")

    assert 170 == extract_numbers("170", int)
    assert 3925321 == extract_numbers("3,925,321", int)

    assert 150.25 == extract_numbers("150.25", float)

    with pytest.raises(TypeError):
        extract_numbers(1)

    with pytest.raises(TypeError):
        extract_numbers(b"\x00")


def test_insert_stock_record(session, account_stock, account_checking):
    data = {
        "date": parse_date("2016-06-30"),
        "sequence": 1,
        "category1": "장내매수",
        "category2": "매수",
        "code": "005380",
        "name": "현대차",
        "unit_price": 136000,
        "quantity": 10,
        "subtotal": 1360000,
        "interest": 0,
        "fees": 200,
        "late_fees": 0,
        "channel": "",
        "final_amount": 1670200,
    }
    asset = Asset.create(type="stock", code="005380.KS", description="현대차")
    record = insert_stock_record(data, account_stock, account_checking)

    # TODO: Automate this process
    session.delete(record)
    session.delete(asset)
    session.commit()


def test_parse_date():
    date = parse_date("2016-06-06")
    assert date.strftime("%Y-%m-%d") == "2016-06-06"

    delta = parse_date(7) - parse_date(2)
    assert delta == timedelta(days=5)


def test_parse_datetime():
    dt = parse_datetime("2018-01-13 01:18:12")
    assert dt.strftime("%Y-%m-%d %H:%M:%S") == "2018-01-13 01:18:12"

    at = datetime.now()
    delta = parse_datetime(3600, at) - parse_datetime(1200, at)
    assert delta == timedelta(seconds=2400)


def test_parse_decimal():
    assert parse_decimal("1.1") == 1.1
    assert parse_decimal(1) == 1.0

    assert parse_decimal("a") == 0
    assert parse_decimal("a", fallback_to=1) == 1


def test_parse_int():
    assert parse_int(1) == 1
    assert parse_int("1") == 1

    assert parse_int("1.1") == 0
    assert parse_int("1.1", fallback_to=2) == 2


def test_parse_dollar_value():
    assert parse_dollar_value("$123.45") == 123.45
    assert parse_dollar_value("75.24") == 75.24
    assert parse_dollar_value(35.00) == 35.00


@pytest.mark.parametrize(
    "code, result",
    [
        ("A145210", "145210"),
        ("051500", "051500"),
        ("", None),
    ],
)
def test_parse_stock_code(code, result):
    assert parse_stock_code(code) == result


def test_parse_stock_records():
    sample_file = "tests/samples/shinhan_stock_records.csv"
    flag = True
    expected_keys = (
        "date",
        "sequence",
        "category1",
        "category2",
        "code",
        "name",
        "quantity",
        "unit_price",
        "subtotal",
        "interest",
        "fees",
        "late_fees",
        "channel",
        "final_amount",
    )
    expected_types = {
        "date": datetime,
        "sequence": int,
        "unit_price": int,
        "quantity": int,
        "subtotal": int,
        "interest": int,
        "fees": int,
        "late_fees": int,
        "final_amount": int,
    }

    with open(sample_file) as fin:
        for data in parse_stock_records(fin):
            flag = False
            for key in expected_keys:
                assert key in data

            for k, t in expected_types.items():
                assert isinstance(data[k], t)

            # It should be either a six-digit code or None
            assert data["code"] is None or re.match(r"^\d{6}$", data["code"])

            # print(data['date'], data['sequence'], data['category1'],
            #       data['category2'], data['code'], data['name'],
            #       data['unit_price'], data['quantity'], data['subtotal'],
            #       data['final_amount'])

    if flag:
        pytest.fail("No data was read.")


def test_serialize_datetime():
    now = datetime.now()
    serialized = serialize_datetime(now)
    # e.g., 2018-04-01T03:13:50.266116
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}", serialized)

    with pytest.raises(TypeError):
        serialize_datetime(None)
    with pytest.raises(TypeError):
        serialize_datetime("test")
