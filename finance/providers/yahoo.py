import csv
from datetime import datetime
from contextlib import closing
import io
import re

import requests
from typedecorator import typed

from finance.providers.provider import AssetValueProvider
from finance.utils import parse_date


def year_to_timestamp(year):
    return datetime.strptime(str(year), '%Y').timestamp()


class Yahoo(AssetValueProvider):
    @property
    def request_url(self):
        return 'https://query1.finance.yahoo.com/v7/finance/download/{0}'

    @property
    def request_headers(self):
        """Looks like no special header is required."""
        return {
            'Accept-Encoding': 'text/plain',
        }

    @typed
    def request_params(self: object, code: str, start_year: int,
                       end_year: int) -> dict:
        """
        Example request params:

            period1=1495203609&period2=1497882009&interval=1d&events=history
            &crumb=RWQ4NDixcmw

        """

        return {
            'period1': int(year_to_timestamp(start_year)),
            'period2': int(year_to_timestamp(end_year + 1)),
            'events': 'history',
            'crumb':  self.retrieve_crumb(code),
        }

    @typed
    def fetch_data(self: object, code: str, from_date: datetime,
                   to_date: datetime):
        params = self.request_params(code, from_date.year, to_date.year)
        resp = requests.get(self.request_url.format(code),
                            headers=self.request_headers, params=params)
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',

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

    def retrieve_crumb(self, code):
        url = 'https://finance.yahoo.com/quote/{0}/history?ltr=1'.format(code)
        resp = requests.get(url, headers=self.request_headers)
        s = re.search(r'"CrumbStore":{"crumb":"(\w+)"}', resp.text)
        return s.group(1)
