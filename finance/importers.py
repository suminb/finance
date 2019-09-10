"""A collection of data import functions."""
import csv
import io

from sqlalchemy.exc import IntegrityError

from finance import log
from finance.models import (
    Account, Asset, AssetValue, Granularity, Transaction, db, deposit)
from finance.providers import Miraeasset


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


def import_miraeasset_foreign_records(
    fin: io.TextIOWrapper,
    account: Account,
):
    provider = Miraeasset()
    asset_krw = Asset.get_by_symbol('KRW')

    for r in provider.parse_foreign_transactions(fin):
        assert r.currency != 'KRW'
        # FIXME: Handle a case where asset cannot be found
        target_asset = Asset.get_by_symbol(r.currency)

        if r.category == '해외주매수':
            asset_stock = Asset.get_by_isin(r.code)
            make_double_record_transaction(
                r.synthesized_created_at,
                account,
                target_asset, -r.amount,
                asset_stock, r.quantity)
        elif r.category == '해외주매도':
            asset_stock = Asset.get_by_isin(r.code)
            make_double_record_transaction(
                r.synthesized_created_at,
                account,
                asset_stock, -r.quantity,
                target_asset, r.amount)
        elif r.category == '해외주배당금':
            deposit(account, target_asset, r.amount, r.synthesized_created_at)
        elif r.category == '환전매수':
            local_amount = int(r.raw_columns[6])  # amount in KRW
            make_double_record_transaction(
                r.synthesized_created_at,
                account,
                asset_krw, -local_amount,
                target_asset, r.amount)
        elif r.category == '환전매도':
            raise NotImplementedError
        elif r.category == '외화인지세':
            deposit(account, target_asset, -r.amount, r.synthesized_created_at)
        else:
            raise ValueError('Unknown record category: {0}'.format(r.category))
