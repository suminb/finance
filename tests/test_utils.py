import os
import types

import pytest

from finance.utils import (
    date_range, extract_numbers, make_date, parse_8percent_data)


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, '..'))


def test_date_range():
    start, end = make_date('2016-01-01'), make_date('2016-01-15')
    r = date_range(start, end)
    assert isinstance(r, types.GeneratorType)

    r = list(r)
    assert 14 == len(r)
    assert r[0] == make_date('2016-01-01')
    assert r[13] == make_date('2016-01-14')


def test_extract_numbers():
    assert '160' == extract_numbers('160')
    assert '1694' == extract_numbers('1,694')
    assert '1806' == extract_numbers('1,806 원')

    assert 170 == extract_numbers('170', int)
    assert 3925321 == extract_numbers('3,925,321', int)

    assert 150.25 == extract_numbers('150.25', float)


def test_parse_8percent_data():
    sample_file = os.path.join(PROJECT_PATH, 'sample-data',
                               '8percent-829.html')
    with open(sample_file) as fin:
        raw = fin.read()

    data = [
        ('2016-04-11', 612, 160, 1694, 340),
        ('2016-05-11', 390, 90, 1916, 0),
        ('2016-06-13', 386, 90, 1920, 0),
        ('2016-07-11', 324, 80, 1982, 0),
        ('2016-08-10', 343, 80, 1963, 0),
        ('2016-09-12', 327, 80, 1979, 0),
        ('2016-10-10', 301, 70, 2005, 0),
        ('2016-11-14', 314, 70, 1992, 0),
        ('2016-12-12', 252, 60, 2054, 0),
        ('2017-01-10', 262, 60, 2044, 0),
        ('2017-02-13', 253, 60, 2053, 0),
        ('2017-03-13', 207, 50, 2099, 0),
        ('2017-04-10', 205, 50, 2101, 0),
        ('2017-05-15', 208, 50, 2098, 0),
        ('2017-06-12', 161, 40, 2145, 0),
        ('2017-07-10', 155, 30, 2151, 0),
        ('2017-08-14', 153, 30, 2153, 0),
        ('2017-09-11', 118, 20, 2188, 0),
        ('2017-10-11', 108, 20, 2198, 0),
        ('2017-11-13', 90, 20, 2216, 0),
        ('2017-12-11', 68, 10, 2238, 0),
        ('2018-01-10', 55, 10, 2251, 0),
        ('2018-02-12', 36, 0, 2270, 0),
        ('2018-03-12', 16, 0, 2290, 0),
    ]

    flag = True
    for expected, actual in zip(data, parse_8percent_data(raw)):
        assert len(expected) == len(actual)
        expected = list(expected)
        expected[0] = make_date(expected[0])
        for exp, act in zip(expected, actual):
            flag = False
            assert exp == act

    if flag:
        pytest.fail('parse_8percent_data() did not return any data')
