import json
import os

import click
from click.testing import CliRunner
from logbook import Logger
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.importers import \
    import_stock_values as import_stock_values_  # Avoid name clashes
from finance.models import (
    Account, AccountType, Asset, AssetType, AssetValue, DartReport, db,
    get_asset_by_fund_code, Granularity, Portfolio, Transaction, User)
from finance.providers import Dart, Kofia, Yahoo
from finance.utils import (
    date_to_datetime, extract_numbers, get_dart_code, insert_stock_record,
    parse_date, parse_stock_records, request_import_stock_values as
    request_import_stock_values_, serialize_datetime)


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
log = Logger('finance')


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
        yield Asset.create(type='stock', code=code, description=description,
                           ignore_if_exists=True)


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


def create_account(type_: AccountType, institution: str, number: str, user):
    return Account.create(
        type=type_, name='Test account', institution=institution,
        number=number, user=user, ignore_if_exists=True)


def create_asset(type_: AssetType, code: str, description: str):
    return Asset.create(
        type=type_, code=code, description=description, ignore_if_exists=True)


@cli.command()
def insert_test_data():
    """Inserts some sample data for testing."""
    app = create_app(__name__)
    with app.app_context():
        user = User.create(
            family_name='Byeon', given_name='Sumin', email='suminb@gmail.com',
            ignore_if_exists=True)

        account_checking = create_account(
            AccountType.checking, 'Shinhan', 'checking', user)
        account_stock = create_account(
            AccountType.investment, 'Mirae Asset', 'stock', user)

        asset_krw = create_asset(AssetType.currency, 'KRW', 'Korean Won')
        create_asset(AssetType.currency, 'USD', 'United States Dollar')

        for _ in insert_stock_assets():
            pass

        create_asset(AssetType.security, 'KR5223941018', 'KB S&P500')
        create_asset(AssetType.security, 'KR5229221225', '이스트스프링차이나')

        portfolio = Portfolio()
        portfolio.base_asset = asset_krw
        portfolio.add_accounts(account_checking, account_stock)


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
                    deposit(account_checking, asset_krw, -quantity_krw, date,
                            t)
                except IntegrityError:
                    log.warn('Identical record exists')
                    db.session.rollback()

                try:
                    deposit(account_sp500, asset_sp500, quantity_sp500,
                            date, t)
                except IntegrityError:
                    log.warn('Identical record exists')
                    db.session.rollback()


@cli.command()
@click.argument('stock_code')  # e.g., NVDA, 027410.KS
@click.option('-s', '--start', 'start_date',
              help='Start date (e.g., 2017-01-01)')
@click.option('-e', '--end', 'end_date',
              help='End date (e.g., 2017-12-31)')
def fetch_stock_values(stock_code, start_date, end_date):
    """Fetches daily stock values from Yahoo Finance."""

    start_date = date_to_datetime(
        parse_date(start_date if start_date is not None else -30 * 3600 * 24))
    end_date = date_to_datetime(
        parse_date(end_date if end_date is not None else 0))

    if start_date > end_date:
        raise ValueError('start_date must be equal to or less than end_date')

    provider = Yahoo()
    rows = provider.asset_values(
        stock_code, start_date, end_date, Granularity.day)

    for row in rows:
        # TODO: Write a function to handle this for generic cases
        # TODO: Convert the timestamp to an ISO format
        # NOTE: The last column is data source. Not sure if this is an elegant
        # way to handle this.

        # FIXME: Think of a better way to handle this
        dt = row[0].isoformat()

        print(', '.join([dt] + [str(c) for c in row[1:]] + ['yahoo']))


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
                    granularity=Granularity.day,
                    source='kofia')
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
        for _ in import_stock_values_(stdin, code):
            pass


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


@cli.command()
@click.argument('code')
def request_import_stock_values(code):
    """Enqueue a request to import stock values."""
    start_time = date_to_datetime(parse_date(-3))
    end_time = date_to_datetime(parse_date(0))

    request_import_stock_values_(code, start_time, end_time)


if __name__ == '__main__':
    cli()
