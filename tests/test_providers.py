from datetime import datetime, timedelta
import os

import pytest
from requests.exceptions import HTTPError

from finance.providers import _8Percent, Dart, Kofia, Miraeasset, Yahoo
from finance.providers.dart import Report as DartReport
from finance.utils import parse_date


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, '..'))


skip_if_no_credentials = pytest.mark.skipif(
    '_8PERCENT_USERNAME' not in os.environ or
    '_8PERCENT_PASSWORD' not in os.environ,
    reason='8percent credentials are not provided')


@skip_if_no_credentials
def test_8percent_login():
    username = os.environ.get('_8PERCENT_USERNAME')
    password = os.environ.get('_8PERCENT_PASSWORD')

    provider = _8Percent()
    resp = provider.login(username, password)
    assert 200 == resp.status_code


@skip_if_no_credentials
def test_8percent_fetch_data():
    provider = _8Percent()
    resp = provider.fetch_data(829)
    assert resp.status_code in [200, 404]

    if resp.status_code == 200:
        sample_file = os.path.join(PROJECT_PATH, 'tests', 'data',
                                   '8percent-829.html')
        with open(sample_file, 'w') as fout:
            fout.write(resp.text)


def test_8percent_parse_data():
    sample_file = os.path.join(PROJECT_PATH, 'tests', 'data',
                               '8percent-829.html')
    with open(sample_file) as fin:
        raw = fin.read()

    stored_data = [
        ('2016-04-11', 1694, 613, 160, 340),
        ('2016-05-11', 1916, 390, 90, 0),
        ('2016-06-13', 1920, 386, 90, 0),
        ('2016-07-11', 1982, 324, 80, 0),
        ('2016-08-10', 1963, 343, 80, 0),
        ('2016-09-12', 1979, 327, 80, 0),
        ('2016-10-10', 2005, 301, 70, 0),
        ('2016-11-14', 1992, 314, 70, 0),
        ('2016-12-12', 2054, 252, 60, 0),
        ('2017-01-10', 2044, 262, 60, 0),
        ('2017-02-13', 2053, 253, 60, 0),
        ('2017-03-13', 2099, 207, 50, 0),
        ('2017-04-10', 2101, 205, 50, 0),
        ('2017-05-15', 2098, 208, 50, 0),
        ('2017-06-12', 2145, 161, 40, 0),
        ('2017-07-10', 2151, 155, 30, 0),
        ('2017-08-14', 2153, 153, 30, 0),
        ('2017-09-11', 2188, 118, 20, 0),
        ('2017-10-11', 2198, 108, 20, 0),
        ('2017-11-13', 2216, 90, 20, 0),
        ('2017-12-11', 2238, 68, 10, 0),
        ('2018-01-10', 2251, 55, 10, 0),
        ('2018-02-12', 2270, 36, 0, 0),
        ('2018-03-12', 2290, 16, 0, 0),
    ]

    provider = _8Percent()
    parsed_data = provider.parse_data(raw)

    assert parsed_data['name']
    assert parsed_data['grade']
    assert isinstance(parsed_data['duration'], int)
    assert isinstance(parsed_data['annual_percentage_yield'], float)
    assert 0.0 < parsed_data['annual_percentage_yield'] <= 0.3
    assert isinstance(parsed_data['amount'], int)
    assert 0 < parsed_data['amount']

    flag = True
    for expected, actual in zip(stored_data, parsed_data['records']):
        assert len(expected) == len(actual)
        expected = list(expected)
        expected[0] = parse_date(expected[0])
        for exp, act in zip(expected, actual):
            flag = False
            assert exp == act

    if flag:
        pytest.fail('parse_8percent_data() did not return any data')


def test_kofia_request_url():
    provider = Kofia()
    assert 'kofia.or.kr' in provider.request_url


def test_kofia_request_headers():
    provider = Kofia()
    headers = provider.request_headers

    assert 'Origin' in headers
    assert 'kofia.or.kr' in headers['Origin']

    assert 'User-Agent' in headers

    assert 'Content-Type' in headers
    assert headers['Content-Type'] == 'text/xml'

    assert 'Accept' in headers
    assert headers['Accept'] == 'text/xml'

    assert 'Referer' in headers
    assert 'kofia.or.kr' in headers['Referer']


def test_kofia_get_request_body():
    provider = Kofia()
    body = provider.get_request_body(
        'KR5223941018', parse_date('2016-06-02'), parse_date('2016-06-03'))

    # TODO: Parse XML for assertion
    assert '20160602' in body
    assert '20160603' in body


def test_kofia_fetch_data():
    provider = Kofia()
    from_date, to_date = parse_date('2016-05-01'), parse_date('2016-05-30')
    data = provider.fetch_data('KR5223941018', from_date, to_date)

    for date, unit_price, quantity in data:
        assert isinstance(date, datetime)
        assert from_date <= date <= to_date
        assert isinstance(unit_price, float)
        assert isinstance(quantity, float)


# FIXME: The Yahoo data provider seems broken. Needs to be fixed
# but temporarily disabling for now.
def _test_yahoo_fetch_data():
    provider = Yahoo()
    from_date, to_date = parse_date('2014-01-01'), parse_date('2015-12-31')
    data = provider.fetch_data('005380.KS', from_date, to_date)

    for date, open_, high, low, close_, volume, adj_close in data:
        assert isinstance(date, datetime)
        # assert from_date <= date <= to_date
        assert isinstance(open_, float)
        assert isinstance(high, float)
        assert isinstance(low, float)
        assert isinstance(close_, float)
        assert isinstance(volume, int)
        assert isinstance(adj_close, float)


# FIXME: The Yahoo data provider seems broken. Needs to be fixed
# but temporarily disabling for now.
def _test_yahoo_fetch_data_with_invalid_code():
    provider = Yahoo()
    from_date, to_date = parse_date('2014-01-01'), parse_date('2015-12-31')
    with pytest.raises(HTTPError):
        data = provider.fetch_data('!@#$%', from_date, to_date)
        next(data)


def test_dart_fetch_data():
    provider = Dart()
    end = datetime.now()
    start = end - timedelta(days=7)
    reports = list(provider.fetch_reports('삼성전자', '00126380', start, end))

    assert len(reports) > 0
    for report in reports:
        assert isinstance(report, DartReport)


def test_dart_fetch_data_with_invalid_code():
    provider = Dart()
    with pytest.raises(ValueError):
        list(provider.fetch_reports('_', '_'))


@pytest.mark.parametrize('param', ['local', 'foreign'])
def test_miraeasset_transactions(param):
    provider = Miraeasset()
    filename = os.path.join(
        BASE_PATH, 'data', 'miraeasset_{}.csv'.format(param))
    with open(filename) as fin:
        if param == 'local':
            records = provider.parse_local_transactions(fin)
        elif param == 'foreign':
            records = provider.parse_foreign_transactions(fin)
        else:
            raise ValueError('Unknown transaction kind: {}'.format(param))

        for record in records:
            assert isinstance(record.registered_at, datetime)
            assert isinstance(record.seq, int)
            assert isinstance(record.quantity, int)
            assert record.currency in ['KRW', 'USD']
