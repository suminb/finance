"""A collection of data import functions."""
import csv
import io

from sqlalchemy.exc import IntegrityError
from typedecorator import typed

from finance import log
from finance.models import Asset, AssetValue, db, Granularity
from finance.utils import DictReader


def import_8percent_data(parsed_data, account_checking, account_8p, asset_krw):
    """Import 8percent `AssetValue`s and `Record`s altogether."""
    from finance.models import Asset, AssetType, AssetValue, Record, \
        Transaction

    assert account_checking
    assert account_8p
    assert asset_krw

    parsed_data = DictReader(parsed_data)
    asset_data = {
        'started_at': parsed_data.started_at.isoformat()
    }
    keys = ['annual_percentage_yield', 'amount', 'grade', 'duration',
            'originator']
    for key in keys:
        asset_data[key] = parsed_data[key]

    asset_8p = Asset.create(name=parsed_data.name, type=AssetType.p2p_bond,
                            data=asset_data)
    remaining_value = parsed_data.amount
    started_at = parsed_data.started_at

    with Transaction.create() as t:
        Record.create(
            created_at=started_at, transaction=t, account=account_checking,
            asset=asset_krw, quantity=-remaining_value)
        Record.create(
            created_at=started_at, transaction=t, account=account_8p,
            asset=asset_8p, quantity=1)
    AssetValue.create(
        evaluated_at=started_at, asset=asset_8p,
        base_asset=asset_krw, granularity='1day', close=remaining_value)

    for record in parsed_data.records:
        date, principle, interest, tax, fees = record
        returned = principle + interest - (tax + fees)
        remaining_value -= principle
        with Transaction.create() as t:
            Record.create(
                created_at=date, transaction=t,
                account=account_checking, asset=asset_krw, quantity=returned)
        AssetValue.create(
            evaluated_at=date, asset=asset_8p,
            base_asset=asset_krw, granularity='1day', close=remaining_value)


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
