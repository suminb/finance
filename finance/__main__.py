import csv
import json
import os
import re
import sys

import click
from click.testing import CliRunner
from logbook import Logger
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.importers import \
    import_8percent_data, \
    import_stock_values as import_stock_values_  # Avoid name clashes
from finance.models import (
    Account, Asset, AssetValue, DartReport, db, get_asset_by_fund_code,
    Granularity, Portfolio, Record, Transaction, User)
from finance.providers import _8Percent, Dart, Google, Kofia, Miraeasset
from finance.utils import (
    extract_numbers, get_dart_code, insert_asset, insert_record,
    insert_stock_record, parse_date, parse_stock_records, serialize_datetime)


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
log = Logger('finance')


def insert_accounts(user):
    yield Account.create(
        id=1001, type='checking', name='신한은행 입출금', user=user)
    yield Account.create(
        id=9001, type='investment', name='Woori Gold Banking', user=user)
    yield Account.create(
        id=7001, type='investment', name='S&P500 Fund', user=user)
    yield Account.create(
        id=7002, type='investment', name='East Spring China Fund',
        user=user)
    yield Account.create(
        id=7003, type='investment', name='키움일본인덱스 주식재간접',
        user=user)
    yield Account.create(
        id=8003, type='investment', name='신한 주식', user=user)
    yield Account.create(
        id=8001, type='virtual', name='8퍼센트', user=user)
    yield Account.create(
        id=8002, type='virtual', name='어니스트펀드', user=user)


def insert_stock_assets():
    """NOTE: This is a temporary workaround. All stock informaion shall be
    fetched automatically on the fly.
    """
    rows = [
        ('036570.KS', 'NCsoft Corporation'),
        ('145210.KS', 'SAEHWA IMC'),
        ('069080.KQ', 'Webzen'),
        ('053800.KQ', 'Ahnlab Inc.'),
        ('017670.KS', 'SK Telecom Co. Ltd.'),
        ('005380.KS', 'Hyundai Motor Company'),
        ('056080.KQ', 'Yujin Robot Co., Ltd.'),
        ('069500.KS', 'KODEX 200'),
        ('009830.KS', '한화케미칼'),
    ]

    for code, description in rows:
        log.info('Inserting {} ({})...', code, description)
        yield Asset.create(type='stock', code=code, description=description)


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    """Creates necessary database tables."""
    app = create_app(__name__)
    with app.app_context():
        db.create_all()


@cli.command()
def drop_all():
    """Drops all database tables."""
    app = create_app(__name__)
    with app.app_context():
        db.drop_all()


@cli.command()
def insert_test_data():
    """Inserts some sample data for testing."""
    app = create_app(__name__)
    with app.app_context():
        user = User.create(
            family_name='Byeon', given_name='Sumin', email='suminb@gmail.com')

        account_checking, _, _, _, _, account_stock, account_8p, _ = \
            insert_accounts(user)
        for _ in insert_stock_assets():
            pass

        asset_krw = insert_asset('currency, KRW, Korean Won')
        insert_asset('currency, USD, United States Dollar')
        insert_asset('commodity, Gold, Gold')
        insert_asset('security, KB S&P500,', data={'code': 'KR5223941018'})
        insert_asset('security, 이스트스프링차이나펀드,',
                     data={'code': 'KR5229221225'})
        insert_asset('security, 키움일본인덱스,',
                     data={'code': 'KR5206689717'})
        insert_asset('bond, 포트폴리오 투자상품 1호,')

        portfolio = Portfolio()
        portfolio.base_asset = asset_krw
        portfolio.add_accounts(account_checking, account_stock, account_8p)


@cli.command()
@click.argument('entity_name')
def fetch_dart(entity_name):
    """Fetch all reports from DART (전자공시)."""

    entity_code = get_dart_code(entity_name)
    provider = Dart()

    log.info('Fetching DART reports for {}', entity_name)
    reports = provider.fetch_reports(entity_name, entity_code)

    # Apparently generators are not JSON serializable
    print(json.dumps([dict(r) for r in reports], default=serialize_datetime))


