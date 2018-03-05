"""A collection of data import functions."""
import csv
import io

from sqlalchemy.exc import IntegrityError
from typedecorator import typed

from finance import log
from finance.models import Asset, AssetValue, db, Granularity
from finance.utils import DictReader


# NOTE: A verb 'import' means local structured data -> database
@typed
def import_stock_values(fin: io.TextIOWrapper, code: str):
    """Import stock values."""
    asset = Asset.get_by_symbol(code)
    reader = csv.reader(fin, delimiter=',', quotechar='"')
    # for date, open_, high, low, close_, volume, adj_close in reader:
    for date, open_, high, low, close_, volume in reader:
        try:
            AssetValue.create(
                evaluated_at=date, granularity=Granularity.day, asset=asset,
                open=open_, high=high, low=low, close=close_, volume=volume)
        except IntegrityError:
            log.warn('AssetValue for {0} on {1} already exist', code, date)
            db.session.rollback()
