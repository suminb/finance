import csv
from contextlib import closing
import io

import requests
from typedecorator import typed

from finance.providers.provider import AssetValueProvider
from finance.utils import parse_date


class Yahoo(AssetValueProvider):
    @property
    def request_url(self):
        return 'http://real-chart.finance.yahoo.com/table.csv'

    @property
    def request_headers(self):
        """Looks like no special header is required."""
        return {'Accept-Encoding': 'text/plain'}

    @typed
    def request_params(self: object, code: str, start_year: int,
                       end_year: int) -> dict:
        """
        Example request params:

            d=6&e=2&f=2016&g=d&a=0&b=4&c=2000&ignore=.csv

        """

        # NOTE: Seems like 'f' and 'c' have no effect at all... It always
        # returns data from 2000-01-01 to today's date
        return {
            'd': 6,  # ???
            'e': 2,  # ???
            'f': end_year,
            'g': 'd',  # ???
            'b': 4,  # ???
            'c': start_year,
            's': code,
            'ignore': '.csv',
        }

    @typed
    def fetch_data(self: object, code: str, start_year: int, end_year: int):
        params = self.request_params(code, start_year, end_year)
        resp = requests.get(self.request_url, headers=self.request_headers,
                            params=params)

        if resp.status_code != 200:
            resp.raise_for_status()

        stream = io.StringIO(resp.text)

        # Headers are in the following format.
        # ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        headers = next(stream)

        for row in csv.reader(stream, delimiter=','):
            date, open_, high, low, close_, volume, adj_close = row
            yield parse_date(date), float(open_), float(high), float(low), \
                float(close_), int(volume), float(adj_close)
