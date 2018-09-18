from datetime import datetime
import json

import requests

from finance.models import Granularity
from finance.providers.provider import AssetValueProvider


class Yahoo(AssetValueProvider):
    """Fetches and parses financial data from Yahoo Finance."""

    name = 'yahoo'

    def __init__(self):
        pass

    def get_url(self, symbol):
        """Returns a URL to be fetched.

        :param symbol: A symbol of a security (e.g., NVDA, MSFT)
        """
        return 'https://query1.finance.yahoo.com/v8/finance/chart/{0}'

    def as_timestamp(self, datetime):
        return int(datetime.timestamp())

    def asset_values(self, symbol, start_time, end_time,
                     granularity=Granularity.day):
        mappings = {
            Granularity.day: self.fetch_daily_data,
            Granularity.min: self.fetch_data_by_minutes,
        }

        try:
            fetcher = mappings[granularity]
        except KeyError:
            raise NotImplementedError
        else:
            rows = fetcher(symbol, start_time, end_time)

        return self.filter_empty_rows(rows)

    # NOTE: 'Data by day' would keep the name consistent, but 'daily data'
    # sounds more natural.
    def fetch_daily_data(self, symbol, start_time, end_time):
        url = self.get_url(symbol)

        params = {
            'symbol': symbol,
            'period1': self.as_timestamp(start_time),
            'period2': self.as_timestamp(end_time),
            'interval': '1d',
            'includePrePost': 'true',
            'events': 'div%7Csplit%7Cearn',
            'corsDomain': 'finance.yahoo.com',
        }
        resp = requests.get(url, params=params)
        rows = self.parse_chart_data(resp.text)

        return rows

    def fetch_data_by_minutes(self, symbol, start_time, end_time):
        url = self.get_url(symbol)

        params = {
            'symbol': symbol,
            'period1': self.as_timestamp(start_time),
            'period2': self.as_timestamp(end_time),
            'interval': '1m',
            'includePrePost': 'true',
            'events': 'div%7Csplit%7Cearn',
            'corsDomain': 'finance.yahoo.com',
        }
        resp = requests.get(url, params=params)
        rows = self.parse_chart_data(resp.text)

        return rows

    def parse_chart_data(self, raw_json):
        """Parses Yahoo Finance chart data.

        See some examples if necessary:
        - sample-data/yahoo_finance_msft_1m.json
        - sample-data/yahoo_finance_nvda_1d.json

        In case of error, the response will look something like the following:

            {'chart': {
                'result': None,
                'error': {
                    'code': 'Not Found',
                    'description': 'No data found, symbol may be delisted'}
                }
            }
        """
        parsed = json.loads(raw_json)
        error = parsed['chart']['error']

        if error:
            raise ValueError(error['description'])

        timestamps = parsed['chart']['result'][0]['timestamp']
        timestamps = [datetime.fromtimestamp(int(t)) for t in timestamps]
        quote = parsed['chart']['result'][0]['indicators']['quote'][0]

        keys = ['open', 'high', 'low', 'close', 'volume']
        cols = [timestamps] + [quote[k] for k in keys]

        # Transposition from column-wise data to row-wise data
        return zip(*cols)

    def filter_empty_rows(self, rows):
        for row in rows:
            if all([c is not None for c in row]):
                yield row
