import types

from finance.utils import date_range, extract_numbers, make_date


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
