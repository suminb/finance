from datetime import datetime, timedelta

import xmltodict


def date_range(start, end, step=1):
    """Generates a range of dates.

    :param start: Starting date (inclusive)
    :param end: Ending date (exclusive)
    :param step: Number of days to jump (currently unsupported)
    """
    if step != 1:
        raise NotImplementedError('Any value of step that is not 1 is not '
                                  'supported at the moment')
    if isinstance(start, str):
        start = make_date(start)
    if isinstance(end, str):
        end = make_date(end)

    delta = end - start
    for i in range(0, delta.days):
        yield start + timedelta(days=i)


def extract_numbers(value, type=float):
    """Extracts numbers only from a string."""
    def extract(vs):
        for v in vs:
            if v in '01234567890':
                yield v
    return type(''.join(extract(value)))


def make_date(strdate):
    """Make a datetime object from a string.

    :type strdate: str
    """
    return datetime.strptime(strdate, '%Y-%m-%d')


def parse_nullable_str(v):
    return v if v else None


def parse_decimal(v):
    try:
        return float(v)
    except ValueError:
        return None


def import_8percent_data(raw):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw, 'html.parser')

    rows = soup.find_all('div', class_='Box_444')
    for row in rows:
        cols = row.find_all('div')
        cols = [x.text.strip() for x in cols]
        date, _ = cols[0:2]
        principle, interest, tax, fees, total = map(extract_numbers, cols[2:7])
        yield date, principle, interest, tax, fees, total


def insert_asset(row, data=None):
    """Parses a comma separated values to fill in an Asset object.
    (type, name, description)

    :param row: comma separated values
    """
    from finance.models import Asset
    type, name, description = [x.strip() for x in row.split(',')]
    return Asset.create(
        type=type, name=name, description=description, data=data)


def insert_asset_value(row, asset, target_asset):
    """
    (evaluated_at, granularity, open, high, low, close)
    """
    from finance.models import AssetValue
    columns = [x.strip() for x in row.split(',')]
    evaluated_at = make_date(columns[0])
    granularity = columns[1]
    open, high, low, close = map(parse_decimal, columns[2:6])
    return AssetValue.create(
        asset=asset, target_asset=target_asset, evaluated_at=evaluated_at,
        granularity=granularity, open=open, high=high, low=low, close=close)


def insert_record(row, account, asset, transaction):
    """
    (type, created_at, cateory, quantity)
    """
    from finance.models import Record
    type, created_at, category, quantity = [x.strip() for x in row.split(',')]
    type = parse_nullable_str(type)
    created_at = make_date(created_at)
    category = parse_nullable_str(category)
    quantity = parse_decimal(quantity)
    return Record.create(
        account=account, asset=asset, transaction=transaction, type=type,
        created_at=created_at, category=category, quantity=quantity)


class AssetValueImporter(object):
    pass


class AssetValueSchema(object):
    def __init__(self):
        self.raw = None
        self.parsed = None

    def load(self, raw_data):
        """Loads raw data.

        :type raw_data: str
        """
        self.raw = raw_data
        self.parsed = xmltodict.parse(raw_data)

    def get_data(self):
        message = self.parsed['root']['message']
        price_records = message['COMFundPriceModListDTO']['priceModList']
        for pr in price_records:
            date_str = pr['standardDt']
            date = datetime.strptime(date_str, '%Y%m%d')
            unit_price = float(pr['standardCot'])
            original_quantity = float(pr['uOriginalAmt'])

            yield date, unit_price, original_quantity * 1000000
