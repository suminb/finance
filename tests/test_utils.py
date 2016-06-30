from datetime import timedelta
import os
import re
import types

import pytest

from finance.utils import *  # noqa


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, '..'))


def test_date_range():
    start, end = parse_date('2016-01-01'), parse_date('2016-01-15')
    r = date_range(start, end)
    assert isinstance(r, types.GeneratorType)

    r = list(r)
    assert 14 == len(r)
    assert r[0] == parse_date('2016-01-01')
    assert r[13] == parse_date('2016-01-14')


@pytest.mark.parametrize('start, end, count', [
    (0, 0, 0),
    (-1, 0, 1),
    (-10, 0, 10),
    (-1, -1, 0),
    (-10, -5, 5),
])
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


@pytest.mark.parametrize('start, end', [
    ('2016-01-01', '2015-01-01'),
    (0, -1),
])
def test_date_range_exceptions(start, end):
    with pytest.raises(ValueError):
        [x for x in date_range(start, end)]


def test_extract_numbers():
    assert '160' == extract_numbers('160')
    assert '1694' == extract_numbers('1,694')
    assert '1806' == extract_numbers('1,806 원')

    assert 170 == extract_numbers('170', int)
    assert 3925321 == extract_numbers('3,925,321', int)

    assert 150.25 == extract_numbers('150.25', float)

    with pytest.raises(TypeError):
        extract_numbers(1)

    with pytest.raises(TypeError):
        extract_numbers(b'\x00')


def test_parse_date():
    date = parse_date('2016-06-06')
    assert date.strftime('%Y-%m-%d') == '2016-06-06'

    delta = parse_date(7) - parse_date(2)
    assert delta == timedelta(days=5)


def test_parse_decimal():
    assert parse_decimal('1.1') == 1.1
    assert parse_decimal(1) == 1.0


@pytest.mark.parametrize('code, result', [
    ('A145210', '145210'),
    ('051500', '051500'),
    ('', None),
])
def test_parse_stock_code(code, result):
    assert parse_stock_code(code) == result


def test_parse_stock_data():
    sample_file = 'tests/data/stocks.csv'
    flag = True
    expected_keys = ('date', 'sequence', 'category1', 'category2', 'code',
                     'name', 'quantity', 'unit_price', 'subtotal', 'interest',
                     'fees', 'late_fees', 'channel', 'final_amount')
    expected_types = {
        'date': datetime,
        'sequence': int,
        'unit_price': int,
        'quantity': int,
        'subtotal': int,
        'interest': int,
        'fees': int,
        'late_fees': int,
        'final_amount': int,
    }

    with open(sample_file) as fin:
        for data in parse_stock_data(fin):
            flag = False
            for key in expected_keys:
                assert key in data

            for k, t in expected_types.items():
                assert isinstance(data[k], t)

            # It should be either a six-digit code or None
            assert data['code'] is None or re.match(r'^\d{6}$', data['code'])

            # print(data['date'], data['sequence'], data['category1'],
            #       data['category2'], data['code'], data['name'],
            #       data['unit_price'], data['quantity'], data['subtotal'],
            #       data['final_amount'])

    if flag:
        pytest.fail('No data was read.')
