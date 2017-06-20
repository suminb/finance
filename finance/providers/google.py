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


class Google(AssetValueProvider):
    DATE_FORMAT = '%d-%b-%y'

    @property
    def request_url(self):
        return 'http://www.google.com/finance/historical'

    @property
    def request_headers(self):
        """Looks like no special header is required."""
        return {
            'Accept-Encoding': 'text/plain',
        }

    @typed
    def request_params(self: object, market: str, code: str, start_year: int,
                       end_year: int) -> dict:
        """
        Example request params:

            period1=1495203609&period2=1497882009&interval=1d&events=history
            &crumb=RWQ4NDixcmw

        """

        return {
            'q': '{0}:{1}'.format(market, code),
            'output': 'csv',
        }

    @typed
    def fetch_data(self: object, market: str, code: str, from_date: datetime,
                   to_date: datetime):
        params = self.request_params(market, code, from_date.year, to_date.year)
        resp = requests.get(self.request_url.format(code),
                            headers=self.request_headers, params=params)

        if resp.status_code != 200:
            resp.raise_for_status()

        stream = io.StringIO(resp.text)

        # Headers are in the following format.
        # ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        headers = next(stream)

        for row in csv.reader(stream, delimiter=','):
            date, open_, high, low, close_, volume = row
            yield parse_date(date, self.DATE_FORMAT), float(open_), \
                float(high), float(low), float(close_), int(volume)
