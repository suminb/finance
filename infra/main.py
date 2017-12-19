import math

from logbook import Handler, Logger, Processor
from pandas_datareader import data
from sqlalchemy.exc import IntegrityError

from finance import create_app
from finance.models import Asset, AssetValue, db, Granularity
from finance.utils import parse_date


log = Logger('finance')


# TODO: Write logs to CloudWatch

def handler(event, context):
    # code = 'NVDA'
    code = '069500.KS'

    app = create_app(__name__)
    with app.app_context():
        asset = Asset.get_by_symbol(code)

        df = data.DataReader(code, 'yahoo', parse_date(-90), parse_date(0))
        for record in df.to_records():
            date, open_, high, low, close_, adj_close, volume = record

            if any([math.isnan(x) for x in
                [open_, high, low, close_, adj_close, volume]]):
                log.warn('Some value is NaN. Skipping this record.')
                continue

            try:
                AssetValue.create(
                    evaluated_at=date, granularity=Granularity.day, asset=asset,
                    open=open_, high=high, low=low, close=close_, volume=volume)
            except IntegrityError:
                log.warn('AssetValue for {0} on {1} already exist', code, date)
                db.session.rollback()

    log.info('Asset values for {0} have been imported', code)


if __name__ == '__main__':
    handler(None, None)
