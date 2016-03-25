from datetime import datetime

import click
from logbook import Logger
from sqlalchemy.exc import IntegrityError
import requests

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import *  # noqa
from finance.utils import AssetValueSchema, make_date


tf = lambda x: datetime.strptime(x, '%Y-%m-%d')
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
            type='checking', name='Shinhan Checking', user=user)
        account_gold = Account.create(
            type='investment', name='Woori Gold Banking', user=user)
        account_sp500 = Account.create(
            type='investment', name='S&P500 Fund', user=user)
        account_esch = Account.create(
            type='investment', name='East Spring China Fund', user=user)
        account_hf = Account.create(type='virtual', name='어니스트펀드', user=user)

        asset_krw = Asset.create(
            type='currency', name='KRW', description='Korean Won')
        asset_usd = Asset.create(
            type='currency', name='USD', description='United States Dollar')
        asset_gold = Asset.create(
            type='commodity', name='Gold', description='')
        asset_sp500 = Asset.create(
            type='security', name='KB S&P500', description='',
            data={'code': 'KR5223941018'})
        asset_esch = Asset.create(
            type='security', name='East Spring China',
            data={'code': 'KR5229221225'})
        asset_hf1 = Asset.create(
            type='bond', name='포트폴리오 투자상품 1호')

        with Transaction.create() as t:
            Record.create(
                transaction=t,
                account=account_checking, asset=asset_krw, quantity=1000000)
        with Transaction.create() as t:
            Record.create(
                transaction=t, account=account_checking, asset=asset_krw,
                quantity=-4900)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2015-07-24'), transaction=t,
                account=account_gold, asset=asset_gold,
                quantity=2.00)
            Record.create(
                created_at=tf('2015-07-24'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=-84000)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2015-12-28'), transaction=t,
                account=account_gold, asset=asset_gold,
                quantity=-1.00)
            Record.create(
                created_at=tf('2015-12-28'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=49000)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2016-02-25'), transaction=t,
                account=account_sp500, asset=asset_sp500,
                quantity=1000)
            Record.create(
                created_at=tf('2016-02-25'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=-1000 * 921.77)

        AssetValue.create(
            evaluated_at=tf('2016-02-25'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.77)
        AssetValue.create(
            evaluated_at=tf('2016-02-24'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=932.00)
        AssetValue.create(
            evaluated_at=tf('2016-02-23'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.06)
        AssetValue.create(
            evaluated_at=tf('2016-02-22'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.76)


        data = """
2016-01-22, account_gold, asset_gold, 10.00
2016-01-22, account_checking, asset_krw, -426870
2016-02-12, account_gold, asset_gold, -1.04
2016-02-12, account_checking, asset_krw, 49586
2016-02-12, account_gold, asset_gold, -1.04
2016-02-12, account_checking, asset_krw, 49816
2016-02-19, account_gold, asset_gold, -1.00
2016-02-19, account_checking, asset_krw, 48603
2016-02-23, account_gold, asset_gold, -2.08
2016-02-23, account_checking, asset_krw, 99577
2016-02-24, account_gold, asset_gold, -2.06
2016-02-24, account_checking, asset_krw, 99667
2016-02-26, account_gold, asset_gold, -1.63
2016-02-26, account_checking, asset_krw, 79589
"""
        with Transaction.create() as t:
            Record.create(
                created_at=make_date('2015-12-04'), transaction=t,
                account=account_checking, asset=asset_krw, quantity=500000)
            Record.create(
                created_at=make_date('2015-12-04'), transaction=t,
                account=account_checking, asset=asset_krw, quantity=-500000)
            Record.create(
                created_at=make_date('2015-12-04'), transaction=t,
                account=account_hf, asset=asset_hf1, quantity=1)
        # Initial asset value
        AssetValue.create(
            evaluated_at=make_date('2015-12-04'), asset=asset_hf1,
            target_asset=asset_krw, granularity='1day', close=500000)
        # 1st payment
        interest, tax, returned = 3923, 740, 30930
        with Transaction.create() as t:
            Record.create(
                created_at=make_date('2016-01-08'), transaction=t,
                account=account_checking, asset=asset_krw, quantity=returned)
        # Remaining principle value after the 1st payment
        AssetValue.create(
            evaluated_at=make_date('2016-01-08'), asset=asset_hf1,
            target_asset=asset_krw, granularity='1day', close=472253)
        # 2nd payment
        with Transaction.create() as t:
            Record.create(
                created_at=make_date('2016-02-05'), transaction=t,
                account=account_checking, asset=asset_krw, quantity=25016)
        # Remaining principle value after the 2nd payment
        AssetValue.create(
            evaluated_at=make_date('2016-02-05'), asset=asset_hf1,
            target_asset=asset_krw, granularity='1day', close=450195)

        portfolio = Portfolio()
        portfolio.target_asset = asset_krw
        portfolio.add_accounts(account_hf, account_checking)


@cli.command()
def test():
    app = create_app(__name__)
    with app.app_context():
        account = Account.query.filter(Account.name == 'S&P500 Fund').first()
        print(account.net_worth(tf('2016-02-25')))


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
        'Referer': 'http://dis.kofia.or.kr/websquare/popup.html?w2xPath=/wq/com/popup/DISComFundSmryInfo.xml&companyCd=20090602&standardCd=KR5223941018&standardDt=20160219&grntGb=S&search=&check=1&isMain=undefined&companyGb=A&uFundNm=/v8ASwBCwqTQwLv4rW0AUwAmAFAANQAwADDHeLNxwqTJna2Mx5DSLMeQwuDQwQBbyPzC3QAt0wzA%0A3dYVAF0AQwAtAEU%3D&popupID=undefined&w2xHome=/wq/fundann/&w2xDocumentRoot=',
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
