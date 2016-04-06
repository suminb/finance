from datetime import datetime, timedelta

from logbook import Logger
import requests
import xmltodict


_8PERCENT_DATE_FORMAT = '%y.%m.%d'
log = Logger('finance')


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


def extract_numbers(value, type=str):
    """Extracts numbers only from a string."""
    def extract(vs):
        for v in vs:
            if v in '01234567890.':
                yield v
    return type(''.join(extract(value)))


def make_date(strdate):
    """Make a datetime object from a string.

    :type strdate: str
    """
    return parse_date(strdate)


def parse_date(strdate, format='%Y-%m-%d'):
    """Make a datetime object from a string.

    :type strdate: str
    """
    return datetime.strptime(strdate, format)


def parse_decimal(v):
    try:
        return float(v)
    except ValueError:
        return None


def parse_nullable_str(v):
    return v if v else None


def fetch_8percent_data(bond_id, cookie):
    url = 'https://8percent.kr/my/repayment_detail/{}/'.format(bond_id)
    log.info('Fetching bond information from {}', url)
    headers = {
        'Accept-Encoding': 'text/html',
        'Accept': 'text/html,application/xhtml+xml,application/xml;'
                  'q=0.9,image/webp,*/*;q=0.8',
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/49.0.2623.87 Safari/537.36',
    }
    resp = requests.get(url, headers=headers)
    return resp.text


def parse_8percent_data(raw):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw, 'html.parser')

    def extract_div_text(soup, id=None, class_=None):
        if id:
            return soup.find('div', id=id).text.strip()
        elif class_:
            return soup.find('div', class_=class_).text.strip()
        else:
            return Exception('Either id or class must be provided')

    def etni(soup, id, f):
        return f(extract_numbers(extract_div_text(soup, id=id)))

    def etnc(soup, class_, f):
        return f(extract_numbers(extract_div_text(soup, class_=class_)))

    name = extract_div_text(soup, id='Text_298')
    started_at = parse_date(extract_div_text(soup, id='Text_250'),
                            _8PERCENT_DATE_FORMAT)
    grade = extract_div_text(soup, id='Text_264')
    duration = etni(soup, 'Text_278', int)
    apy = etni(soup, 'Text_281', float) / 100
    amount = etni(soup, 'Text_300', int)

    log.info('Parsed: {}, {}, {}, {}, {}, {}', name, started_at, grade,
             duration, apy, amount)

    rows = soup.find_all('div', class_='Box_444')
    def gen_records(rows):
        for row in rows:
            date = parse_date(extract_div_text(row, class_='Cell_445'),
                              _8PERCENT_DATE_FORMAT)
            principle = etnc(row, 'Cell_451', int)
            interest = etnc(row, 'Cell_448', int)
            tax = etnc(row, 'Cell_449', int)
            fees = etnc(row, 'Cell_452', int)
            returned = etnc(row, 'Cell_453', int)

            # Make sure the parsed data is correct
            try:
                assert returned == principle + interest - (tax + fees)
            except AssertionError:
                import pdb; pdb.set_trace()
                pass

            yield date, principle, interest, tax, fees

    return {
        'name': name,
        'started_at': started_at,
        'grade': grade,
        'duration': duration,
        'annual_percentage_yield': apy,
        'amount': amount,
        'records': list(gen_records(rows)),
    }


def import_8percent_data(parsed_data, account_checking, account_8p, asset_krw):
    from finance.models import Asset, AssetValue, Record, Transaction

    assert account_checking
    assert account_8p
    assert asset_krw

    asset_8p = Asset.create(name=parsed_data['name'])
    remaining_value = parsed_data['amount']
    started_at = parsed_data['started_at']

    with Transaction.create() as t:
        Record.create(
            created_at=started_at, transaction=t, account=account_checking,
            asset=asset_krw, quantity=-remaining_value)
        Record.create(
            created_at=started_at, transaction=t, account=account_8p,
            asset=asset_8p, quantity=1)
    AssetValue.create(
        evaluated_at=started_at, asset=asset_8p,
        target_asset=asset_krw, granularity='1day', close=remaining_value)

    for record in parsed_data['records']:
        date, principle, interest, tax, fees = record
        returned = principle + interest - (tax + fees)
        remaining_value -= principle
        with Transaction.create() as t:
            Record.create(
                created_at=date, transaction=t,
                account=account_checking, asset=asset_krw, quantity=returned)
        AssetValue.create(
            evaluated_at=date, asset=asset_8p,
            target_asset=asset_krw, granularity='1day', close=remaining_value)


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