# TODO: Load data from stdin
@cli.command()
@click.argument('fin', type=click.File('r'))
def import_dart(fin):
    """Import DART (전자공시) data."""

    try:
        data = json.loads(fin.read())
    except json.decoder.JSONDecodeError as e:
        log.error('Valid JSON data expected: {}', e)

    app = create_app(__name__)
    with app.app_context():
        for row in data:
            try:
                report = DartReport.create(**row)
            except IntegrityError:
                log.info('DartReport-{} already exists', row['id'])
                db.session.rollback()
            else:
                log.info('Fetched report: {}', report)


@cli.command()
def import_sp500_asset_values():
    runner = CliRunner()
    runner.invoke(import_fund, ['KR5223941018', '2015-01-01', '2016-06-01'],
                  catch_exceptions=True)


@cli.command()
def import_sp500_records():
    """Import S&P500 fund sample data. Expects a tab seprated value document.
    """
    app = create_app(__name__)
    app.app_context().push()

    account_checking = Account.get(id=1001)
    account_sp500 = Account.get(id=7001)
    asset_krw = Asset.query.filter_by(name='KRW').first()
    asset_sp500 = Asset.query.filter_by(name='KB S&P500').first()

    # Expected number of columns
    expected_col_count = 6

    with open('sample-data/sp500.csv') as fin:
        # Skip the first row (headers)
        headers = next(fin)
        col_count = len(headers.split())
        if col_count != expected_col_count:
            raise Exception(
                'Expected number of columns = {}, '
                'actual number of columns = {}'.format(
                    expected_col_count, col_count))

        for line in fin:
            cols = line.split('\t')
            if len(cols) != expected_col_count:
                continue
            date = parse_date(cols[0], '%Y.%m.%d')
            _type = cols[1]
            quantity_krw, quantity_sp500 = \
                [int(extract_numbers(v)) for v in cols[3:5]]

            log.info(', '.join([c.strip() for c in cols]))

            if not (_type == '일반입금' or _type == '일반신규'):
                log.info('Record type \'{}\' will be ignored', _type)
                continue

            with Transaction.create() as t:
                # NOTE: The actual deposit date and the buying date generally
                # differ by a few days. Need to figure out how to parse this
                # properly from the raw data.
                try:
                    Record.create(
                        created_at=date, account=account_checking,
                        asset=asset_krw, quantity=-quantity_krw,
                        transaction=t)
                except IntegrityError:
                    log.warn('Identical record exists')
                    db.session.rollback()

                try:
                    Record.create(
                        created_at=date, account=account_sp500,
                        asset=asset_sp500, quantity=quantity_sp500,
                        transaction=t)
                except IntegrityError:
                    log.warn('Identical record exists')
                    db.session.rollback()


def _parse_miraeasset_data(filename, parse_func):
    with open(filename) as fin:
        records = parse_func(fin)
        writer = csv.writer(sys.stdout)
        for record in records:
            writer.writerow(record.values())


@cli.command()
@click.argument('filename')
def parse_miraeasset_foreign_data(filename):
    """Parses a CSV file exported in 해외거래내역 (9465)."""
    provider = Miraeasset()
    _parse_miraeasset_data(filename, provider.parse_foreign_transactions)


# TODO: Load data from stdin
@cli.command()
@click.argument('filename')
def parse_miraeasset_local_data(filename):
    """Parses CSV file exported in 거래내역조회 (0650)."""
    provider = Miraeasset()
    _parse_miraeasset_data(filename, provider.parse_local_transactions)


# TODO: Load data from stdin
@cli.command()
@click.argument('filename')
def import_miraeasset_foreign_data(filename):
    """Imports a CSV file exported in 해외거래내역 (9465)."""
    provider = Miraeasset()
    _import_miraeasset_data(filename, provider.parse_foreign_transactions)


@cli.command()
@click.argument('filename')
def fetch_8percent(filename):
    """
    :param filename: A file containing bond IDs
    """
    with open(filename) as fin:
        raw = fin.read()
    bond_ids = [int(x) for x in
                re.findall(r'/my/repayment_detail/(\d+)', raw)]
    provider = _8Percent()
    provider.login()
    for bond_id in bond_ids:
        log.info('Fetching bond ID = {}', bond_id)
        target_path = os.path.join(BASE_PATH, 'sample-data',
                                   '8percent-{}.html'.format(bond_id))
        resp = provider.fetch_data(bond_id)
        with open(target_path, 'w') as fout:
            fout.write(resp.text)


