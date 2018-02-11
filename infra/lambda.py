import os

from logbook import Logger
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import Asset, AssetType, AssetValue, db, Granularity
from finance.providers import Yahoo
from finance.utils import date_to_datetime, parse_date


log = Logger('finance')


# TODO: Write logs to CloudWatch

def handler(event, context):
    codes = event['codes']
    config = {
        'SQLALCHEMY_DATABASE_URI': event['db_url'],
    }

    app = create_app(__name__, config=config)
    with app.app_context():
        for code in codes:
            fetch_asset_values(code)


def fetch_asset_values(code):
    try:
        asset = Asset.get_by_symbol(code)
    except AssetNotFoundException:
        log.info('Asset {0} does not exist. Creating an Asset record...',
                 code)
        asset = Asset.create(name=code, code=code, type=AssetType.stock)

    start_date = date_to_datetime(parse_date(-7))
    end_date = date_to_datetime(parse_date(0))

    provider = Yahoo()
    rows = provider.asset_values(
        code, start_date, end_date, Granularity.min)

    for date, open_, high, low, close_, volume in rows:
        insert_asset_value(asset, date, open_, high, low, close_, volume)

    log.info('Asset values for {0} have been imported', code)


def insert_asset_value(asset, date, open_, high, low, close_, volume):
    try:
        asset_value = AssetValue.create(
            evaluated_at=date, granularity=Granularity.min,
            asset=asset, open=open_, high=high, low=low, close=close_,
            volume=int(volume), source='yahoo')
        log.info('Record has been create: {0}', asset_value)
    except IntegrityError:
        log.warn('AssetValue for {0} on {1} already exist', asset.code, date)
        db.session.rollback()


# TODO: Have a list of stock symbols to be fetched


if __name__ == '__main__':
    event = {
        'db_url': os.environ['DB_URL'],
        'codes': ['ESRT', 'NVDA']
    }
    handler(event, None)
