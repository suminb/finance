import math

from logbook import Logger
from pandas_datareader import data
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.exceptions import AssetNotFoundException
from finance.models import Asset, AssetType, AssetValue, db, Granularity
from finance.utils import parse_date


log = Logger('finance')


# TODO: Write logs to CloudWatch

def handler(event, context):
    # TODO: Take this value as a parameter
    code = 'MSFT'
    # code = '069500.KS'

    app = create_app(__name__)
    with app.app_context():
        try:
            asset = Asset.get_by_symbol(code)
        except AssetNotFoundException:
            log.info('Asset {0} does not exist. Creating an Asset record...',
                     code)
            asset = Asset.create(name=code, code=code, type=AssetType.stock)

        df = data.DataReader(code, 'yahoo', parse_date(-180), parse_date(-1))
        for record in df.to_records():
            date, open_, high, low, close_, adj_close, volume = record

            if any([math.isnan(x) for x in
                    [open_, high, low, close_, adj_close, volume]]):
                log.warn('Some value is NaN. Skipping this record.')
                continue

            try:
                # NOTE: Without casting `volume` into an integer type, it will
                # produce an error of
                # `psycopg2.ProgrammingError: can't adapt type 'numpy.int64'`
                # Need to figure out why.
                asset_value = AssetValue.create(
                    evaluated_at=date, granularity=Granularity.day,
                    asset=asset, open=open_, high=high, low=low, close=close_,
                    volume=int(volume))
                log.info('AssetValue record has been create: {0}', asset_value)
                # TODO: Define AssetValue.__repr__()
            except IntegrityError:
                log.warn('AssetValue for {0} on {1} already exist', code, date)
                db.session.rollback()

    log.info('Asset values for {0} have been imported', code)


# TODO: Have a list of stock symbols to be fetched


if __name__ == '__main__':
    handler(None, None)