@cli.command()
@click.argument('stock_code')  # e.g., NYSE:IBM, NASDAQ:NVDA, 027410.KS
def fetch_stock_values(stock_code):
    """Fetches daily stock values from Google Finance."""
    if re.match(r'\d{6}\.K[SQ]', stock_code):
        code, market = stock_code.split('.')
        if market == 'KS':
            market = 'KRX'
        elif market == 'KQ':
            market = 'KOSDAQ'
        else:
            raise ValueError('Unknown market: {0}'.format(market))
    else:
        # TODO: Could we get rid of the need for specifying markets?
        market, code = stock_code.split(':')

    provider = Google()
    # FIXME: The date range currently has no effect. This should be fixed.
    records = provider.fetch_data(
        market, code, parse_date(-90), parse_date(0))

    for date, open_, high, low, close_, volume in records:
        # FIXME: This date format, %Y-%m%-%d, shall be a const
        formatted = [date.strftime('%Y-%m-%d'), open_, high, low,
                     close_, volume]
        print(', '.join(map(str, formatted)))


# TODO: Load data from stdin
@cli.command()
@click.argument('filename')
def import_8percent(filename):
    """Imports a single file."""
    app = create_app(__name__)
    provider = _8Percent()
    with app.app_context():
        with open(filename) as fin:
            raw = fin.read()
        account_8p = Account.query.filter(Account.name == '8퍼센트').first()
        account_checking = Account.query.filter(
            Account.name == '신한은행 입출금').first()
        asset_krw = Asset.query.filter(Asset.name == 'KRW').first()

        parsed_data = provider.parse_data(raw)
        import_8percent_data(
            parsed_data, account_checking=account_checking,
            account_8p=account_8p, asset_krw=asset_krw)


@cli.command()
def import_hf():
    app = create_app(__name__)
    app.app_context().push()

    account = Account.get(id=1001)
    asset = Asset.query.filter_by(name='KRW').first()

    with open('sample-data/hf.txt') as fin:
        for line in fin:
            if line.strip():
                insert_record(line, account, asset, None)


@cli.command()
def import_rf():
    app = create_app(__name__)
    app.app_context().push()

    account = Account.get(id=1001)
    asset = Asset.query.filter_by(name='KRW').first()

    with open('sample-data/rf.txt') as fin:
        for line in fin:
            if line.strip():
                insert_record(line, account, asset, None)


# NOTE: This will probably be called by AWS Lambda
# TODO: Load data from stdin
@cli.command()
@click.argument('code')
@click.argument('from-date')
@click.argument('to-date')
def import_fund(code, from_date, to_date):
    """Imports fund data from KOFIA.

    :param code: e.g., KR5223941018
    :param from_date: e.g., 2016-01-01
    :param to_date: e.g., 2016-02-28
    """
    provider = Kofia()

    app = create_app(__name__)
    with app.app_context():
        asset = get_asset_by_fund_code(code)

        # FIXME: Target asset should also be determined by asset.data.code
        base_asset = Asset.query.filter_by(name='KRW').first()

        data = provider.fetch_data(
            code, parse_date(from_date), parse_date(to_date))
        for date, unit_price, quantity in data:
            log.info('Import data on {}', date)
            unit_price /= 1000.0
            try:
                AssetValue.create(
                    asset=asset, base_asset=base_asset,
                    evaluated_at=date, close=unit_price,
                    granularity=Granularity.day)
            except IntegrityError:
                log.warn('Identical record has been found for {}. Skipping.',
                         date)
                db.session.rollback()


@cli.command()
@click.argument('code')
def import_stock_values(code):
    """Import stock price information."""
    app = create_app(__name__)
    with app.app_context():
        # NOTE: We assume all Asset records are already in the database, but
        # this is a temporary workaround. We should implement some mechanism to
        # automatically insert an Asset record when it is not found.

        stdin = click.get_text_stream('stdin')
        import_stock_values_(stdin, code)


# TODO: Load data from stdin
@cli.command()
@click.argument('filename')
def import_stock_records(filename):
    """Parses exported data from the Shinhan HTS."""
    app = create_app(__name__)
    with app.app_context():
        account_bank = Account.query \
            .filter(Account.name == '신한 입출금').first()
        account_stock = Account.query \
            .filter(Account.name == '신한 주식').first()
        with open(filename) as fin:
            for parsed in parse_stock_records(fin):
                insert_stock_record(parsed, account_stock, account_bank)


if __name__ == '__main__':
    cli()
