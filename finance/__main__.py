from datetime import datetime

import click
from logbook import Logger
from sqlalchemy.exc import IntegrityError
import requests

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import *  # noqa
from finance.utils import (
    AssetValueSchema, fetch_8percent_data, make_date, import_8percent_data,
    insert_asset, insert_asset_value, insert_record)


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
        account_kjp = Account.create(
            type='investment', name='키움일본인덱스 주식재간접', user=user)
        account_hf = Account.create(
            type='virtual', name='어니스트펀드', user=user)

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

        insert_record(',2015-01-01,,2400727', account_sp500, asset_sp500, None)
        insert_record(',2015-01-01,,1685792', account_esch, asset_esch, None)
        insert_record(',2015-01-01,,268695', account_kjp, asset_kjp, None)

        with Transaction.create() as t:
            insert_record(',2016-01-22,,10.00', account_gold, asset_gold, t)
            insert_record(',2016-01-22,,-426870', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-01-22,,-1.04', account_gold, asset_gold, t)
            insert_record(',2016-01-22,,49586', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-01-22,,-1.04', account_gold, asset_gold, t)
            insert_record(',2016-01-22,,49816', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-01-29,,-1.00', account_gold, asset_gold, t)
            insert_record(',2016-01-29,,48603', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-02-23,,-2.08', account_gold, asset_gold, t)
            insert_record(',2016-02-23,,99577', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-02-24,,-2.06', account_gold, asset_gold, t)
            insert_record(',2016-02-24,,99667', account_checking, asset_krw, t)
        with Transaction.create() as t:
            insert_record(',2016-02-26,,-1.63', account_gold, asset_gold, t)
            insert_record(',2016-02-26,,79589', account_checking, asset_krw, t)

        with Transaction.create() as t:
            insert_record(',2015-12-04,,500000',
                          account_checking, asset_krw, t)
            insert_record(',2015-12-04,,-500000',
                          account_checking, asset_krw, t)
            insert_record(',2015-12-04,,1', account_hf, asset_hf1, t)
        # Initial asset value
        insert_asset_value('2015-12-04,1day,,,,500000', asset_hf1, asset_krw)
        # 1st payment
        interest, tax, returned = 3923, 740, 30930
        with Transaction.create() as t:
            insert_record(',2016-01-08,,30930', account_checking, asset_krw, t)
        # Remaining principle value after the 1st payment
        insert_asset_value('2016-01-08,1day,,,,472253', asset_hf1, asset_krw)
        # 2nd payment
        with Transaction.create() as t:
            insert_record(',2016-02-05,,25016', account_checking, asset_krw, t)
        # Remaining principle value after the 2nd payment
        insert_asset_value('2016-02-05,1day,,,,450195', asset_hf1, asset_krw)

        portfolio = Portfolio()
        portfolio.target_asset = asset_krw
        portfolio.add_accounts(account_hf, account_checking, account_sp500,
                               account_kjp)


@cli.command()
def test():
    app = create_app(__name__)
    with app.app_context():
        account = Account.query.filter(Account.name == 'S&P500 Fund').first()
        print(account.net_worth(tf('2016-02-25')))


@cli.command()
@click.argument('bond_id')
@click.argument('cookie')
def import_8percent(bond_id, cookie):
    raw = fetch_8percent_data(bond_id, cookie)
    for row in import_8percent_data(raw):
        print(row)


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
