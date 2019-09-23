import csv
from datetime import datetime, time, timedelta
import json
import os

import boto3
from flask import request
from logbook import Logger

# NOTE: finance.models should not be imported here in order to avoid circular
# depencencies

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

    if isinstance(start, str) or isinstance(start, int):
        start = parse_date(start)

    if isinstance(end, str) or isinstance(end, int):
        end = parse_date(end)

    if start > end:
        raise ValueError('Start date must be smaller than end date')

    delta = end - start
    for i in range(0, delta.days):
        yield start + timedelta(days=i)


def date_to_datetime(date, end_of_day=False):
    """Converts date to datetime.

    :param end_of_day: Indicates whether we want the datetime of the end of the
                       day.
    """
    return datetime.combine(
        date, time(23, 59, 59) if end_of_day else time(0, 0, 0))


def deprecated(func):
    '''This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.'''
    import warnings

    def new_func(*args, **kwargs):
        warnings.warn('Call to deprecated function {}'.format(func.__name__),
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


def extract_numbers(value, type=str):
    """Extracts numbers only from a string."""
    def extract(vs):
        for v in vs:
            if v in '01234567890.':
                yield v
    return type(''.join(extract(value)))


def get_dart_codes():
    """Returns all DART codes."""
    with open('data/dart_codes.csv') as fin:
        for line in fin.readlines():
            yield [x.strip() for x in line.split(',')]


def get_dart_code(entity_name):
    for name, code in get_dart_codes():
        if name == entity_name:
            return code
    raise ValueError('CRP code for {} is not found'.format(entity_name))


def load_stock_codes(fin):
    reader = csv.reader(fin, delimiter='\t', quotechar='"')
    for code, name in reader:
        if code != 'N/A':
            yield code, name


def make_request_import_stock_values_message(code, start_time, end_time):
    # type: (str, datetime, datetime) -> dict
    return {
        'version': 0,
        'code': code,
        'start_time': int(start_time.timestamp()),
        'end_time': int(end_time.timestamp()),
    }


def parse_date(date, format='%Y-%m-%d'):
    """Makes a date object from a string.

    :type date: str or int
    :rtype: datetime.date
    """
    if isinstance(date, int):
        return datetime.now().date() + timedelta(days=date)
    else:
        return datetime.strptime(date, format)


def parse_datetime(dt, at=datetime.now(), format='%Y-%m-%d %H:%M:%S'):
    """Makes a datetime object from a string.

    :param dt: Datetime
    :param at: Time at which the relative time is evaluated
    :param format: Datetime string format
    """
    if isinstance(dt, int):
        return at + timedelta(seconds=dt)
    else:
        return datetime.strptime(dt, format)


def parse_decimal(v, type_=float, fallback_to=0):
    try:
        return type_(v)
    except ValueError:
        return fallback_to


def parse_int(v, fallback_to=0):
    """Parses a string as an integer value. Falls back to zero when failed to
    parse."""
    try:
        return int(v)
    except ValueError:
        return fallback_to


def parse_stock_code(code: str):
    """Parses a stock code. NOTE: Only works for the Shinhan HTS"""
    if code.startswith('A'):
        return code[1:]
    elif code == '':
        return None
    else:
        return code


def parse_stock_records(stream):
    """
    :param stream: A steam to read in a CSV file.
    """
    # Skip first two lines
    next(stream), next(stream)

    while True:
        try:
            first_line, second_line = next(stream), next(stream)
        except StopIteration:
            break

        cols1 = first_line.split('\t')[:13]
        cols2 = second_line.split('\t')[:12]

        date, category1, code, quantity, subtotal, 미수발생_변제, interest, \
            fees, late_fees, 상대처, 변동금액, 대출일, 처리자 = cols1

        상품, category2, name, unit_price, 신용_대출금, 신용_대출이자, \
            예탁금이용료, 제세금, channel, 의뢰자명, final_amount, 만기일 \
            = cols2

        # NOTE: Date is in some peculiar format as following:
        #
        #     20160222000000000000000003
        #     20160222000000000000000002
        #     20160222000000000000000001
        #
        # where '20160202' is a date (YYYYMMDD) and the tailing number
        # appears to be the sequence of the day. In this case, the first row
        # indicates the transaction was the third one on 2016-02-02.
        #
        # date, sequence = parse_date(date[:8], '%Y%m%d'), int(date[8:])
        sequence = int(date[8:])
        # NOTE: The Record table has a unique constaint with
        # (account, asset, created_at, quantity) quadriple. As such, if we
        # have multiple transactions in the stock account with the same
        # code and the same quantity, it will cause a unique key constraint
        # violation. As a temporary workaround, we will put the daily sequence
        # as a microsecond portion of the datetime. If we have more than a
        # million transactions per day this will cause a problem.
        date = parse_date('{}.{:06d}'.format(date[:8], sequence), '%Y%m%d.%f')

        yield {
            'date': date,
            'sequence': sequence,
            'category1': category1,
            'category2': category2,
            'code': parse_stock_code(code),
            'name': name,
            'unit_price': parse_int(unit_price),
            'quantity': parse_int(quantity),
            'subtotal': parse_int(subtotal),
            'interest': parse_int(interest),
            'fees': parse_int(fees),
            'late_fees': parse_int(late_fees),
            'channel': channel,
            'final_amount': parse_int(final_amount),
        }


def poll_import_stock_values_requests(sqs_region, queue_url):
    client = boto3.client('sqs', region_name=sqs_region)
    resp = client.receive_message(**{
        'QueueUrl': queue_url, 'VisibilityTimeout': 180})
    messages = resp['Messages'] if 'Messages' in resp else []

    for message in messages:
        yield json.loads(message['Body'])
        client.delete_message(**{
            'QueueUrl': queue_url, 'ReceiptHandle': message['ReceiptHandle']})


def request_import_stock_values(
    code, start_time, end_time,
    sqs_region=os.environ.get('SQS_REGION', ''),
    queue_url=os.environ.get('REQUEST_IMPORT_STOCK_VALUES_QUEUE_URL', '')
):
    message = make_request_import_stock_values_message(
        code, start_time, end_time)

    client = boto3.client('sqs', region_name=sqs_region)
    resp = client.send_message(**{
        'QueueUrl': queue_url,
        'MessageBody': json.dumps(message),
    })

    if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
        log.error('Something went wrong: {0}', resp)


def insert_stock_record(data: dict, stock_account: object,
                        bank_account: object):
    """
    account_id = db.Column(db.BigInteger, db.ForeignKey('account.id'))
    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    # asset = db.relationship(Asset, uselist=False)
    transaction_id = db.Column(db.BigInteger, db.ForeignKey('transaction.id'))
    type = db.Column(db.Enum(*record_types, name='record_type'))
    # NOTE: We'll always use the UTC time
    created_at = db.Column(db.DateTime(timezone=False))
    category = db.Column(db.String)
    quantity = db.Column(db.Numeric(precision=20, scale=4))
    """
    if data['category2'] in ['매도', '매수']:
        return insert_stock_trading_record(data, stock_account)
    elif data['category2'] in ['제휴입금', '매매대금출금']:
        return insert_stock_transfer_record(data, bank_account)
    else:
        log.info('Skipping {} record...', data['category2'])
        return None


def insert_stock_trading_record(data: dict, stock_account: object):
    """Inserts a stock trading (i.e., buying or selling stocks) records."""
    from finance.models import Asset, deposit
    if data['category1'].startswith('장내'):
        code_suffix = '.KS'
    elif data['category1'].startswith('코스닥'):
        code_suffix = '.KQ'
    else:
        code_suffix = ''
        raise ValueError(
            "code_suffix could not be determined with the category '{}'"
            ''.format(data['category1']))

    code = data['code'] + code_suffix

    asset = Asset.get_by_symbol(code)
    if asset is None:
        raise ValueError(
            "Asset object could not be retrived with code '{}'".format(code))

    return deposit(stock_account, asset, data['quantity'], data['date'])


def insert_stock_transfer_record(data: dict, bank_account: object):
    """Inserts a transfer record between a bank account and a stock account.
    """
    from finance.models import Asset, deposit

    # FIXME: Not a good idea to use a hard coded value
    asset_krw = Asset.query.filter(Asset.name == 'KRW').first()

    subtotal = data['subtotal']
    date = data['date']

    if data['name'] == '증거금이체':
        # Transfer from a bank account to a stock account
        return deposit(bank_account, asset_krw, -subtotal, date)
    elif data['name'] == '매매대금정산':
        # Transfer from a stock account to a bank account
        return deposit(bank_account, asset_krw, subtotal, date)
    else:
        raise ValueError(
            "Unrecognized transfer type '{}'".format(data['name']))


def json_requested():
    """Determines whether the requested content type is application/json."""
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/plain'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/plain']


def serialize_datetime(obj):
    """JSON serializer for objects not serializable by default json code. This
    may be used as follows:

        json.dumps(obj, default=serialize_datetime)
    """

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError('Type not serializable')


class DictReader(object):
    def __init__(self, value):
        if not isinstance(value, dict):
            raise ValueError('DictReader only accepts dict type')
        self.value = value

    def __getattr__(self, name):
        return self.value[name]

    def __getitem__(self, key):
        return self.value[key]
