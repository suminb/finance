from finance.utils import date_range, make_date


def test_date_range():
    start, end = make_date('2016-01-01'), make_date('2016-01-15')
    r = date_range(start, end)

    assert 14 == len(r)
    assert r[0] == make_date('2016-01-01')
    assert r[13] == make_date('2016-01-14')
