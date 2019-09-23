"""A collection of data import functions."""
import csv
import io

from sqlalchemy.exc import IntegrityError

from finance import log
from finance.models import (
    Asset, AssetValue, Granularity, Transaction, db, deposit)


# NOTE: A verb 'import' means local structured data -> database
def import_stock_values(fin: io.TextIOWrapper, code: str, base_asset=None):
    """Import stock values."""
    asset = Asset.get_by_symbol(code)
    reader = csv.reader(
        fin, delimiter=',', quotechar='"', skipinitialspace=True)
    for date, open_, high, low, close_, volume, source in reader:
        try:
            yield AssetValue.create(
                evaluated_at=date, granularity=Granularity.day, asset=asset,
                base_asset=base_asset, open=open_, high=high, low=low,
                close=close_, volume=volume, source=source)
        except IntegrityError:
            log.warn('AssetValue for {0} on {1} already exist', code, date)
            db.session.rollback()


def make_double_record_transaction(
    created_at, account, asset_from, quantity_from, asset_to, quantity_to
):
    """Creates a double record transaction (e.g., a buy order of stocks)"""
    with Transaction.create() as t:
        record1 = deposit(account, asset_from, quantity_from, created_at, t)
        record2 = deposit(account, asset_to, quantity_to, created_at, t)
    return (record1, record2)
