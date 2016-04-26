import os
import re

import click
from logbook import Logger
from sqlalchemy.exc import IntegrityError
import requests

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import *  # noqa
from finance.utils import (
    AssetValueSchema, extract_numbers, fetch_8percent_data, make_date,
    import_8percent_data, insert_asset, insert_asset_value, insert_record,
    parse_8percent_data, parse_date)


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
        portfolio.target_asset = asset_krw
        portfolio.add_accounts(account_checking, account_8p)


@cli.command()
def import_sp500():
    app = create_app(__name__)
    with app.app_context():
        account_checking = Account.get(id=1001)
        account_sp500 = Account.get(id=7001)
        asset_krw = Asset.query.filter_by(name='KRW').first()
        asset_sp500 = Asset.query.filter_by(name='KB S&P500').first()

        with open('sample-data/sp500.csv') as fin:
            for line in fin:
                cols = line.split()
                if len(cols) != 5:
                    continue
                date = parse_date(cols[0], '%Y.%m.%d')
                _type = cols[1]
                quantity_krw, quantity_sp500 = \
                    [int(extract_numbers(v)) for v in cols[2:4]]

                print(cols)

                withdraw = _type == '일반입금'

                with Transaction.create() as t:
                    if withdraw:
                        Record.create(
                            created_at=date, account=account_checking,
                            asset=asset_krw, quantity=-quantity_krw,
                            transaction=t)
                    Record.create(
                        created_at=date, account=account_sp500,
                        asset=asset_sp500, quantity=quantity_sp500,
                        transaction=t)

        print(account_sp500.net_worth(make_date('2016-02-25'), target_asset=asset_krw))



@cli.command()
@click.argument('filename')
@click.argument('cookie')
def fetch_8percent(filename, cookie):
    """
    :param filename: A file containing bond IDs
    """
    with open(filename) as fin:
        raw = fin.read()
    bond_ids = [int(x) for x in
                re.findall(r'/my/repayment_detail/(\d+)', raw)]
    for bond_id in bond_ids:
        target_path = os.path.join(BASE_PATH, 'sample-data',
                                   '8percent-{}.html'.format(bond_id))
        raw = fetch_8percent_data(bond_id, cookie)
        with open(target_path, 'w') as fout:
            fout.write(raw)


@cli.command()
@click.argument('filename')
def import_8percent(filename):
    """Imports a single file."""
    app = create_app(__name__)
    with app.app_context():
        with open(filename) as fin:
            raw = fin.read()
        account_8p = Account.query.get(8001)
        account_checking = Account.query.filter(
            Account.name == 'Shinhan Checking').first()
        asset_krw = Asset.query.filter(Asset.name == 'KRW').first()

        parsed_data = parse_8percent_data(raw)
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

    :param from_date: e.g., 20160101
    :param to_date: e.g., 20160228
    """
    url = 'http://dis.kofia.or.kr/proframeWeb/XMLSERVICES/'
    headers = {
        'Origin': 'http://dis.kofia.or.kr',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8,ko;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/48.0.2564.109 Safari/537.36',
        'Content-Type': 'text/xml',
        'Accept': 'text/xml',
        'Referer': 'http://dis.kofia.or.kr/websquare/popup.html?w2xPath='
                   '/wq/com/popup/DISComFundSmryInfo.xml&companyCd=20090602&'
                   'standardCd=KR5223941018&standardDt=20160219&grntGb=S&'
                   'search=&check=1&isMain=undefined&companyGb=A&uFundNm='
                   '/v8ASwBCwqTQwLv4rW0AUwAmAFAANQAwADDHeLNxwqTJna2Mx5DSLMeQwu'
                   'DQwQBbyPzC3QAt0wzA%0A3dYVAF0AQwAtAEU%3D&popupID=undefined&'
                   'w2xHome=/wq/fundann/&w2xDocumentRoot=',
    }
    data = """<?xml version="1.0" encoding="utf-8"?>
        <message>
            <proframeHeader>
                <pfmAppName>FS-COM</pfmAppName>
                <pfmSvcName>COMFundPriceModSO</pfmSvcName>
                <pfmFnName>priceModSrch</pfmFnName>
            </proframeHeader>
            <systemHeader></systemHeader>
            <COMFundUnityInfoInputDTO>
                <standardCd>{code}</standardCd>
                <companyCd>A01031</companyCd>
                <vSrchTrmFrom>{from_date}</vSrchTrmFrom>
                <vSrchTrmTo>{to_date}</vSrchTrmTo>
                <vSrchStd>1</vSrchStd>
            </COMFundUnityInfoInputDTO>
        </message>
    """.format(code=code, from_date=from_date, to_date=to_date)
    resp = requests.post(url, headers=headers, data=data)

    app = create_app(__name__)
    with app.app_context():
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
        target_asset = Asset.query.filter_by(name='KRW').first()

        schema = AssetValueSchema()
        schema.load(resp.text)
        for date, unit_price, original_quantity in schema.get_data():
            log.info('Import data on {}', date)
            unit_price /= 1000.0
            try:
                AssetValue.create(
                    asset=asset, target_asset=target_asset,
                    evaluated_at=date, close=unit_price, granularity='1day')
            except IntegrityError:
                log.warn('Identical record has been found for {}. Skipping.',
                         date)
                db.session.rollback()


if __name__ == '__main__':
    cli()
