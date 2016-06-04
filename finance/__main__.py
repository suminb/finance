import os
import re

import click
from click.testing import CliRunner
from logbook import Logger
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import *  # noqa
from finance.providers import _8Percent, Kofia
from finance.utils import (
    extract_numbers, import_8percent_data, insert_asset, insert_record,
    parse_date)


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
log = Logger('finance')


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    app = create_app(__name__)
    with app.app_context():
        db.create_all()


@cli.command()
def drop_all():
    app = create_app(__name__)
    with app.app_context():
        db.drop_all()


@cli.command()
def insert_test_data():
    app = create_app(__name__)
    with app.app_context():
        user = User.create(
            family_name='Byeon', given_name='Sumin', email='suminb@gmail.com')

        account_checking = Account.create(
            id=1001, type='checking', name='Shinhan Checking', user=user)
        account_gold = Account.create(
            id=9001, type='investment', name='Woori Gold Banking', user=user)
        account_sp500 = Account.create(
            id=7001, type='investment', name='S&P500 Fund', user=user)
        account_esch = Account.create(
            id=7002, type='investment', name='East Spring China Fund',
            user=user)
        account_kjp = Account.create(
            id=7003, type='investment', name='키움일본인덱스 주식재간접',
            user=user)
        account_8p = Account.create(
            id=8001, type='investment', name='8퍼센트', user=user)
        account_hf = Account.create(
            id=8002, type='virtual', name='어니스트펀드', user=user)

        asset_krw = insert_asset('currency, KRW, Korean Won')
        asset_usd = insert_asset('currency, USD, United States Dollar')
        asset_gold = insert_asset('commodity, Gold, Gold')
        asset_sp500 = insert_asset('security, KB S&P500,',
                                   data={'code': 'KR5223941018'})
        asset_esch = insert_asset('security, 이스트스프링차이나펀드,',
                                  data={'code': 'KR5229221225'})
        asset_kjp = insert_asset('security, 키움일본인덱스,',
                                 data={'code': 'KR5206689717'})
        asset_hf1 = insert_asset('bond, 포트폴리오 투자상품 1호,')

        portfolio = Portfolio()
        portfolio.base_asset = asset_krw
        portfolio.add_accounts(account_checking, account_8p)


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

    # print(account_sp500.net_worth(parse_date('2016-02-25'),
    #      base_asset=asset_krw))


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
    for bond_id in bond_ids:
        target_path = os.path.join(BASE_PATH, 'sample-data',
                                   '8percent-{}.html'.format(bond_id))
        raw = provider.fetch_data(bond_id)
        with open(target_path, 'w') as fout:
            fout.write(raw)


@cli.command()
@click.argument('filename')
def import_8percent(filename):
    """Imports a single file."""
    app = create_app(__name__)
    provider = _8Percent()
    with app.app_context():
        with open(filename) as fin:
            raw = fin.read()
        account_8p = Account.query.get(8001)
        account_checking = Account.query.filter(
            Account.name == 'Shinhan Checking').first()
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


@cli.command()
@click.argument('code')
@click.argument('from-date')
@click.argument('to-date')
def import_fund(code, from_date, to_date):
    """Imports fund data from KOFIA.

    :param from_date: e.g., 2016-01-01
    :param to_date: e.g., 2016-02-28
    """
    provider = Kofia()

    app = create_app(__name__)
    app.app_context().push()

    # NOTE: I know this looks really stupid, but we'll stick with this
    # temporary workaround until we figure out how to create an instance of
    # Asset model from a raw query result
    # (sqlalchemy.engine.result.RowProxy)
    query = "SELECT * FROM asset WHERE data->>'code' = :code LIMIT 1"
    raw_asset = db.session.execute(query, {'code': code}).first()
    if not raw_asset:
        raise AssetNotFoundException(
            'Fund code {} is not mapped to any asset'.format(code))
    asset_id = raw_asset[0]
    asset = Asset.query.get(asset_id)

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
                evaluated_at=date, close=unit_price, granularity='1day')
        except IntegrityError:
            log.warn('Identical record has been found for {}. Skipping.',
                     date)
            db.session.rollback()


if __name__ == '__main__':
    cli()
