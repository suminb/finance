from datetime import datetime, time, timedelta
import os

import pytest

from finance.models import Granularity
from finance.providers import Dart, Kofia, Miraeasset
from finance.providers.dart import Report as DartReport
from finance.providers.yahoo import Yahoo
from finance.utils import parse_date


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, '..'))


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


def test_dart_fetch_data():
    provider = Dart()
    end = datetime.now()
    start = end - timedelta(days=90)
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
            assert isinstance(record.created_at, datetime)
            assert isinstance(record.seq, int)
            assert isinstance(record.quantity, int)
            assert record.currency in ['KRW', 'USD']


@pytest.mark.parametrize('granularity', [Granularity.min, Granularity.day])
def test_yahoo_provider(granularity):
    provider = Yahoo()
    symbol = 'MSFT'
    start_time = datetime.combine(parse_date(-5), time(0))
    end_time = datetime.utcnow()
    asset_values = \
        provider.asset_values(symbol, start_time, end_time, granularity)
    flag = False
    for asset_value in asset_values:
        flag = True
        assert len(asset_value) == 6
        assert all([c is not None for c in asset_value])
    assert flag


def test_yahoo_provider_with_invalid_symbol():
    provider = Yahoo()
    symbol = '(invalid)'
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    with pytest.raises(ValueError):
        provider.asset_values(symbol, start_time, end_time, Granularity.day)
